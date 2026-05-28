from __future__ import annotations

import ast
import math
import random
from typing import Any

import pandas as pd

from .harmony import active_chord, chord_tone_role
from .scales import legal_notes, midi_to_note, nearest_index, note_to_midi


def section_for_bar(config: dict, bar_index: int) -> dict:
    form = config["mapping"].get("form", {})
    if not form.get("enabled", False):
        return {"name": "full", "density_multiplier": 1.0, "velocity_multiplier": 1.0}
    for section in form.get("sections", []):
        if int(section["start_bar"]) <= bar_index <= int(section["end_bar"]):
            return section
    return {"name": "full", "density_multiplier": 1.0, "velocity_multiplier": 1.0}


def generate_melody_events(config: dict, features: pd.DataFrame) -> pd.DataFrame:
    rng = random.Random(int(config["project"].get("random_seed", 7)))
    pitch_cfg = config["mapping"]["pitch"]
    rhythm_cfg = config["mapping"]["rhythm"]
    velocity_cfg = config["mapping"]["velocity"]
    events = []

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
                velocity = _velocity(config, row, section, scale=float(config.get("arpeggio", {}).get("melody_velocity_scale", 1.0)))

                events.append(_event_record(
                    config=config,
                    batch=batch,
                    row=row,
                    beat_start=beat_start,
                    beat_duration=beat_duration,
                    pitch=int(pitch),
                    velocity=velocity,
                    event_type="melody",
                    section_name=section["name"],
                    register_value=register_value,
                    motion_value=motion_value,
                    direction_value=direction_value,
                    local_average=local_average,
                    direction=direction,
                    step_size=step_size,
                    tension_value=tension_value,
                    chord=None,
                    original_pitch=int(pitch),
                    pitch_adjustment=0,
                    chord_tone="unplanned",
                ))

    return _finalize_events(pd.DataFrame(events))


def apply_harmony_and_arpeggios(config: dict, features: pd.DataFrame, melody_events: pd.DataFrame, harmony_plan: pd.DataFrame) -> pd.DataFrame:
    adjusted = _adjust_melody_to_harmony(config, melody_events, harmony_plan)
    layers = [adjusted]
    if config.get("accompaniment", {}).get("enabled", False):
        layers.append(_generate_broken_chord_accompaniment(config, harmony_plan))
    if config.get("arpeggio", {}).get("enabled", False):
        layers.append(_generate_arpeggios(config, features, harmony_plan))
    if config.get("resolution", {}).get("enabled", False):
        layers.append(_generate_resolution_event(config, harmony_plan))
    return _finalize_events(pd.concat(layers, ignore_index=True))


def generate_events(config: dict, features: pd.DataFrame, harmony_plan: pd.DataFrame | None = None) -> pd.DataFrame:
    melody = generate_melody_events(config, features)
    if harmony_plan is None:
        return melody
    return apply_harmony_and_arpeggios(config, features, melody, harmony_plan)


def _adjust_melody_to_harmony(config: dict, melody_events: pd.DataFrame, harmony_plan: pd.DataFrame) -> pd.DataFrame:
    beats_per_bar = int(config["timeline"]["beats_per_bar"])
    adjusted = []
    notes_by_batch = {batch: legal_notes(config, stem["register_min"], stem["register_max"]) for batch, stem in config["stems"].items()}
    for _, event in melody_events.iterrows():
        chord = active_chord(harmony_plan, float(event["beat_start"]))
        beat_in_bar = float(event["beat_start"]) % beats_per_bar
        strong_beat = abs(beat_in_bar - 0.0) < 0.01 or abs(beat_in_bar - 2.0) < 0.01
        medium_beat = abs(beat_in_bar - 1.0) < 0.01 or abs(beat_in_bar - 3.0) < 0.01
        original_pitch = int(event["pitch_midi"])
        pitch = original_pitch
        target_pcs = chord["core_pitch_classes"] if strong_beat else chord["chord_pitch_classes"] if medium_beat else []
        if target_pcs and pitch % 12 not in [int(pc) % 12 for pc in target_pcs]:
            pitch = _nearest_pitch_for_pcs(notes_by_batch[event["batch"]], pitch, target_pcs)
        role = chord_tone_role(chord, pitch % 12)
        record = event.to_dict()
        record.update({
            "pitch_midi": int(pitch),
            "pitch_name": midi_to_note(int(pitch)),
            "original_pitch_midi": int(original_pitch),
            "pitch_adjustment": int(pitch - original_pitch),
            "chord_symbol": chord["chord_symbol"],
            "chord_function": chord["chord_function"],
            "chord_tone_role": role,
            "is_chord_tone": role != "passing",
        })
        adjusted.append(record)
    return pd.DataFrame(adjusted)


