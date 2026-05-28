# Plant Music Design Plan

## Goal

Create a 3-4 minute musical piece from plant growth data by mapping quantified growth features into MIDI events. The piece should use three musical stems, one for each plant batch, and should express plant growth through rhythm, dynamics, pitch, and musical form.

## Source Data

Use `Greenhouse Plant Growth Metrics.csv` as the primary dataset.

The dataset contains:

- `30,000` rows
- Three plant batches: `R1`, `R2`, `R3`
- Six experimental classes: `SA`, `SB`, `SC`, `TA`, `TB`, `TC`
- Numeric growth features such as `PHR`, `ALAP`, `ACHP`, `AWWGV`, `ANPL`, `ARL`, `ARD`, and related root/vegetative measurements

Each plant batch becomes one musical stem:

| Batch | Stem | Suggested Role |
|---|---|---|
| `R1` | Stem 1 | Lower/mid melodic body |
| `R2` | Stem 2 | Mid-register harmonic motion |
| `R3` | Stem 3 | Upper-register melodic detail |

## Musical Timeline

Recommended timeline:

- Meter: `4/4`
- Tempo: `90 BPM`
- Length: `75 bars`
- Total beats: `300`
- Target duration: `3 minutes 20 seconds`

This gives a strict duration above 3 minutes while remaining close to the requested 3-4 minute range.

Mapping:

```text
30,000 rows / 300 beats = 100 rows per beat
300 beats / 90 BPM = 3.33 minutes
```

Each beat should represent an aggregation window of approximately `100` rows.

## Data Preprocessing

1. Load the CSV with `pandas`.
2. Add a global row-sequence index.
3. Convert row sequence into beat windows.
4. Group by `beat_index` and `Random` batch.
5. Aggregate numeric growth features using the mean.
6. Normalize selected features to `0.0 - 1.0`.
7. Smooth noisy values with a rolling average.
8. Compute first differences to estimate growth change and local momentum.

Recommended derived signals:

| Derived Signal | Formula Idea | Musical Use |
|---|---|---|
| `growth_mass` | Mean of `AWWGV`, `ADWV`, `AWWR`, `ADWR` | Note duration and body |
| `leaf_energy` | Mean of `ALAP`, `ANPL`, `ACHP` | Register and brightness |
| `root_energy` | Mean of `ARL`, `ARD`, `PDMRG` | Grounding and lower movement |
| `growth_speed` | Difference of smoothed `PHR` or `growth_mass` | Rhythmic density and pitch motion |
| `vitality` | Weighted blend of `PHR`, `ACHP`, `ALAP` | MIDI velocity and intensity |

## Core Musical Problem

Plant growth data is often monotonic or mostly directional. If absolute growth is mapped directly to pitch, the melody becomes a simple upward line, which is predictable and musically weak.

The solution is to avoid direct absolute-growth-to-pitch mapping. Instead, use a contour-based melodic system.

## Pitch Mapping Strategy

Use plant data to control a melodic contour rather than direct pitch height.

Recommended scale:

```text
D minor pentatonic: D, F, G, A, C
```

This scale is stable, organic, and forgiving when three independent stems overlap.

Alternative scale:

```text
D Dorian: D, E, F, G, A, B, C
```

Use D Dorian if more melodic variety is needed.

### Register Assignment

| Stem | Batch | Register |
|---|---|---|
| Stem 1 | `R1` | `D3-C5` |
| Stem 2 | `R2` | `A3-G5` |
| Stem 3 | `R3` | `D4-C6` |

### Contour-Based Pitch Walker

For each stem:

1. Start near a central note in the assigned register.
2. Use normalized growth level to influence the general register.
3. Use growth speed to determine motion size.
4. Use local deviation from a rolling average to determine direction.
5. Quantize every pitch to the chosen scale.
6. Clamp notes to the assigned register.

Suggested movement rules:

| Growth Behavior | Pitch Behavior |
|---|---|
| Low growth speed | Repeat note or move by step |
| Medium growth speed | Step or small skip |
| High growth speed | Larger skip or brief leap |
| Above local average | Bias upward |
| Below local average | Bias downward |
| Stable/flat movement | Sustain, repeat, or return toward center |

This keeps the data meaningful while allowing the melody to rise and fall expressively.

