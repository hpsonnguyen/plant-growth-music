from __future__ import annotations

import pandas as pd

from .config import ensure_output_dirs, load_config, output_path
from .data import load_and_aggregate
from .mapping import generate_events
from .midi import export_midi
from .render import render_demo
from .signals import derive_signals
from .visualize import make_visualizations


def generate(config_path: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    config = load_config(config_path)
    ensure_output_dirs(config)
    raw = load_and_aggregate(config)
    features = derive_signals(config, raw)
    events = generate_events(config, features)
    export_midi(config, events)
    return config, features, events


def visualize(config_path: str) -> None:
    config = load_config(config_path)
    ensure_output_dirs(config)
    features = pd.read_csv(output_path(config, "processed", "beat_features.csv"))
    events = pd.read_csv(output_path(config, "events", "midi_events.csv"))
    make_visualizations(config, features, events)


def render(config_path: str) -> str:
    config = load_config(config_path)
    ensure_output_dirs(config)
    return render_demo(config)


def run_all(config_path: str) -> str:
    config, features, events = generate(config_path)
    make_visualizations(config, features, events)
    return render_demo(config)
