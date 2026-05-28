# Plant Music Design Plan

## Goal

Create a 3-4 minute musical piece from plant growth data by mapping quantified plant-growth features into MIDI events. The piece uses three musical stems, one for each plant batch, and expresses growth through rhythm, dynamics, register, melodic contour, and formal intensity.

## Current Data Insight

The visualization and metrics show that the plant-derived signals are meaningful but mostly moderate in range. `growth_speed` contains sharp localized spikes, while `growth_mass`, `leaf_energy`, `root_energy`, and `vitality` move more gradually. A literal mapping therefore produces a credible but conservative piece unless the mapping intentionally increases contrast.

Current design response:

- Use `growth_speed` as an event-density trigger, but apply a curve so small changes become audible.
- Use `vitality` for dynamics with a wider velocity range.
- Use `root_energy` and `growth_speed` together to trigger occasional dramatic leaps.
- Use wider stem registers so each batch has a stronger musical identity.
- Use form multipliers so bloom is clearly louder and denser than germination or settling.

## Source Data

Primary dataset:

```text
data/Greenhouse Plant Growth Metrics.csv
```

The dataset contains:

- `30,000` rows
- Three plant batches: `R1`, `R2`, `R3`
- Six experimental classes: `SA`, `SB`, `SC`, `TA`, `TB`, `TC`
- Growth features including `PHR`, `ALAP`, `ACHP`, `AWWGV`, `ANPL`, `ARL`, `ARD`, `ADWR`, `AWWR`, `ADWV`, and `PDMRG`

## Musical Timeline

Current timeline:

- Meter: `4/4`
- Tempo: `90 BPM`
- Length: `75 bars`
- Total beats: `300`
- Duration: `200 seconds`
- Rows per beat: `100`

This preserves the dataset row sequence as musical time:

```text
30,000 rows / 100 rows per beat = 300 beats
300 beats / 90 BPM = 200 seconds
```

## Scale

Current scale:

```text
D Dorian: D, E, F, G, A, B, C
```

D Dorian was chosen over the original minor pentatonic option because it gives the contour walker more melodic color while remaining stable across three independent stems.

## Stem Design

| Batch | Stem | Instrument | Register | Role |
|---|---|---|---|---|
| `R1` | Stem 1 | Marimba | `C2-D5` | Low/mid body, grounded growth force |
| `R2` | Stem 2 | Harp | `G3-A5` | Middle connective tissue and harmonic motion |
| `R3` | Stem 3 | Celesta | `D4-E6` | Upper growth detail and bright activity |

The current design intentionally widens the register of `R1` so the piece has more depth and contrast. `R3` remains bright but has enough room for climactic upper gestures.

## Derived Signals

| Signal | Formula Idea | Musical Role |
|---|---|---|
| `growth_mass` | Weighted mean of vegetative/root mass features | Duration, body, direction contour |
| `leaf_energy` | Weighted mean of `ALAP`, `ANPL`, `ACHP` | Register tendency |
| `root_energy` | Weighted mean of `ARL`, `ARD`, `PDMRG` | Tension and leap probability |
| `vitality` | Weighted mean of `PHR`, `ACHP`, `ALAP` | Velocity and intensity |
| `growth_speed` | Absolute diff of smoothed `growth_mass` | Rhythmic density and motion energy |

## Pitch Mapping

The piece uses a contour-based pitch walker rather than direct absolute-growth-to-pitch mapping.

Current pitch inputs:

- Register signal: `leaf_energy`
- Motion signal: `growth_speed`
- Direction signal: `growth_mass`
- Tension signal: `root_energy`

Current dramatic behavior:

- `max_scale_steps_per_event: 5`
- `return_to_center_strength: 0.08`
- `leap_threshold: 0.72`
- `leap_probability: 0.45`
- `leap_steps: 4`

This means normal growth produces stepwise or small-skip motion, while high motion plus high root tension can produce larger expressive leaps. The lower return-to-center strength lets phrases travel farther before resolving.

## Rhythm Mapping

Rhythm is driven by `growth_speed` with contrast enhancement.

Current rhythm behavior:

- `density_signal: growth_speed`
- `density_floor: 0.18`
- `density_curve_power: 0.55`
- `rest_probability_min: 0.02`
- `rest_probability_max: 0.48`
- Sixteenth ornaments are allowed.

The curve power makes low-to-mid `growth_speed` values more audible, while the floor prevents the piece from becoming empty during subtle growth periods.

## Dynamics Mapping

Velocity is driven by `vitality`.

Current velocity range:

```text
35-118
```

This wider range replaced the earlier conservative `45-95` range. The result is a more dramatic bloom section while preserving quieter germination and settling sections.

## Formal Arc

| Section | Bars | Density Multiplier | Velocity Multiplier | Character |
|---|---:|---:|---:|---|
| Germination | `1-16` | `0.45` | `0.72` | Sparse, quiet, tentative |
| Growth | `17-40` | `0.90` | `1.02` | Active but controlled |
| Bloom | `41-60` | `1.90` | `1.24` | Densest, loudest, most dramatic |
| Settling | `61-75` | `0.48` | `0.82` | Thinning and quieter |

The form is intentionally more interventionist than the raw data. The data still drives event details, but the form gives the listener a clear musical growth narrative.

## Current Output Diagnostics

After the current dramatic remapping:

- Duration: `200 seconds`
- MIDI tracks: tempo/meta track plus three plant stems
- Event counts: `R1 = 203`, `R2 = 197`, `R3 = 206`
- Bloom is the loudest section with mean velocity around `96`
- Germination and settling are much quieter with mean velocity around `49-50`
- Bloom is the densest section at about `9.7 notes/bar`
- Each stem has balanced upward and downward pitch motion
- Large leaps now occur in every stem, including octave-scale gestures

## Evaluation Outputs

Use these files to evaluate the translation:

- `outputs/figures/growth_signals.png`
- `outputs/figures/piano_roll.png`
- `outputs/figures/pitch_vs_growth.png`
- `outputs/figures/velocity_density.png`
- `outputs/figures/stem_comparison.png`
- `outputs/metrics.json`
- `outputs/events/midi_events.csv`

## Current Recommended Configuration

```text
Tempo: 90 BPM
Meter: 4/4
Length: 75 bars
Scale: D Dorian
Rows per beat: 100
Pitch method: contour walker with dramatic leap triggers
Rhythm: growth_speed with contrast curve and form multipliers
Dynamics: vitality mapped to velocity 35-118
Instruments: marimba, harp, celesta
Rendering: FluidSynth with gain 2.2 when available
```
