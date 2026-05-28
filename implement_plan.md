# Technical Implementation Plan

## Goal

Build a configurable Python pipeline that converts plant growth data into MIDI files, renders a playable demo, and produces musical/data visualizations that help evaluate whether the generated music meaningfully represents plant growth.

The system should support experimentation with mapping decisions such as scale, tempo, row-to-beat resolution, derived signals, pitch logic, rhythm logic, velocity logic, instruments, and output formats.

## Deliverables

The project should produce the following outputs:

- `outputs/midi/plant_music_full.mid`: full three-stem MIDI arrangement
- `outputs/midi/R1_stem.mid`: isolated MIDI stem for batch `R1`
- `outputs/midi/R2_stem.mid`: isolated MIDI stem for batch `R2`
- `outputs/midi/R3_stem.mid`: isolated MIDI stem for batch `R3`
- `outputs/audio/plant_music_demo.wav`: playable rendered demo
- `outputs/events/midi_events.csv`: event-level mapping log from plant data to musical decisions
- `outputs/processed/beat_features.csv`: normalized and derived beat-level features
- `outputs/figures/growth_signals.png`: growth signals over musical time
- `outputs/figures/piano_roll.png`: generated MIDI piano-roll visualization
- `outputs/figures/pitch_vs_growth.png`: pitch contour compared with growth-derived signals
- `outputs/figures/velocity_density.png`: MIDI velocity and rhythmic density over time
- `outputs/figures/stem_comparison.png`: side-by-side comparison of the three plant batches/stems

## Recommended Project Structure

```text
plant-music/
  Greenhouse Plant Growth Metrics.csv
  implement_plan.md
  design_plan.md
  config/
    default.yml
    scales.yml
    instruments.yml
  src/
    plant_music/
      __init__.py
      config.py
      data.py
      signals.py
      scales.py
      mapping.py
      midi.py
      render.py
      visualize.py
      pipeline.py
  scripts/
    generate_midi.py
    render_demo.py
    make_visualizations.py
    run_all.py
  outputs/
    midi/
    audio/
    events/
    processed/
    figures/
```

## Dependencies

Current environment already includes `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, and `scikit-learn`.

Add MIDI/audio dependencies:

```yaml
dependencies:
  - python=3.11
  - pandas
  - numpy
  - matplotlib
  - seaborn
  - scipy
  - scikit-learn
  - pyyaml
  - pip
  - pip:
      - mido
      - pretty_midi
      - midi2audio
```

For audio rendering, install a SoundFont and FluidSynth system package if needed:

```text
fluidsynth
GeneralUser GS.sf2 or another GM-compatible SoundFont
```

If FluidSynth is unavailable, the pipeline should still export MIDI and visualizations.

## Configuration Design

All major music-mapping choices should live in `config/default.yml`.

Example configuration:

```yaml
project:
  input_csv: "Greenhouse Plant Growth Metrics.csv"
  output_dir: "outputs"
  random_seed: 7

timeline:
  bpm: 90
  meter_numerator: 4
  meter_denominator: 4
  bars: 75
  beats_per_bar: 4
  rows_per_beat: 100
  ticks_per_beat: 480

scale:
  root: "D"
  mode: "minor_pentatonic"
  allowed_pitch_classes: [2, 5, 7, 9, 0]

stems:
  R1:
    track_name: "R1_marimba"
    channel: 0
    program: 12
    register_min: "D3"
    register_max: "C5"
    center_note: "A3"
  R2:
    track_name: "R2_harp"
    channel: 1
    program: 46
    register_min: "A3"
    register_max: "G5"
    center_note: "D4"
  R3:
    track_name: "R3_celesta"
    channel: 2
    program: 8
    register_min: "D4"
    register_max: "C6"
    center_note: "A4"