def _generate_arpeggios(config: dict, features: pd.DataFrame, harmony_plan: pd.DataFrame) -> pd.DataFrame:
    events = []
    arpeggio_cfg = config["arpeggio"]
    rows = features.sort_values("beat_index").set_index(["Random", "beat_index"])
    beats_per_bar = int(config["timeline"]["beats_per_bar"])
    for _, chord_row in harmony_plan.iterrows():
        chord = _chord_dict(chord_row)
        section_name = chord["section"]
        pattern = arpeggio_cfg.get("patterns", {}).get(section_name, ["root", "fifth", "third", "fifth"])
        span = float(chord["beat_end"]) - float(chord["beat_start"])
        for batch, stem in config["stems"].items():
            source = _feature_for_beat(rows, batch, int(float(chord["beat_start"])))
            section = section_for_bar(config, int(chord["bar_index"]))
            batch_pattern, event_type = _pattern_for_batch(batch, section_name, pattern)
            if not batch_pattern:
                continue
            base_step = float(arpeggio_cfg.get("step_beats", {}).get(section_name, span / len(batch_pattern)))
            step = _step_for_batch(batch, section_name, base_step)
            idx = 0
            beat_start = float(chord["beat_start"])
            while beat_start < float(chord["beat_end"]) - 1e-6:
                role = batch_pattern[idx % len(batch_pattern)]
                target = _target_fraction(batch, role)
                pitch = _pitch_for_role(config, chord, stem, role, target)
                velocity_scale = float(arpeggio_cfg.get("bass_velocity_scale", 0.78)) if event_type == "bass" else float(arpeggio_cfg.get("velocity_scale", 0.58))
                velocity = _velocity(config, source, section, scale=velocity_scale)
                min_velocity_key = "bass_min_velocity" if event_type == "bass" else "min_velocity"
                velocity = max(velocity, int(arpeggio_cfg.get(min_velocity_key, 1)))
                duration = max(0.08, step * float(arpeggio_cfg.get("duration_ratio", 0.9)))
                duration = min(duration, step * 0.96)
                events.append(_event_record(
                    config=config,
                    batch=batch,
                    row=source,
                    beat_start=beat_start,
                    beat_duration=duration,
                    pitch=int(pitch),
                    velocity=velocity,
                    event_type=event_type,
                    section_name=section_name,
                    register_value=float(source.get("leaf_energy", 0.0)),
                    motion_value=float(source.get("growth_speed", 0.0)),
                    direction_value=float(source.get("growth_mass", 0.0)),
                    local_average=float(source.get("growth_mass", 0.0)),
                    direction=0,
                    step_size=0,
                    tension_value=float(source.get("root_energy", 0.0)),
                    chord=chord,
                    original_pitch=int(pitch),
                    pitch_adjustment=0,
                    chord_tone=role,
                ))
                idx += 1
                beat_start += step
    return pd.DataFrame(events)


