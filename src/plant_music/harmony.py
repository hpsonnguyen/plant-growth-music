from __future__ import annotations

import ast
from typing import Any

import pandas as pd

from .config import output_path
from .scales import NOTE_TO_PC, MODES, PC_TO_NOTE


ROLE_NAMES = ["root", "third", "fifth", "seventh", "ninth"]


def _section_for_bar(config: dict, bar_index: int) -> dict[str, Any]:
    form = config["mapping"].get("form", {})
    for section in form.get("sections", []):
        if int(section["start_bar"]) <= bar_index <= int(section["end_bar"]):
            return section
    return {"name": "full", "start_bar": 1, "end_bar": config["timeline"]["bars"]}


def _mode_intervals(config: dict) -> list[int]:
    harmony = config.get("harmony", {})
    mode = harmony.get("mode", config["scale"]["mode"])
    return MODES[mode]


def _degree_to_pc(config: dict, degree: int) -> int:
    harmony = config.get("harmony", {})
    root = NOTE_TO_PC[harmony.get("key", config["scale"]["root"]).upper()]
    intervals = _mode_intervals(config)
    index = (int(degree) - 1) % len(intervals)
    return (root + intervals[index]) % 12


def build_chord_palette(config: dict) -> list[dict[str, Any]]:
    palette = []
    for spec in config.get("harmony", {}).get("chord_palette", []):
        degrees = [int(degree) for degree in spec["degrees"]]
        pcs = [_degree_to_pc(config, degree) for degree in degrees]
        roles = {ROLE_NAMES[i] if i < len(ROLE_NAMES) else f"tone_{i + 1}": pc for i, pc in enumerate(pcs)}
        if "sixth" not in roles and len(pcs) >= 4 and spec["symbol"].endswith("6"):
            roles["sixth"] = pcs[3]
        palette.append({
            "symbol": spec["symbol"],
            "function": spec["function"],
            "degrees": degrees,
            "pitch_classes": pcs,
            "core_pitch_classes": pcs[:3],
            "roles": roles,
            "root_pc": pcs[0],
            "root_name": PC_TO_NOTE[pcs[0]],
        })
    if not palette:
        raise ValueError("Harmony is enabled but no chord palette is configured")
    return palette


def generate_harmony_plan(config: dict, features: pd.DataFrame, melody_events: pd.DataFrame) -> pd.DataFrame:
    palette = build_chord_palette(config)
    timeline = config["timeline"]
    beats_per_bar = int(timeline["beats_per_bar"])
    bars = int(timeline["bars"])
    rhythm_cfg = config["harmony"].get("harmonic_rhythm", {})
    bar_features = features.groupby("bar_index", as_index=False).agg({
        "growth_mass": "mean",
        "leaf_energy": "mean",
        "root_energy": "mean",
        "vitality": "mean",
        "growth_speed": "mean",
    })
    feature_lookup = {int(row.bar_index): row for row in bar_features.itertuples(index=False)}
    melody = melody_events.copy()
    melody["pitch_class"] = melody["pitch_midi"] % 12
    previous_function = "i"
    records = []
    segment_id = 1
    bar = 1
    while bar <= bars:
        section = _section_for_bar(config, bar)
        section_name = section["name"]
        rhythm = float(rhythm_cfg.get(section_name, 1.0))
        if rhythm >= 1.0:
            span_bars = max(1, int(round(rhythm)))
            beat_start = (bar - 1) * beats_per_bar
            beat_end = min(bars * beats_per_bar, (bar + span_bars - 1) * beats_per_bar)
            chord = _select_chord(config, palette, previous_function, melody, feature_lookup, bar, beat_start, beat_end, section_name)
            records.append(_record(segment_id, bar, 0, beat_start, beat_end, rhythm, section_name, chord, feature_lookup))
            previous_function = chord["function"]
            segment_id += 1
            bar += span_bars
        else:
            subdivisions = max(1, int(round(1.0 / rhythm)))
            for slot in range(subdivisions):
                beat_start = (bar - 1) * beats_per_bar + slot * beats_per_bar / subdivisions
                beat_end = (bar - 1) * beats_per_bar + (slot + 1) * beats_per_bar / subdivisions
                chord = _select_chord(config, palette, previous_function, melody, feature_lookup, bar, beat_start, beat_end, section_name)
                records.append(_record(segment_id, bar, slot, beat_start, beat_end, rhythm, section_name, chord, feature_lookup))
                previous_function = chord["function"]
                segment_id += 1
            bar += 1
    plan = pd.DataFrame(records)
    plan.to_csv(output_path(config, "events", "harmony_plan.csv"), index=False)
    return plan