derived_signals:
  growth_mass:
    method: "weighted_mean"
    features: {AWWGV: 0.35, ADWV: 0.20, AWWR: 0.25, ADWR: 0.20}
  leaf_energy:
    method: "weighted_mean"
    features: {ALAP: 0.45, ANPL: 0.25, ACHP: 0.30}
  root_energy:
    method: "weighted_mean"
    features: {ARL: 0.40, ARD: 0.30, PDMRG: 0.30}
  vitality:
    method: "weighted_mean"
    features: {PHR: 0.40, ACHP: 0.30, ALAP: 0.30}
  growth_speed:
    method: "diff_abs"
    source: "growth_mass"
    smoothing_window: 5

mapping:
  pitch:
    method: "contour_walker"
    register_signal: "leaf_energy"
    motion_signal: "growth_speed"
    direction_signal: "growth_mass"
    tension_signal: "root_energy"
    return_to_center_strength: 0.18
    max_scale_steps_per_event: 3
  rhythm:
    density_signal: "growth_speed"
    duration_signal: "growth_mass"
    rest_probability_min: 0.05
    rest_probability_max: 0.35
    allow_sixteenths: true
  velocity:
    signal: "vitality"
    min: 45
    max: 95
    smoothing_window: 3
  form:
    enabled: true
    sections:
      - {name: "germination", start_bar: 1, end_bar: 16, density_multiplier: 0.65, velocity_multiplier: 0.80}
      - {name: "growth", start_bar: 17, end_bar: 40, density_multiplier: 1.00, velocity_multiplier: 1.00}
      - {name: "bloom", start_bar: 41, end_bar: 60, density_multiplier: 1.25, velocity_multiplier: 1.08}
      - {name: "settling", start_bar: 61, end_bar: 75, density_multiplier: 0.70, velocity_multiplier: 0.88}

render:
  enabled: true
  soundfont: "soundfonts/GeneralUser_GS.sf2"
  sample_rate: 44100
```

## Pipeline Overview

The pipeline should run in five stages:

1. Load and aggregate plant data.
2. Normalize and derive musical control signals.
3. Generate MIDI events from configurable mappings.
4. Export MIDI files and optional rendered audio.
5. Generate visualizations and diagnostic files.

Primary command:

```bash
python scripts/run_all.py --config config/default.yml
```

Individual commands:

```bash
python scripts/generate_midi.py --config config/default.yml
python scripts/render_demo.py --config config/default.yml
python scripts/make_visualizations.py --config config/default.yml
```

## Stage 1: Data Loading And Beat Aggregation

Module: `src/plant_music/data.py`

Responsibilities:

- Load `Greenhouse Plant Growth Metrics.csv`.
- Validate required columns.
- Preserve original row sequence as the time dimension.
- Assign each row to a beat using `row_index // rows_per_beat`.
- Keep only the configured number of beats.
- Group by `beat_index` and `Random` batch.
- Aggregate numeric features by mean.

Expected output:

```text
outputs/processed/beat_features_raw.csv
```

Important columns:

```text
beat_index, bar_index, beat_in_bar, Random, ACHP, PHR, AWWGV, ALAP, ANPL, ARD, ADWR, PDMVG, ARL, AWWR, ADWV, PDMRG
```

## Stage 2: Signal Derivation

Module: `src/plant_music/signals.py`

Responsibilities:

- Normalize configured numeric features per feature across the full dataset.
- Optionally normalize per batch if configured.
- Compute weighted derived signals from config.
- Smooth selected signals with rolling windows.
- Compute difference-based signals such as `growth_speed`.
- Clamp all musical control signals to `0.0-1.0`.

Recommended normalization:

```text
robust_minmax = clip((x - q05) / (q95 - q05), 0, 1)
```

Use robust percentiles instead of raw min/max to prevent outliers from dominating the mapping.

Expected output:

```text
outputs/processed/beat_features.csv
```

## Stage 3: Musical Mapping

Module: `src/plant_music/mapping.py`

Responsibilities:

- Convert beat-level signals into note-level musical decisions.
- Generate one event stream per batch/stem.
- Use deterministic randomness with the configured seed for repeatable results.
- Write every decision into an event log for interpretability.

### Pitch Mapping

Use `contour_walker` as the default pitch method.

Inputs:

- `register_signal`: moves the general range up/down.
- `motion_signal`: controls step size.
- `direction_signal`: compares current value to rolling local average to bias up/down.
- `tension_signal`: increases probability of skips or leaps.
- `return_to_center_strength`: prevents drifting permanently upward or downward.

Algorithm:

1. Convert the configured scale and register into a list of legal MIDI notes.
2. Start from the configured center note.
3. For each event, calculate local direction from the direction signal.
4. Calculate scale-step movement from motion and tension.
5. Apply form influence if enabled.
6. Add a weak pull toward the target register implied by `register_signal`.
7. Add a weak pull back toward the stem center note.
8. Clamp to the stem register.
9. Quantize to the nearest legal scale note.

The pitch log should include:

```text
source_signal_value, local_average, direction, scale_steps, raw_pitch, quantized_pitch
```

### Rhythm Mapping

Use `growth_speed` as the default density signal.

Suggested mapping:

| Density Signal | Rhythmic Result |
|---|---|
| `0.00-0.25` | Sparse half notes or rests |
| `0.25-0.50` | Quarter notes |
| `0.50-0.75` | Eighth notes |
| `0.75-1.00` | Eighth notes with occasional sixteenth ornaments |

The rhythm mapper should decide:

- Whether a note occurs at a beat position.
- Whether the beat is subdivided.
- Note duration in beats.
- Rest probability.

### Velocity Mapping

Default velocity formula:

```text
velocity = min_velocity + vitality * (max_velocity - min_velocity)
```

Apply optional smoothing and form-section multipliers.

### Duration Mapping

Use `growth_mass` as the default duration/body signal.

Suggested behavior:

- Higher `growth_mass`: longer and more legato notes.
- Lower `growth_mass`: shorter notes and more space.

## Stage 4: MIDI Export

Module: `src/plant_music/midi.py`

Responsibilities:

- Create one MIDI track per plant batch.
- Assign General MIDI program numbers from config.
- Write tempo and time signature metadata.
- Convert beats to ticks using `ticks_per_beat`.
- Export a full combined MIDI file.
- Export one isolated stem MIDI file per batch.
- Export `midi_events.csv` with all mapping decisions.

Recommended MIDI library:

```text
mido
```

Event log columns:

```text
event_id, batch, track_name, beat_start, beat_duration, bar_index, section,
source_row_start, source_row_end, pitch_midi, pitch_name, velocity, channel,
program, scale, register_signal, motion_signal, direction_signal, tension_signal,
growth_mass, leaf_energy, root_energy, vitality, growth_speed
```

## Stage 5: Playable Demo Rendering

Module: `src/plant_music/render.py`

Responsibilities:

- Render `plant_music_full.mid` to `plant_music_demo.wav` when FluidSynth and a SoundFont are available.
- Fail gracefully if rendering dependencies are missing.
- Leave MIDI files usable even if WAV rendering fails.

Preferred rendering path:

```text
MIDI -> FluidSynth + SoundFont -> WAV
```

Fallback options:

- Export only MIDI.
- Render outside Python in a DAW.
- Render with another local MIDI synthesizer.

## Stage 6: Musical Visualization

Module: `src/plant_music/visualize.py`

Visualizations should be generated from both `beat_features.csv` and `midi_events.csv`.

### Growth Signals Plot

Output:

```text
outputs/figures/growth_signals.png
```

Purpose:

- Show `growth_mass`, `leaf_energy`, `root_energy`, `vitality`, and `growth_speed` over musical time.
- Split or color by batch.

Evaluation question:

```text
Does the plant-growth arc have visible sections that correspond to the musical form?
```

### Piano Roll Plot

Output:

```text
outputs/figures/piano_roll.png
```

Purpose:

- Show generated notes over time.
- Use color for batch/stem.
- Use marker opacity or size for velocity.

Evaluation question:

```text
Do the three stems create distinct but related musical lines?
```

### Pitch Vs Growth Plot

Output:

```text
outputs/figures/pitch_vs_growth.png
```

Purpose:

