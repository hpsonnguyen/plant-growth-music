from __future__ import annotations

import pandas as pd

from .config import ensure_output_dirs, load_config, output_path
from .data import load_and_aggregate
from .harmony import generate_harmony_plan
from .mapping import apply_harmony_and_arpeggios, generate_melody_events
from .midi import export_midi
from .render import render_demo
from .signals import derive_signals
from .visualize import make_visualizations


def generate(config_path: str) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    config = load_config(config_path)
    ensure_output_dirs(config)
    raw = load_and_aggregate(config)
    features = derive_signals(config, raw)
    melody_events = generate_melody_events(config, features)
    harmony_plan = None
    if config.get("harmony", {}).get("enabled", False):
        harmony_plan = generate_harmony_plan(config, features, melody_events)
        events = apply_harmony_and_arpeggios(config, features, melody_events, harmony_plan)
    else:
        events = melody_events
    export_midi(config, events)
    return config, features, events, harmony_plan


def visualize(config_path: str) -> None:
    config = load_config(config_path)
    ensure_output_dirs(config)
    features = pd.read_csv(output_path(config, "processed", "beat_features.csv"))
    events = pd.read_csv(output_path(config, "events", "midi_events.csv"))
    harmony_path = output_path(config, "events", "harmony_plan.csv")
    harmony_plan = pd.read_csv(harmony_path) if harmony_path.exists() else None
    make_visualizations(config, features, events, harmony_plan)


def render(config_path: str) -> str:
    config = load_config(config_path)
    ensure_output_dirs(config)
    return render_demo(config)


def run_all(config_path: str) -> str:
    config, features, events, harmony_plan = generate(config_path)
    make_visualizations(config, features, events, harmony_plan)
    return render_demo(config)
