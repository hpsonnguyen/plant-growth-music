# Technical Implementation Plan

## Goal

Build and maintain a configurable Python pipeline that converts plant growth data into MIDI files, renders a playable demo, and produces musical/data visualizations for evaluating the data-to-music translation.

The current implementation is complete and executable with:

```bash
python scripts/run_all.py --config config/default.yml
```

## Current Project Structure

```text
plant-music/
  config/
    default.yml
    scales.yml
    instruments.yml
  data/
    Greenhouse Plant Growth Metrics.csv
    metadata.txt
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

## Main Outputs

- `outputs/midi/plant_music_full.mid`
- `outputs/midi/R1_stem.mid`
- `outputs/midi/R2_stem.mid`
- `outputs/midi/R3_stem.mid`
- `outputs/audio/plant_music_demo.wav`
- `outputs/events/midi_events.csv`
- `outputs/processed/beat_features.csv`
- `outputs/processed/beat_features_raw.csv`
- `outputs/figures/growth_signals.png`
- `outputs/figures/piano_roll.png`
- `outputs/figures/pitch_vs_growth.png`
- `outputs/figures/velocity_density.png`
- `outputs/figures/stem_comparison.png`
- `outputs/metrics.json`

## Dependencies

The implementation uses:

- `pandas`
- `numpy`
- `pyyaml`
- `matplotlib`
- Optional: `fluidsynth` system binary and a GM SoundFont

The MIDI writer is implemented directly in `src/plant_music/midi.py`, so `mido` is useful for validation but not required for generation.

Audio rendering behavior:

- If FluidSynth and the configured SoundFont are available, render through FluidSynth.
- If FluidSynth or the SoundFont is unavailable, render a fallback sine/harmonic WAV demo.

## Current Configurable Mapping

All mapping decisions live in `config/default.yml`.

Current musical setup:

```yaml
timeline:
  bpm: 90
  bars: 75
  beats_per_bar: 4
  rows_per_beat: 100

scale:
  root: "D"
  mode: "dorian"
```

Current stems:

```yaml
stems:
  R1:
    program: 12
    register_min: "C2"
    register_max: "D5"
    center_note: "D3"
  R2:
    program: 46
    register_min: "G3"
    register_max: "A5"
    center_note: "D4"
  R3:
    program: 8
    register_min: "D4"
    register_max: "E6"
    center_note: "A4"
```

Current dramatic pitch controls:

```yaml
mapping:
  pitch:
    method: "contour_walker"
    register_signal: "leaf_energy"
    motion_signal: "growth_speed"
    direction_signal: "growth_mass"
    tension_signal: "root_energy"
    return_to_center_strength: 0.08
    max_scale_steps_per_event: 5
    leap_threshold: 0.72
    leap_probability: 0.45
    leap_steps: 4
```

Current rhythm controls:

```yaml
mapping:
  rhythm:
    density_signal: "growth_speed"
    duration_signal: "growth_mass"
    density_floor: 0.18
    density_curve_power: 0.55
    rest_probability_min: 0.02
    rest_probability_max: 0.48
    allow_sixteenths: true
```

Current dynamics and form:

```yaml
mapping:
  velocity:
    signal: "vitality"
    min: 35
    max: 118
    smoothing_window: 3
  form:
    enabled: true
    sections:
      - {name: "germination", start_bar: 1, end_bar: 16, density_multiplier: 0.45, velocity_multiplier: 0.72}
      - {name: "growth", start_bar: 17, end_bar: 40, density_multiplier: 0.90, velocity_multiplier: 1.02}
      - {name: "bloom", start_bar: 41, end_bar: 60, density_multiplier: 1.90, velocity_multiplier: 1.24}
      - {name: "settling", start_bar: 61, end_bar: 75, density_multiplier: 0.48, velocity_multiplier: 0.82}
```

Current rendering:

```yaml
render:
  enabled: true
  soundfont: "/usr/share/sounds/sf2/FluidR3_GM.sf2"
  sample_rate: 44100
  gain: 2.2
```

## Module Responsibilities

### `config.py`

- Load YAML config.
- Validate required sections.
- Resolve project-relative paths.
- Create output directories.

### `data.py`

- Load `data/Greenhouse Plant Growth Metrics.csv`.
- Validate required columns.
- Convert row sequence into beat windows.
- Aggregate each batch per beat.
- Export `outputs/processed/beat_features_raw.csv`.

### `signals.py`

- Normalize raw data with robust percentile min-max scaling.
- Compute derived signals from configurable weighted feature groups.
- Compute `growth_speed` from absolute differences of smoothed `growth_mass`.
- Export `outputs/processed/beat_features.csv`.

### `scales.py`

- Parse note names.
- Convert notes to MIDI values.
- Generate legal notes for a register and scale.
- Support `minor_pentatonic`, `dorian`, and `major_pentatonic` modes.

### `mapping.py`

- Convert beat-level plant signals into note events.
- Apply form multipliers.
- Apply density floor and density curve for stronger rhythmic contrast.
- Generate contour-walker pitch decisions.
- Trigger occasional high-tension leaps from `growth_speed` and `root_energy`.
- Log all event-level mapping decisions.

### `midi.py`

- Write standard MIDI files using a built-in MIDI writer.
- Export full arrangement and isolated stem files.
- Export `outputs/events/midi_events.csv`.

### `render.py`

- Render with FluidSynth using configurable `render.gain`.
- Fall back to an internal sine/harmonic synth if FluidSynth is unavailable.
- Export `outputs/audio/plant_music_demo.wav`.

### `visualize.py`

- Generate PNG visualizations with `matplotlib`.
- Export metrics to `outputs/metrics.json`.
- Provide fallback SVG/CSV diagnostics if plotting dependencies are unavailable.

## Commands

Run everything:

```bash
python scripts/run_all.py --config config/default.yml
```

Only regenerate MIDI/events/features:

```bash
python scripts/generate_midi.py --config config/default.yml
```

Only render audio from the current MIDI/events:

```bash
python scripts/render_demo.py --config config/default.yml
```

Only regenerate visualizations from current outputs:

```bash
python scripts/make_visualizations.py --config config/default.yml
```

## Current Verification Snapshot

Latest run after dramatic remapping:

- Duration: `200.0` seconds
- WAV render: FluidSynth, stereo, about `199.3` seconds
- Event counts: `R1 = 203`, `R2 = 197`, `R3 = 206`
- Pitch ranges: `R1 = 36-74`, `R2 = 55-81`, `R3 = 62-88`
- Mean section velocities: germination about `49`, growth about `77`, bloom about `96`, settling about `49`
- Notes per bar: germination about `5.6`, growth about `8.8`, bloom about `9.7`, settling about `7.3`
- Each stem has balanced upward and downward pitch motion.
- Each stem now includes large leaps, including octave-scale gestures.

## Acceptance Checklist

- `python scripts/run_all.py --config config/default.yml` runs end-to-end.
- Full MIDI and isolated stems are generated.
- Playable WAV demo is generated.
- MIDI duration is strictly longer than 3 minutes.
- Mapping is configurable through YAML.
- Event log explains note-level decisions.
- Figures and metrics make the data-to-music relationship inspectable.
- The current mapping is more dramatic than the first pass while still connected to plant-derived signals.