- Overlay pitch contour against mapped growth signals.
- Confirm pitch has ups and downs while still responding to data.

Evaluation question:

```text
Does the contour reflect plant activity without becoming a simple monotonic line?
```

### Velocity And Density Plot

Output:

```text
outputs/figures/velocity_density.png
```

Purpose:

- Plot note velocity and note density per bar.
- Compare against `vitality` and `growth_speed`.

Evaluation question:

```text
Do louder and denser musical moments correspond to higher plant vitality/activity?
```

### Stem Comparison Plot

Output:

```text
outputs/figures/stem_comparison.png
```

Purpose:

- Compare each batch's derived signals, pitch range, velocity, and event density.

Evaluation question:

```text
Are R1, R2, and R3 musically differentiated in a way that reflects their data differences?
```

## Evaluation Metrics

Add lightweight diagnostic metrics to the console output and optionally save them to:

```text
outputs/metrics.json
```

Recommended metrics:

| Metric | Purpose |
|---|---|
| Duration seconds | Confirms strict 3+ minute length |
| Events per stem | Confirms all three batches are represented |
| Pitch range per stem | Confirms register differentiation |
| Pitch direction balance | Confirms ups and downs exist |
| Mean velocity per section | Confirms form dynamics |
| Notes per bar per section | Confirms density arc |
| Correlation: vitality vs velocity | Checks dynamics mapping |
| Correlation: growth_speed vs note density | Checks rhythm mapping |
| Correlation: leaf_energy vs pitch register | Checks pitch-register mapping |

The goal is not to maximize correlations blindly. The metrics should verify that musical behavior is meaningfully connected to plant data while still sounding composed.

## Implementation Order

1. Create project directories.
2. Add config files.
3. Update environment dependencies.
4. Implement `config.py` for YAML loading and validation.
5. Implement `data.py` for CSV loading and beat aggregation.
6. Implement `signals.py` for normalization and derived signals.
7. Implement `scales.py` for note parsing, scale generation, and quantization.
8. Implement `mapping.py` for pitch, rhythm, duration, velocity, and form decisions.
9. Implement `midi.py` for full MIDI and stem MIDI export.
10. Implement `visualize.py` for diagnostic plots.
11. Implement `render.py` for optional WAV rendering.
12. Add scripts for `generate_midi`, `render_demo`, `make_visualizations`, and `run_all`.
13. Run the full pipeline with `config/default.yml`.
14. Review MIDI, WAV, event CSV, and figures.
15. Iterate on mapping config without changing code.

## Minimum Viable Demo

The first working version should produce:

- One full MIDI file with three tracks.
- Three isolated stem MIDI files.
- One event log CSV.
- One processed beat-feature CSV.
- At least three figures: growth signals, piano roll, and pitch-vs-growth.

Audio rendering can be considered optional for the first pass if local FluidSynth/SoundFont setup is unavailable.

## Acceptance Checklist

The technical implementation is complete when:

- `python scripts/run_all.py --config config/default.yml` runs end-to-end.
- The generated MIDI duration is strictly longer than 3 minutes.
- The full MIDI contains exactly three main musical stems.
- Stem files are exported separately.
- The pitch material is quantized to the configured scale.
- Mapping choices can be changed from YAML config.
- Derived signals can be changed from YAML config.
- The event log explains how each musical event was produced.
- Visualizations make the data-to-music relationship inspectable.
- The pipeline fails gracefully if audio rendering is unavailable.

## Recommended First Experiment

Use this configuration for the first end-to-end run:

```text
BPM: 90
Bars: 75
Rows per beat: 100
Scale: D minor pentatonic
Pitch: contour_walker
Rhythm signal: growth_speed
Velocity signal: vitality
Duration signal: growth_mass
Register signal: leaf_energy
Instruments: marimba, harp, celesta
```

After the first render, evaluate:

- Does the piece feel like it grows over time?
- Are the three stems distinguishable?
- Does the pitch contour move naturally rather than simply rising?
- Do high-growth sections sound more active?
- Do the visualizations support the musical interpretation?
