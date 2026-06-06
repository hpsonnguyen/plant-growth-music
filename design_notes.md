# Design Notes

## Design Problem

The dataset is not a melody. It is `30,000` rows of greenhouse measurements split across three batches, `R1`, `R2`, and `R3`. Many of the raw values describe accumulation: plant weight, leaf area, root length, water content. If those values were mapped directly to pitch, the result would mostly be a slow staircase with occasional jumps.

The design therefore separates the question into musical components:

| Data Question | Musical Component |
|---|---|
| How much plant material is present? | phrase body, duration, contour direction |
| How much leaf structure is present? | register and openness |
| How active is recent growth? | note density and local movement |
| How healthy or expressive is the plant state? | velocity and dynamic force |
| Which batch produced the values? | separate melodic voice |

This keeps the music tied to the data without pretending that a plant metric is already a pitch, chord, or rhythm.

## Time Mapping

Every `100` dataset rows become one beat. With `30,000` rows, this gives `300` beats. At `90 BPM`, the data-driven portion lasts `200 seconds`.

This scale was chosen for two reasons. First, it preserves the slow character of plant growth: changes unfold over phrases rather than flickering by as isolated points. Second, it gives enough musical time for the three batches to remain separate voices instead of being compressed into a short data sonification.

The generated audio lasts about `202.7 seconds` because a final sustained `D3` is added after the data timeline. That note is not data-derived; it is a compositional boundary so the piece resolves instead of stopping abruptly at the end of the CSV.

## Derived Signals

The raw columns are grouped by what they describe biologically before they are used musically.

| Derived Signal | Source Measurements | Why This Grouping Makes Sense | Musical Use |
|---|---|---|---|
| `growth_mass` | green-vegetative weight, dry/wet root and vegetative weight | These columns describe accumulated plant body rather than momentary change. | phrase weight, note duration, contour direction |
| `leaf_energy` | leaf area, number of leaves, chlorophyll | These describe the visible photosynthetic surface of the plant. | register: more leaf energy opens the melody upward |
| `root_energy` | root length, root diameter, root dry matter | These describe below-ground structure. | harmonic/chord scoring and grounding behavior |
| `vitality` | plant height, chlorophyll, leaf area | These combine height and photosynthetic strength. | velocity and dynamic intensity |
| `growth_speed` | smoothed absolute change in `growth_mass` | This captures recent movement rather than accumulated size. | rhythm density and local melodic motion |

The important distinction is between amount and change. `growth_mass` tells the system where the plant has arrived. `growth_speed` tells it that something is currently changing. That is why `growth_speed` controls activity while `growth_mass` contributes to phrase shape.

## Melody Generation

The melody is generated before accompaniment. Each batch is processed independently, so `R1`, `R2`, and `R3` each become their own melodic line.

The generator does not convert one plant value directly into one note. It uses the plant features to answer four separate questions at every beat:

| Question | Data Used | Musical Result |
|---|---|---|
| Does this beat produce a note? | `growth_speed` plus section density | rest or melody event |
| Should the contour move up or down? | `growth_mass` compared to a 9-beat local average | direction `+1` or `-1` |
| How far should it move? | `0.65 * growth_speed + 0.35 * root_energy` | scale-step distance |
| Where should the line be pulled in register? | `leaf_energy` | drift toward lower or higher part of the batch register |
| How strong should the note be? | `vitality` plus section velocity | MIDI velocity |

This separation matters because the dataset mixes accumulated size and local change. `growth_mass` is useful for direction because it gives the contour a long-term tendency. `growth_speed` is useful for density and motion because it reacts to recent change. `leaf_energy` is useful for register because leaf area, leaf count, and chlorophyll describe the visible upper structure of the plant.

The melody algorithm for one batch is:

1. Build the legal pitch set from the configured register and `D Dorian` scale.
2. Start at the configured center note for the batch.
3. For each beat, calculate density as `max(0.18, growth_speed^0.55) * section_density_multiplier`, clipped to `0-1`.
4. If an event is produced, compare `growth_mass` to its local rolling average. If it is above average, the contour moves upward; otherwise it moves downward.
5. Calculate step size with `1 + round((0.65 * growth_speed + 0.35 * root_energy) * max_steps)`. The default `max_steps` is `5`.
6. If `0.55 * growth_speed + 0.45 * root_energy` crosses the leap threshold, a probabilistic extra leap can add `4` scale steps.
7. Convert `leaf_energy` into a target location inside the batch register. The melody takes a one-step drift toward that target, so register changes influence the line without instantly snapping it to a graph.
8. Apply a small probabilistic pull back toward the batch center note. This prevents the contour from sticking at the top or bottom of the register after large moves.
9. Clamp the result to the batch register.
10. Calculate velocity from `vitality` over the configured MIDI range `35-118`, then apply the section velocity multiplier.
11. Emit the melody event with pitch, beat position, duration, velocity, and the source signal values used to create it.

The rhythm gate uses the same density value. The rest probability is high when `growth_speed` is low and falls as density rises:

```text
rest_probability = 0.48 - density * (0.48 - 0.02)
```

