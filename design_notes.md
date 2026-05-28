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

## Why Pitch Is A Contour, Not A Direct Graph

The pitch generator is a contour walker. It keeps a current pitch, then moves up, down, or stays close depending on the data.

This choice comes from looking at the kind of data we have. Growth measurements are often directional or slowly varying. A literal mapping from growth to pitch would overstate long-term accumulation and understate local changes. The contour walker instead asks three smaller musical questions:

| Mapping Question | Data Signal |
|---|---|
| Should the line tend upward or downward? | `growth_mass` compared with its local average |
| How large should the next move be? | mostly `growth_speed`, with some `root_energy` |
| Where should the line sit in the register? | `leaf_energy` |

This produces melodic motion without losing the plant signal. The generated melody can rise, fall, pause, and return, while still being constrained by the measured growth behavior.

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