def _generate_broken_chord_accompaniment(config: dict, harmony_plan: pd.DataFrame) -> pd.DataFrame:
    accompaniment_cfg = config["accompaniment"]
    events = []
    low = note_to_midi(accompaniment_cfg["register_min"])
    high = note_to_midi(accompaniment_cfg["register_max"])
    previous_chord = None
    repeat_count = 0
    for _, chord_row in harmony_plan.iterrows():
        chord = _chord_dict(chord_row)
        if chord["chord_symbol"] == previous_chord:
            repeat_count += 1
        else:
            repeat_count = 0
            previous_chord = chord["chord_symbol"]
        section_name = chord["section"]
        pattern, is_climax = _select_accompaniment_pattern(config, chord, repeat_count)
        step = _accompaniment_step(config, chord, is_climax)
        duration = step * float(accompaniment_cfg.get("duration_ratio", 0.94))
        beat_start = float(chord["beat_start"])
        idx = 0
        tones = _broken_chord_tones(chord, low, high)
        while beat_start < float(chord["beat_end"]) - 1e-6:
            role = pattern[idx % len(pattern)]
            pitch = tones[role]
            velocity = _accompaniment_velocity(config, chord, is_climax=is_climax)
            events.append(_event_record(
                config=config,
                batch="ACCOMP",
                row=_row_from_chord(chord),
                beat_start=beat_start,
                beat_duration=duration,
                pitch=int(pitch),
                velocity=velocity,
                event_type="accompaniment",
                section_name=section_name,
                register_value=float(chord.get("leaf_energy", 0.0)),
                motion_value=float(chord.get("growth_speed", 0.0)),
                direction_value=float(chord.get("growth_mass", 0.0)),
                local_average=float(chord.get("growth_mass", 0.0)),
                direction=0,
                step_size=0,
                tension_value=float(chord.get("root_energy", 0.0)),
                chord=chord,
                original_pitch=int(pitch),
                pitch_adjustment=0,
                chord_tone=role,
            ))
            idx += 1
            beat_start += step
    return pd.DataFrame(events)


def _select_accompaniment_pattern(config: dict, chord: dict[str, Any], repeat_count: int) -> tuple[list[str], bool]:
    cfg = config["accompaniment"]
    if _is_climax_accompaniment(config, chord):
        return cfg.get("climax_pattern", cfg.get("pattern", ["low", "middle", "high", "middle"])), True
    repeat_after = int(cfg.get("repeat_variation_after", 1))
    variations = cfg.get("repeat_variations", [])
    if variations and repeat_count >= repeat_after:
        return variations[(repeat_count - repeat_after) % len(variations)], False
    return cfg.get("pattern", ["low", "middle", "high", "middle"]), False


def _is_climax_accompaniment(config: dict, chord: dict[str, Any]) -> bool:
    cfg = config["accompaniment"]
    thresholds = cfg.get("climax_thresholds", {})
    vitality_threshold = float(thresholds.get("vitality", 1.1))
    speed_threshold = float(thresholds.get("growth_speed", 1.1))
    return chord.get("section") == "bloom" and (
        float(chord.get("vitality", 0.0)) >= vitality_threshold
        or float(chord.get("growth_speed", 0.0)) >= speed_threshold
    )


def _accompaniment_step(config: dict, chord: dict[str, Any], is_climax: bool) -> float:
    cfg = config["accompaniment"]
    section_name = chord["section"]
    step = float(cfg.get("step_beats", {}).get(section_name, 0.5))
    if is_climax:
        step *= float(cfg.get("climax_step_multiplier", 1.0))
    return max(0.0625, step)