Density also controls how many possible note starts exist within a beat. Low density allows only the main beat. Medium density can add the half-beat. High density can add a sixteenth-position pickup at `0.75` beats. This is why active growth produces not only louder notes, but more rhythmic surface.

Durations are shortened as density increases. Sparse areas can sustain for about a beat or more; dense areas use shorter notes so the texture does not blur. This keeps the rhythmic mapping audible instead of turning high-growth passages into overlapping sustained tones.

After this data-driven contour is generated, harmony correction adjusts some pitches to nearby active chord tones, especially on strong beats. The original generated pitch and the adjustment are both kept in `outputs/events/midi_events.csv` as `original_pitch_midi` and `pitch_adjustment`. This means the melody remains data-shaped, but it is not left harmonically arbitrary.

The contour visualization makes this process inspectable:

```text
outputs/figures/melody_contour_mapping.png
```

In that figure, the dark line is the generated melody contour, the pale line is the `leaf_energy` register target, point color shows whether `growth_mass` is above or below its local average, and point size shows the generated scale-step distance.

## Batch Identity

The three batches are kept separate all the way through the music. They are not averaged into one plant curve.

| Batch | Mean `leaf_energy` | Mean `growth_mass` | Instrument | Register Role |
|---|---:|---:|---|---|
| `R1` | `0.449` | `0.418` | Marimba | lower/mid voice |
| `R2` | `0.377` | `0.377` | Harp | mid voice |
| `R3` | `0.381` | `0.341` | Celesta | upper voice |

The batches have different signal profiles, but the differences are not dramatic enough to justify three unrelated musical languages. The design response is to keep one shared scale and harmony while giving each batch its own instrument and register. That makes the piece readable as one ecosystem with three plant traces inside it.

## Register And Leaf Energy

`leaf_energy` controls register because leaf area, leaf count, and chlorophyll are the most visibly upward-facing parts of the dataset. This is not a claim that “more leaves equals higher pitch” in nature. It is a design analogy: more leaf structure opens vertical space in the music.

The current output reflects that separation clearly. The batch melody ranges are:

| Stem | MIDI Range |
|---|---|
| `R1` | `36-74` |
| `R2` | `55-81` |
| `R3` | `62-88` |

The ranges overlap enough to sound related, but they are separated enough that the listener can follow the three batches as different strands.

## Rhythm And Dynamics

`growth_speed` controls note density because it measures recent change. When the plant-derived mass is changing more quickly, the melody is allowed to produce more events. This is visible in the output metrics: the correlation between `growth_speed` and note density is about `0.64`.

`vitality` controls velocity because it combines height, chlorophyll, and leaf area: measurements that suggest a stronger visible plant state. The generated result keeps this relationship strong; the correlation between `vitality` and velocity is about `0.81`.

These correlations are not the musical goal by themselves, but they are useful checks. They show that the musical surface is still responding to the intended plant signals after harmony correction, accompaniment, and rendering.

## Form

The piece uses four sections:

| Section | Bars | Density Multiplier | Velocity Multiplier | Reason |
|---|---:|---:|---:|---|
| Germination | `1-16` | `0.45` | `0.72` | Start sparse so the listener can learn the three voices. |
| Growth | `17-40` | `0.90` | `1.02` | Let the data speak with little exaggeration. |
| Bloom | `41-60` | `1.90` | `1.24` | Emphasize the most animated central span. |
| Settling | `61-75` | `0.48` | `0.82` | Thin the texture before the final resolution. |

This form is not independent of the data. It is a listening frame around the data. Without it, the output would be locally correct but dramatically flat: many rows translated faithfully, but no large-scale musical arc.

The section metrics confirm the intended contrast. Bloom has the highest note density at `34.5` events per bar and the highest mean velocity, while germination and settling are much lighter.

## Tonal World

The piece uses `D Dorian` with chords such as:

```text
Dm9, G9, Cmaj7, Fmaj7, Am7
```

`D Dorian` was chosen because it gives the piece a minor center without closing the harmony too tightly. The raised sixth supports `G`-based color, so the music can brighten during active or bloom-like passages without leaving the same modal world.

The melody is adjusted toward the active chord after generation. This keeps the plant-driven line from sounding random while preserving the contour. The current melody chord-tone fit is about `98.8%`, which means the generated plant voices are strongly integrated with the harmonic plan.

## Accompaniment

The accompaniment is deliberately separated from the plant melody. It is a continuous broken-chord background, not another plant voice.

The basic pattern is:

```text
low chord tone -> middle chord tone -> high chord tone -> middle chord tone
```

This solves a practical problem. Three data-driven melodic stems can become pointillistic: interesting as data, but thin as music. The accompaniment supplies harmonic continuity underneath them while staying out of the way. It also makes the chord plan audible without asking the plant voices to carry every harmonic function themselves.

## What The Listener Should Notice

The listener should hear three related plant lines, not one averaged plant.

The denser and louder moments should line up with higher recent growth activity and vitality.

The register should feel connected to leaf-related growth, especially in the separation between the lower `R1` voice and the brighter `R3` voice.

The ending should feel composed rather than merely terminated: the data stream stops, then the music resolves to `D3`.
