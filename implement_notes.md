# Implementation Notes

## Overview

The project is a Python pipeline that converts greenhouse plant growth data into MIDI, renders a WAV demo, and exports a compact set of showcase figures.

Run the full pipeline with:

```bash
python scripts/run_all.py --config config/default.yml
```

## Main Inputs

```text
data/Greenhouse Plant Growth Metrics.csv
config/default.yml
```

The CSV provides the plant measurements. The YAML config controls the timeline, scale, stems, derived signals, pitch/rhythm/dynamics mapping, harmony, accompaniment, rendering, and final resolution note.

## Main Outputs

```text
outputs/audio/plant_music_demo.wav
outputs/midi/plant_music_full.mid
outputs/midi/R1_stem.mid
outputs/midi/R2_stem.mid
outputs/midi/R3_stem.mid
outputs/midi/ACCOMP_stem.mid
outputs/events/midi_events.csv
outputs/events/harmony_plan.csv
outputs/processed/beat_features.csv
outputs/metrics.json
outputs/figures/growth_to_intensity.png
outputs/figures/leaf_to_register.png
outputs/figures/harmony_to_accompaniment.png
```

## Pipeline

```text
CSV data
  -> beat aggregation
  -> normalized plant signals
  -> melodic event generation
  -> harmony planning
  -> chord-aware melody adjustment
  -> broken-chord accompaniment
  -> MIDI export
  -> audio render
  -> showcase figures and metrics
```

## Modules

| Module | Responsibility |
|---|---|
| `config.py` | Load YAML config, resolve paths, create output directories |
| `data.py` | Load CSV and aggregate rows into beat-level features |
| `signals.py` | Normalize raw features and derive musical control signals |
| `scales.py` | Convert notes, MIDI values, and scale pitch classes |
| `harmony.py` | Build the chord palette and generate the bar/segment harmony plan |
| `mapping.py` | Generate melody, adjust melody to harmony, add accompaniment and resolution |
| `midi.py` | Write full MIDI and isolated stem MIDI files |
| `render.py` | Render WAV using FluidSynth, with fallback synthesis if needed |
| `visualize.py` | Generate final showcase figures and metrics |
| `pipeline.py` | Orchestrate the full run |

## Event Types

The final event log contains:

| Event Type | Meaning |
|---|---|
| `melody` | Plant-generated melodic events for `R1`, `R2`, `R3` |
| `accompaniment` | Continuous broken-chord harmonic background |
| `resolution` | Final tonic note after the data timeline |

The event log includes chord labels, chord-tone roles, velocity, pitch, timing, source data signals, and MIDI channel/program information.

## Harmony And Accompaniment

Harmony is generated before final accompaniment. The harmony planner scores chords using melody fit, plant-derived values, section tendencies, and progression bias.

The accompaniment is a dedicated MIDI stem named `ACCOMP`. It is generated from the active chord and follows configurable patterns in `config/default.yml`.

The default pattern is:

```text
low -> middle -> high -> middle
```

Repeat variations and climax behavior are configurable:

```yaml
accompaniment:
  repeat_variations:
  climax_pattern:
  climax_thresholds:
  climax_step_multiplier:
  climax_velocity_multiplier:
```

## Rendering

If FluidSynth and the configured SoundFont are available, the project renders through FluidSynth.

If they are unavailable, `render.py` falls back to a simple internal synth so the pipeline still produces a playable WAV.

## Visualization

The final visualization set is intentionally small. Each figure pairs a data-side idea with its musical translation:

| Figure | Correspondence |
|---|---|
| `growth_to_intensity.png` | `growth_speed`/`vitality` to musical density/velocity |
| `leaf_to_register.png` | `leaf_energy` to melodic register |
| `harmony_to_accompaniment.png` | harmony plan to broken-chord accompaniment texture |

These are presentation figures, not exhaustive debugging plots.

## Notes For Future Work

- Add a second accompaniment style, such as wider left-hand arpeggios.
- Add pedaling or sustain-controller events for piano rendering.
- Export MusicXML or LilyPond for score inspection.
- Add a small CLI option for generating named variations from alternate configs.