def _generate_resolution_event(config: dict, harmony_plan: pd.DataFrame) -> pd.DataFrame:
    cfg = config["resolution"]
    bars = int(config["timeline"]["bars"])
    beats_per_bar = int(config["timeline"]["beats_per_bar"])
    beat_start = float(bars * beats_per_bar)
    note = cfg.get("note", f"{config['scale']['root']}3")
    pitch = note_to_midi(note)
    last_chord = _chord_dict(harmony_plan.iloc[-1])
    row = pd.Series({
        "bar_index": bars + 1,
        "source_row_start": 0,
        "source_row_end": 0,
        "growth_mass": float(last_chord.get("growth_mass", 0.0)),
        "leaf_energy": float(last_chord.get("leaf_energy", 0.0)),
        "root_energy": float(last_chord.get("root_energy", 0.0)),
        "vitality": float(last_chord.get("vitality", 0.0)),
        "growth_speed": float(last_chord.get("growth_speed", 0.0)),
    })
    return pd.DataFrame([_event_record(
        config=config,
        batch="ACCOMP",
        row=row,
        beat_start=beat_start,
        beat_duration=float(cfg.get("duration_beats", 4.0)),
        pitch=int(pitch),
        velocity=int(cfg.get("velocity", 82)),
        event_type="resolution",
        section_name="resolution",
        register_value=float(row.get("leaf_energy", 0.0)),
        motion_value=float(row.get("growth_speed", 0.0)),
        direction_value=float(row.get("growth_mass", 0.0)),
        local_average=float(row.get("growth_mass", 0.0)),
        direction=0,
        step_size=0,
        tension_value=float(row.get("root_energy", 0.0)),
        chord=last_chord,
        original_pitch=int(pitch),
        pitch_adjustment=0,
        chord_tone="tonic_resolution",
    )])


def _broken_chord_tones(chord: dict[str, Any], low: int, high: int) -> dict[str, int]:
    roles = chord.get("chord_roles", {})
    root = int(roles.get("root", chord["chord_pitch_classes"][0]))
    third = int(roles.get("third", chord["chord_pitch_classes"][min(1, len(chord["chord_pitch_classes"]) - 1)]))
    fifth = int(roles.get("fifth", chord["chord_pitch_classes"][min(2, len(chord["chord_pitch_classes"]) - 1)]))
    high_color = int(roles.get("ninth", roles.get("seventh", chord["chord_pitch_classes"][-1])))
    low_candidates = [root]
    middle_candidates = [third, fifth]
    high_candidates = [fifth, high_color, third]
    return {
        "low": _nearest_pitch_for_pitch_classes(low_candidates, low + 0.04 * (high - low), low, high),
        "inner": _nearest_pitch_for_pitch_classes(middle_candidates, low + 0.34 * (high - low), low, high),
        "middle": _nearest_pitch_for_pitch_classes(middle_candidates, low + 0.45 * (high - low), low, high),
        "high": _nearest_pitch_for_pitch_classes(high_candidates, low + 0.62 * (high - low), low, high),
        "upper": _nearest_pitch_for_pitch_classes(high_candidates, low + 0.78 * (high - low), low, high),
    }


def _nearest_pitch_for_pitch_classes(pitch_classes: list[int], target: float, low: int, high: int) -> int:
    candidates = [pitch for pitch in range(low, high + 1) if pitch % 12 in {pc % 12 for pc in pitch_classes}]
    if not candidates:
        return int(round(target))
    return min(candidates, key=lambda pitch: abs(pitch - target))


def _accompaniment_velocity(config: dict, chord: dict[str, Any], is_climax: bool = False) -> int:
    cfg = config["accompaniment"]
    vitality = float(chord.get("vitality", 0.0))
    velocity = float(cfg.get("velocity_min", 42)) + vitality * (float(cfg.get("velocity_max", 76)) - float(cfg.get("velocity_min", 42)))
    velocity *= float(cfg.get("section_velocity_multiplier", {}).get(chord.get("section", ""), 1.0))
    if is_climax:
        velocity *= float(cfg.get("climax_velocity_multiplier", 1.0))
    return int(max(1, min(127, round(velocity))))


