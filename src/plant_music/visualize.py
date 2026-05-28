from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import output_path


def _try_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _write_svg_line(path, series_by_name: dict[str, list[float]], title: str) -> None:
    width, height = 1200, 420
    colors = ["#2f7d32", "#1976d2", "#c55a11", "#7b1fa2", "#455a64", "#d32f2f"]
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="24" y="32" font-size="22" font-family="sans-serif">{title}</text>']
    for idx, (name, values) in enumerate(series_by_name.items()):
        if not values:
            continue
        n = len(values)
        points = []
        lo, hi = min(values), max(values)
        span = hi - lo if hi != lo else 1.0
        for i, value in enumerate(values):
            x = 60 + i * (width - 100) / max(1, n - 1)
            y = height - 50 - ((value - lo) / span) * (height - 100)
            points.append(f"{x:.1f},{y:.1f}")
        color = colors[idx % len(colors)]
        body.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
        body.append(f'<text x="{70 + idx * 160}" y="{height - 14}" font-size="14" fill="{color}" font-family="sans-serif">{name}</text>')
    body.append("</svg>")
    path.write_text("\n".join(body), encoding="utf-8")


def make_visualizations(config: dict, features: pd.DataFrame, events: pd.DataFrame) -> None:
    figures = output_path(config, "figures")
    plt = _try_matplotlib()

    signals = ["growth_mass", "leaf_energy", "root_energy", "vitality", "growth_speed"]
    if plt:
        readme = figures / "README.txt"
        if readme.exists():
            readme.unlink()
        fig, axes = plt.subplots(len(signals), 1, figsize=(14, 10), sharex=True)
        for ax, signal in zip(axes, signals):
            for batch, group in features.groupby("Random"):
                ax.plot(group["beat_index"], group[signal], label=batch)
            ax.set_ylabel(signal)
        axes[0].legend()
        axes[-1].set_xlabel("Beat")
        fig.tight_layout()
        fig.savefig(figures / "growth_signals.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(14, 6))
        for batch, group in events.groupby("batch"):
            ax.scatter(group["beat_start"], group["pitch_midi"], s=np.maximum(8, group["velocity"] / 3), alpha=0.65, label=batch)
        ax.set_xlabel("Beat")
        ax.set_ylabel("MIDI pitch")
        ax.legend()
        fig.tight_layout()
        fig.savefig(figures / "piano_roll.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(14, 6))
        for batch, group in events.groupby("batch"):
            ax.plot(group["beat_start"], group["pitch_midi"], label=f"{batch} pitch", alpha=0.75)
        ax.set_xlabel("Beat")
        ax.set_ylabel("Pitch")
        ax.legend()
        fig.tight_layout()
        fig.savefig(figures / "pitch_vs_growth.png", dpi=160)
        plt.close(fig)

        density = events.groupby(["batch", "bar_index"]).size().reset_index(name="notes_per_bar")
        fig, ax = plt.subplots(figsize=(14, 6))
        for batch, group in density.groupby("batch"):
            ax.plot(group["bar_index"], group["notes_per_bar"], label=batch)
        ax.set_xlabel("Bar")
        ax.set_ylabel("Notes per bar")
        ax.legend()
        fig.tight_layout()
        fig.savefig(figures / "velocity_density.png", dpi=160)
        plt.close(fig)

        comparison = events.groupby("batch").agg(pitch_min=("pitch_midi", "min"), pitch_max=("pitch_midi", "max"), velocity_mean=("velocity", "mean"), events=("event_id", "count"))
        fig, ax = plt.subplots(figsize=(10, 5))
        comparison[["velocity_mean", "events"]].plot(kind="bar", ax=ax)
        fig.tight_layout()
        fig.savefig(figures / "stem_comparison.png", dpi=160)
        plt.close(fig)
    else:
        for signal in signals:
            series = {batch: group.sort_values("beat_index")[signal].tolist() for batch, group in features.groupby("Random")}
            _write_svg_line(figures / f"{signal}.svg", series, signal)
        piano = events[["batch", "beat_start", "beat_duration", "pitch_midi", "velocity", "section"]]
        piano.to_csv(figures / "piano_roll.csv", index=False)
        (figures / "README.txt").write_text("matplotlib is not installed, so PNG figures were not generated. SVG signal plots and CSV visualization data are available in this directory.\n", encoding="utf-8")

    _write_metrics(config, features, events)


def _safe_corr(a: pd.Series, b: pd.Series) -> float | None:
    if len(a) < 2 or a.nunique() < 2 or b.nunique() < 2:
        return None
    value = a.corr(b)
    if pd.isna(value):
        return None
    return float(value)


def _write_metrics(config: dict, features: pd.DataFrame, events: pd.DataFrame) -> None:
    bpm = int(config["timeline"]["bpm"])
    total_beats = int(config["timeline"]["bars"]) * int(config["timeline"]["beats_per_bar"])
    density = events.groupby(["batch", "bar_index"]).size().reset_index(name="notes_per_bar")
    feature_bar = features.groupby(["Random", "bar_index"], as_index=False).agg({"growth_speed": "mean", "vitality": "mean", "leaf_energy": "mean"})
    event_bar = events.groupby(["batch", "bar_index"], as_index=False).agg({"velocity": "mean", "pitch_midi": "mean"})
    merged = feature_bar.merge(event_bar, left_on=["Random", "bar_index"], right_on=["batch", "bar_index"], how="inner").merge(density, left_on=["Random", "bar_index"], right_on=["batch", "bar_index"], how="left")
    direction_balance = {}
    for batch, group in events.sort_values(["batch", "beat_start"]).groupby("batch"):
        diff = group["pitch_midi"].diff()
        direction_balance[batch] = {
            "up": int((diff > 0).sum()),
            "down": int((diff < 0).sum()),
            "same": int((diff == 0).sum()),
        }

    metrics = {
        "duration_seconds": total_beats * 60 / bpm,
        "events_per_stem": events.groupby("batch").size().to_dict(),
        "pitch_range_per_stem": events.groupby("batch")["pitch_midi"].agg(["min", "max"]).to_dict("index"),
        "pitch_direction_balance": direction_balance,
        "mean_velocity_per_section": events.groupby("section")["velocity"].mean().round(3).to_dict(),
        "notes_per_bar_per_section": events.groupby("section").size().div(events.groupby("section")["bar_index"].nunique()).round(3).to_dict(),
        "correlations": {
            "vitality_vs_velocity": _safe_corr(merged["vitality"], merged["velocity"]),
            "growth_speed_vs_note_density": _safe_corr(merged["growth_speed"], merged["notes_per_bar"].fillna(0)),
            "leaf_energy_vs_pitch_register": _safe_corr(merged["leaf_energy"], merged["pitch_midi"]),
        },
    }
    output_path(config, "metrics.json").write_text(json.dumps(_json_safe(metrics), indent=2), encoding="utf-8")


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value
