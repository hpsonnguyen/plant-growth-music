from __future__ import annotations

import math
import random

import pandas as pd

from .scales import legal_notes, midi_to_note, nearest_index, note_to_midi


def section_for_bar(config: dict, bar_index: int) -> dict:
    form = config["mapping"].get("form", {})
    if not form.get("enabled", False):
        return {"name": "full", "density_multiplier": 1.0, "velocity_multiplier": 1.0}
    for section in form.get("sections", []):
        if int(section["start_bar"]) <= bar_index <= int(section["end_bar"]):
            return section
    return {"name": "full", "density_multiplier": 1.0, "velocity_multiplier": 1.0}


def _event_offsets(density: float, allow_sixteenths: bool) -> list[float]:
    if density < 0.25:
        return [0.0]
    if density < 0.5:
        return [0.0]
    if density < 0.75:
        return [0.0, 0.5]
    return [0.0, 0.5, 0.75] if allow_sixteenths else [0.0, 0.5]


def _duration(duration_signal: float, density: float) -> float:
    if density < 0.25:
        return 1.5 if duration_signal > 0.5 else 1.0
    if density < 0.5:
        return 0.85 + duration_signal * 0.35
    if density < 0.75:
        return 0.45 + duration_signal * 0.25
    return 0.22 + duration_signal * 0.20


def generate_events(config: dict, features: pd.DataFrame) -> pd.DataFrame:
    rng = random.Random(int(config["project"].get("random_seed", 7)))
    pitch_cfg = config["mapping"]["pitch"]
    rhythm_cfg = config["mapping"]["rhythm"]
    velocity_cfg = config["mapping"]["velocity"]
    events = []
    event_id = 1

    for batch, stem in config["stems"].items():
        stem_df = features[features["Random"] == batch].sort_values("beat_index").reset_index(drop=True)
        notes = legal_notes(config, stem["register_min"], stem["register_max"])
        center = note_to_midi(stem["center_note"])
        note_index = nearest_index(notes, center)
        direction_series = stem_df[pitch_cfg["direction_signal"]].rolling(9, min_periods=1, center=True).mean()

        for i, row in stem_df.iterrows():
            section = section_for_bar(config, int(row["bar_index"]))
            raw_density = float(row[rhythm_cfg["density_signal"]])
            density_power = float(rhythm_cfg.get("density_curve_power", 1.0))
            density_floor = float(rhythm_cfg.get("density_floor", 0.0))
            density = max(density_floor, raw_density ** density_power) * float(section.get("density_multiplier", 1.0))
            density = max(0.0, min(1.0, density))
            rest_min = float(rhythm_cfg.get("rest_probability_min", 0.05))
            rest_max = float(rhythm_cfg.get("rest_probability_max", 0.35))
            rest_probability = rest_max - density * (rest_max - rest_min)
            if rng.random() < rest_probability:
                continue

            offsets = _event_offsets(density, bool(rhythm_cfg.get("allow_sixteenths", True)))
            for offset in offsets:
                if offset > 0 and rng.random() > density:
                    continue
                register_value = float(row[pitch_cfg["register_signal"]])
                motion_value = float(row[pitch_cfg["motion_signal"]])
                tension_value = float(row[pitch_cfg["tension_signal"]])
                direction_value = float(row[pitch_cfg["direction_signal"]])
                local_average = float(direction_series.iloc[i])
                direction = 1 if direction_value >= local_average else -1
                max_steps = int(pitch_cfg.get("max_scale_steps_per_event", 3))
                step_size = 1 + int(round((motion_value * 0.65 + tension_value * 0.35) * max_steps))
                drama_value = motion_value * 0.55 + tension_value * 0.45
                if drama_value >= float(pitch_cfg.get("leap_threshold", 1.1)) and rng.random() < float(pitch_cfg.get("leap_probability", 0.0)):
                    step_size += int(pitch_cfg.get("leap_steps", 0))
                target_index = round(register_value * (len(notes) - 1))
                center_index = nearest_index(notes, center)
                drift = int(math.copysign(1, target_index - note_index)) if target_index != note_index else 0
                center_pull = int(math.copysign(1, center_index - note_index)) if center_index != note_index and rng.random() < float(pitch_cfg.get("return_to_center_strength", 0.18)) else 0
                note_index += direction * step_size + drift + center_pull
                note_index = max(0, min(len(notes) - 1, note_index))
                pitch = notes[note_index]
                duration_signal = float(row[rhythm_cfg["duration_signal"]])
                beat_duration = _duration(duration_signal, density)
                beat_start = float(row["beat_index"]) + offset
                velocity_signal = float(row[velocity_cfg["signal"]])
                velocity = int(round(float(velocity_cfg["min"]) + velocity_signal * (float(velocity_cfg["max"]) - float(velocity_cfg["min"]))))
                velocity = int(max(1, min(127, round(velocity * float(section.get("velocity_multiplier", 1.0))))))

                events.append({
                    "event_id": event_id,
                    "batch": batch,
                    "track_name": stem["track_name"],
                    "beat_start": beat_start,
                    "beat_duration": beat_duration,
                    "bar_index": int(row["bar_index"]),
                    "section": section["name"],
                    "source_row_start": int(row["source_row_start"]),
                    "source_row_end": int(row["source_row_end"]),
                    "pitch_midi": int(pitch),
                    "pitch_name": midi_to_note(int(pitch)),
                    "velocity": velocity,
                    "channel": int(stem["channel"]),
                    "program": int(stem["program"]),
                    "scale": f"{config['scale']['root']} {config['scale']['mode']}",
                    "register_signal": register_value,
                    "motion_signal": motion_value,
                    "direction_signal": direction_value,
                    "direction_local_average": local_average,
                    "direction": direction,
                    "scale_steps": step_size,
                    "tension_signal": tension_value,
                    "growth_mass": float(row.get("growth_mass", 0.0)),
                    "leaf_energy": float(row.get("leaf_energy", 0.0)),
                    "root_energy": float(row.get("root_energy", 0.0)),
                    "vitality": float(row.get("vitality", 0.0)),
                    "growth_speed": float(row.get("growth_speed", 0.0)),
                })
                event_id += 1

    return pd.DataFrame(events).sort_values(["beat_start", "batch"]).reset_index(drop=True)