def _row_from_chord(chord: dict[str, Any]) -> pd.Series:
    return pd.Series({
        "bar_index": int(chord.get("bar_index", 1)),
        "source_row_start": 0,
        "source_row_end": 0,
        "growth_mass": float(chord.get("growth_mass", 0.0)),
        "leaf_energy": float(chord.get("leaf_energy", 0.0)),
        "root_energy": float(chord.get("root_energy", 0.0)),
        "vitality": float(chord.get("vitality", 0.0)),
        "growth_speed": float(chord.get("growth_speed", 0.0)),
    })


def _pattern_for_batch(batch: str, section_name: str, pattern: list[str]) -> tuple[list[str], str]:
    if batch == "R1":
        if section_name == "bloom":
            return ["low_root", "fifth", "root", "fifth"], "bass"
        return ["low_root", "fifth"], "bass"
    if batch == "R2":
        return pattern, "arpeggio"
    if section_name == "bloom":
        return ["third", "ninth", "upper_fifth", "ninth"], "arpeggio"
    if section_name == "growth":
        return ["ninth", "fifth", "third", "ninth"], "arpeggio"
    if section_name == "germination":
        return ["ninth"], "arpeggio"
    return ["third"], "arpeggio"


def _step_for_batch(batch: str, section_name: str, base_step: float) -> float:
    if batch == "R1":
        if section_name == "bloom":
            return 1.0
        if section_name == "growth":
            return 1.5
        return 2.0
    if batch == "R3":
        if section_name == "bloom":
            return 0.5
        if section_name == "growth":
            return 1.0
        return 2.0
    return base_step


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


def _velocity(config: dict, row: pd.Series, section: dict, scale: float = 1.0) -> int:
    velocity_cfg = config["mapping"]["velocity"]
    signal = float(row.get(velocity_cfg["signal"], 0.0))
    velocity = float(velocity_cfg["min"]) + signal * (float(velocity_cfg["max"]) - float(velocity_cfg["min"]))
    velocity *= float(section.get("velocity_multiplier", 1.0)) * float(scale)
    return int(max(1, min(127, round(velocity))))