def active_chord(plan: pd.DataFrame, beat_start: float) -> dict[str, Any]:
    matches = plan[(plan["beat_start"] <= beat_start) & (beat_start < plan["beat_end"])]
    if matches.empty:
        row = plan.iloc[-1]
    else:
        row = matches.iloc[0]
    record = row.to_dict()
    for key in ["chord_pitch_classes", "core_pitch_classes", "chord_degrees"]:
        value = record.get(key)
        if isinstance(value, str):
            record[key] = ast.literal_eval(value)
    return record


def chord_tone_role(chord: dict[str, Any], pitch_class: int) -> str:
    roles = chord.get("chord_roles") or chord.get("roles") or {}
    if isinstance(roles, str):
        roles = ast.literal_eval(roles)
    for role, pc in roles.items():
        if int(pc) % 12 == int(pitch_class) % 12:
            return role
    if int(pitch_class) % 12 in [int(pc) % 12 for pc in chord.get("core_pitch_classes", [])]:
        return "chord_tone"
    if int(pitch_class) % 12 in [int(pc) % 12 for pc in chord.get("chord_pitch_classes", [])]:
        return "extension"
    return "passing"


def _select_chord(config: dict, palette: list[dict[str, Any]], previous_function: str, melody: pd.DataFrame, feature_lookup: dict, bar: int, beat_start: float, beat_end: float, section_name: str) -> dict[str, Any]:
    segment_notes = melody[(melody["beat_start"] >= beat_start) & (melody["beat_start"] < beat_end)]
    features = feature_lookup.get(bar)
    progression_bias = config["harmony"].get("progression_bias", {})
    preferred_next = progression_bias.get(previous_function, [])
    best_score = -1e9
    best = palette[0]
    for chord in palette:
        core = set(chord["core_pitch_classes"])
        all_pcs = set(chord["pitch_classes"])
        score = 0.0
        for pc in segment_notes["pitch_class"]:
            if pc in core:
                score += 2.0
            elif pc in all_pcs:
                score += 1.0
            else:
                score -= 0.35
        if chord["function"] in preferred_next:
            score += 1.25
        if section_name in {"germination", "settling"} and chord["function"] == "i":
            score += 1.4
        if section_name == "bloom" and chord["symbol"] in {"Dm9", "G9", "Fmaj7"}:
            score += 1.4
        if features is not None:
            score += float(features.vitality) * (0.18 * len(chord["pitch_classes"]))
            if chord["function"] in {"IV", "III", "VII"}:
                score += float(features.leaf_energy) * 1.0
            if chord["function"] in {"i", "v"}:
                score += float(features.root_energy) * 0.9
            if chord["function"] == "i":
                score += float(features.growth_mass) * 0.8
        if bar == 1 and chord["function"] == "i":
            score += 5.0
        if bar >= int(config["timeline"]["bars"]) - 1 and chord["function"] == "i":
            score += 5.0
        if score > best_score:
            best_score = score
            best = chord
    selected = dict(best)
    selected["score"] = round(best_score, 4)
    return selected


def _record(segment_id: int, bar: int, slot: int, beat_start: float, beat_end: float, rhythm: float, section_name: str, chord: dict[str, Any], feature_lookup: dict) -> dict[str, Any]:
    features = feature_lookup.get(bar)
    return {
        "segment_id": segment_id,
        "bar_index": int(bar),
        "chord_slot": int(slot),
        "beat_start": float(beat_start),
        "beat_end": float(beat_end),
        "section": section_name,
        "chord_symbol": chord["symbol"],
        "chord_function": chord["function"],
        "chord_root": chord["root_name"],
        "chord_pitch_classes": chord["pitch_classes"],
        "core_pitch_classes": chord["core_pitch_classes"],
        "chord_degrees": chord["degrees"],
        "chord_roles": chord["roles"],
        "harmonic_rhythm": float(rhythm),
        "growth_mass": float(getattr(features, "growth_mass", 0.0)),
        "vitality": float(getattr(features, "vitality", 0.0)),
        "growth_speed": float(getattr(features, "growth_speed", 0.0)),
        "leaf_energy": float(getattr(features, "leaf_energy", 0.0)),
        "root_energy": float(getattr(features, "root_energy", 0.0)),
        "selected_by": "melody_data_progression_score",
        "score": chord["score"],
    }