## Rhythm Mapping Strategy

Use row sequence as the time base, but allow plant activity to shape rhythmic density.

Base grid:

- Quarter notes
- Eighth notes
- Occasional sixteenth-note ornaments

Suggested rhythm mapping:

| Normalized Growth Speed | Rhythm Behavior |
|---|---|
| `0.00-0.25` | Half notes, sustained notes, more rests |
| `0.25-0.50` | Quarter notes |
| `0.50-0.75` | Eighth notes |
| `0.75-1.00` | Eighth notes with syncopated sixteenth ornaments |

This makes the music feel as if it accelerates and becomes more active when the plant data is more active.

## Dynamics Mapping Strategy

Use `vitality` and growth intensity to control MIDI velocity.

Recommended mapping:

```text
MIDI velocity = 45 + normalized_vitality * 50
```

Expected range:

- Quiet: `45`
- Medium: `70`
- Strong: `95`

Smooth the velocity curve to prevent jittery dynamics.

## Instrumentation

Recommended instrument palette:

| Stem | Suggested Instrument | Musical Function |
|---|---|---|
| `R1` | Marimba or kalimba | Warm organic pulse |
| `R2` | Harp or nylon guitar | Plucked harmonic motion |
| `R3` | Celesta, bell synth, or flute | Bright upper growth detail |

Alternative plant-like palette:

| Stem | Suggested Instrument |
|---|---|
| `R1` | Low wood marimba |
| `R2` | Plucked harp |
| `R3` | Glassy bell pad |

## Musical Form

Shape the piece into a clear growth arc.

| Section | Bars | Character |
|---|---:|---|
| Germination | `1-16` | Sparse notes, low velocity, small intervals |
| Growth | `17-40` | More density, stronger pulse, wider movement |
| Bloom | `41-60` | Highest density, strongest dynamics, widest register |
| Settling | `61-75` | Longer notes, thinning texture, return toward tonal center |

The form can be controlled with a global `form_factor` based on row position.

Examples:

- Early section: reduce note density and velocity.
- Middle section: allow full rhythmic and melodic movement.
- Late section: gradually reduce density and pull pitches back toward central scale degrees.

## Feature-To-Music Mapping

| Data Feature | Musical Role |
|---|---|
| `PHR` | Growth speed, rhythmic density, phrase momentum |
| `ALAP` | Register, openness, melodic height tendency |
| `ACHP` | Brightness, dynamics, articulation strength |
| `AWWGV` | Note duration, musical weight/body |
| `ANPL` | Ornaments, repetitions, local activity |
| `ARL` | Grounding, lower-register tendency |
| `PDMRG` | Tension, probability of larger intervals |

## Implementation Steps

1. Load and inspect the CSV.
2. Assign each row to a beat window.
3. Aggregate each batch per beat.
4. Normalize, smooth, and derive musical control signals.
5. Create one MIDI track per batch.
6. Generate notes using the contour-based pitch walker.
7. Map growth speed to rhythm and density.
8. Map vitality to MIDI velocity.
9. Quantize all notes to the selected scale.
10. Export the result as a MIDI file.
11. Export a companion event log showing the data-to-MIDI mapping.
12. Render the MIDI using chosen instruments in a DAW or a Python audio workflow.

## Validation Checklist

The final piece should satisfy the following:

- Duration is strictly longer than 3 minutes.
- Duration is close to 3-4 minutes.
- There are exactly three primary stems.
- Each stem corresponds to one plant batch.
- Pitch has meaningful ups and downs.
- All pitches are quantized to the chosen scale.
- Growth affects rhythm, dynamics, and pitch behavior.
- The piece has an audible formal arc.
- The mapping remains explainable from plant data to music.

## Recommended Starting Configuration

Use this configuration for the first full implementation:

```text
Tempo: 90 BPM
Meter: 4/4
Length: 75 bars
Scale: D minor pentatonic
Rows per beat: 100
Tracks: 3
Pitch method: contour-based pitch walker
Dynamics: normalized vitality to MIDI velocity
Rhythm: growth speed to density and duration
```

This configuration should produce a musical, organic, and data-driven piece while avoiding the dullness of directly mapping monotonic growth to steadily rising pitch.