def _event_record(config: dict, batch: str, row: pd.Series, beat_start: float, beat_duration: float, pitch: int, velocity: int, event_type: str, section_name: str, register_value: float, motion_value: float, direction_value: float, local_average: float, direction: int, step_size: int, tension_value: float, chord: dict[str, Any] | None, original_pitch: int, pitch_adjustment: int, chord_tone: str) -> dict[str, Any]:
    if batch == "ACCOMP":
        stem = config["accompaniment"]
        channel = int(stem["channel"])
    else:
        stem = config["stems"][batch]
        channel_offsets = config.get("midi", {}).get("channel_offsets", {})
        channel = int(stem["channel"]) + int(channel_offsets.get(event_type, 0))
    chord_symbol = chord.get("chord_symbol", "") if chord else ""
    chord_function = chord.get("chord_function", "") if chord else ""
    role = chord_tone_role(chord, pitch % 12) if chord else chord_tone
    chord_pcs = chord.get("chord_pitch_classes", []) if chord else []
    return {
        "event_id": 0,
        "event_type": event_type,
        "batch": batch,
        "track_name": stem["track_name"],
        "beat_start": float(beat_start),
        "beat_duration": float(beat_duration),
        "bar_index": int(row.get("bar_index", int(float(beat_start)) // int(config["timeline"]["beats_per_bar"]) + 1)),
        "section": section_name,
        "source_row_start": int(row.get("source_row_start", 0)),
        "source_row_end": int(row.get("source_row_end", 0)),
        "pitch_midi": int(pitch),
        "pitch_name": midi_to_note(int(pitch)),
        "original_pitch_midi": int(original_pitch),
        "pitch_adjustment": int(pitch_adjustment),
        "velocity": int(velocity),
        "channel": int(channel),
        "program": int(stem["program"]),
        "scale": f"{config['scale']['root']} {config['scale']['mode']}",
        "chord_symbol": chord_symbol,
        "chord_function": chord_function,
        "chord_tone_role": role,
        "is_chord_tone": bool(pitch % 12 in [int(pc) % 12 for pc in chord_pcs]) if chord else False,
        "register_signal": float(register_value),
        "motion_signal": float(motion_value),
        "direction_signal": float(direction_value),
        "direction_local_average": float(local_average),
        "direction": int(direction),
        "scale_steps": int(step_size),
        "tension_signal": float(tension_value),
        "growth_mass": float(row.get("growth_mass", 0.0)),
        "leaf_energy": float(row.get("leaf_energy", 0.0)),
        "root_energy": float(row.get("root_energy", 0.0)),
        "vitality": float(row.get("vitality", 0.0)),
        "growth_speed": float(row.get("growth_speed", 0.0)),
    }


def _feature_for_beat(rows: pd.DataFrame, batch: str, beat_index: int) -> pd.Series:
    key = (batch, beat_index)
    if key in rows.index:
        return rows.loc[key]
    batch_rows = rows.loc[batch]
    nearest = min(batch_rows.index, key=lambda value: abs(int(value) - int(beat_index)))
    return batch_rows.loc[nearest]


def _chord_dict(chord_row: pd.Series) -> dict[str, Any]:
    chord = chord_row.to_dict()
    for key in ["chord_pitch_classes", "core_pitch_classes", "chord_degrees", "chord_roles"]:
        value = chord.get(key)
        if isinstance(value, str):
            chord[key] = ast.literal_eval(value)
    return chord


def _target_fraction(batch: str, role: str) -> float:
    if batch == "R1" or role == "low_root":
        return 0.08
    if batch == "R2":
        return 0.45
    if role in {"upper_fifth", "ninth"}:
        return 0.82
    return 0.68


def _pitch_for_role(config: dict, chord: dict[str, Any], stem: dict, role: str, target_fraction: float) -> int:
    role_pcs = chord.get("chord_roles", {})
    if role in {"low_root", "root"}:
        pc = role_pcs.get("root", chord["chord_pitch_classes"][0])
    elif role in {"upper_fifth", "fifth"}:
        pc = role_pcs.get("fifth", chord["chord_pitch_classes"][min(2, len(chord["chord_pitch_classes"]) - 1)])
    elif role == "tenth":
        pc = role_pcs.get("third", chord["chord_pitch_classes"][min(1, len(chord["chord_pitch_classes"]) - 1)])
    elif role == "ninth":
        pc = role_pcs.get("ninth", role_pcs.get("sixth", chord["chord_pitch_classes"][-1]))
    else:
        pc = role_pcs.get(role, chord["chord_pitch_classes"][0])
    low = note_to_midi(stem["register_min"])
    high = note_to_midi(stem["register_max"])
    candidates = [pitch for pitch in range(low, high + 1) if pitch % 12 == int(pc) % 12]
    if not candidates:
        return low
    target = low + target_fraction * (high - low)
    if role in {"low_root"}:
        target = low + 0.05 * (high - low)
    return min(candidates, key=lambda pitch: abs(pitch - target))


def _nearest_pitch_for_pcs(notes: list[int], pitch: int, pcs: list[int]) -> int:
    allowed = [note for note in notes if note % 12 in {int(pc) % 12 for pc in pcs}]
    if not allowed:
        return pitch
    return min(allowed, key=lambda note: abs(note - pitch))


def _finalize_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    order = {"bass": 0, "accompaniment": 1, "arpeggio": 1, "melody": 2, "resolution": 3}
    events = events.copy()
    events["_event_order"] = events["event_type"].map(order).fillna(9)
    events = events.sort_values(["beat_start", "_event_order", "batch", "pitch_midi"]).drop(columns=["_event_order"]).reset_index(drop=True)
    events["event_id"] = range(1, len(events) + 1)
    return events
