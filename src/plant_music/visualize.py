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


def make_visualizations(config: dict, features: pd.DataFrame, events: pd.DataFrame, harmony_plan: pd.DataFrame | None = None) -> None:
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

        if harmony_plan is not None and not harmony_plan.empty:
            _plot_harmony_timeline(plt, figures, harmony_plan)
            _plot_chord_piano_roll(plt, figures, events)
            _plot_melody_chord_fit(plt, figures, events)
    else:
        for signal in signals:
            series = {batch: group.sort_values("beat_index")[signal].tolist() for batch, group in features.groupby("Random")}
            _write_svg_line(figures / f"{signal}.svg", series, signal)
        piano = events[["batch", "beat_start", "beat_duration", "pitch_midi", "velocity", "section"]]
        piano.to_csv(figures / "piano_roll.csv", index=False)
        if harmony_plan is not None and not harmony_plan.empty:
            harmony_plan.to_csv(figures / "harmony_timeline.csv", index=False)
            events[["event_type", "batch", "beat_start", "beat_duration", "pitch_midi", "velocity", "chord_symbol"]].to_csv(figures / "chord_piano_roll.csv", index=False)
        (figures / "README.txt").write_text("matplotlib is not installed, so PNG figures were not generated. SVG signal plots and CSV visualization data are available in this directory.\n", encoding="utf-8")

    _write_metrics(config, features, events)


def _plot_harmony_timeline(plt, figures, harmony_plan: pd.DataFrame) -> None:
    unique_chords = list(dict.fromkeys(harmony_plan["chord_symbol"].tolist()))
    chord_to_y = {chord: idx for idx, chord in enumerate(unique_chords)}
    colors = {"i": "#355c7d", "IV": "#2a9d8f", "VII": "#e9c46a", "III": "#f4a261", "v": "#6d597a"}
    fig, ax = plt.subplots(figsize=(14, 4.8))
    for _, row in harmony_plan.iterrows():
        y = chord_to_y[row["chord_symbol"]]
        width = float(row["beat_end"]) - float(row["beat_start"])
        ax.broken_barh([(float(row["beat_start"]), width)], (y - 0.38, 0.76), facecolors=colors.get(row["chord_function"], "#777777"), alpha=0.9)
        if width >= 2.0:
            ax.text(float(row["beat_start"]) + width / 2, y, row["chord_symbol"], ha="center", va="center", fontsize=8, color="white")
    ax.set_yticks(range(len(unique_chords)))
    ax.set_yticklabels(unique_chords)
    ax.set_xlabel("Beat")
    ax.set_title("Harmony Timeline")
    fig.tight_layout()
    fig.savefig(figures / "harmony_timeline.png", dpi=160)
    plt.close(fig)


def _plot_chord_piano_roll(plt, figures, events: pd.DataFrame) -> None:
    colors = {"accompaniment": "#2a9d8f", "bass": "#264653", "arpeggio": "#2a9d8f", "melody": "#e76f51", "resolution": "#1d3557"}
    fig, ax = plt.subplots(figsize=(14, 7))
    for event_type, group in events.groupby("event_type"):
        ax.scatter(group["beat_start"], group["pitch_midi"], s=np.maximum(6, group["velocity"] / 4), alpha=0.62, label=event_type, color=colors.get(event_type, "#666666"))
    ax.set_xlabel("Beat")
    ax.set_ylabel("MIDI pitch")
    ax.set_title("Layered Piano Roll: Broken-Chord Accompaniment And Melody")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "chord_piano_roll.png", dpi=160)
    plt.close(fig)


def _plot_melody_chord_fit(plt, figures, events: pd.DataFrame) -> None:
    melody = events[events.get("event_type", "") == "melody"].copy()
    if melody.empty or "is_chord_tone" not in melody.columns:
        return
    fit = melody.groupby("bar_index")["is_chord_tone"].mean().reset_index(name="fit_rate")
    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.plot(fit["bar_index"], fit["fit_rate"], color="#355c7d", linewidth=2)
    ax.fill_between(fit["bar_index"], 0, fit["fit_rate"], color="#a8dadc", alpha=0.45)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Bar")
    ax.set_ylabel("Melody chord-tone fit")
    ax.set_title("Melody Fit To Active Harmony")
    fig.tight_layout()
    fig.savefig(figures / "melody_chord_fit.png", dpi=160)
    plt.close(fig)


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
    event_end_beat = float((events["beat_start"] + events["beat_duration"]).max()) if not events.empty else total_beats
    density = events.groupby(["batch", "bar_index"]).size().reset_index(name="notes_per_bar")
    feature_bar = features.groupby(["Random", "bar_index"], as_index=False).agg({"growth_speed": "mean", "vitality": "mean", "leaf_energy": "mean"})
    event_bar = events.groupby(["batch", "bar_index"], as_index=False).agg({"velocity": "mean", "pitch_midi": "mean"})
    merged = feature_bar.merge(event_bar, left_on=["Random", "bar_index"], right_on=["batch", "bar_index"], how="inner").merge(density, left_on=["Random", "bar_index"], right_on=["batch", "bar_index"], how="left")
    melody_events = events[events["event_type"] == "melody"] if "event_type" in events.columns else events
    direction_balance = {}
    for batch, group in melody_events.sort_values(["batch", "beat_start"]).groupby("batch"):
        diff = group["pitch_midi"].diff()
        direction_balance[batch] = {
            "up": int((diff > 0).sum()),
            "down": int((diff < 0).sum()),
            "same": int((diff == 0).sum()),
        }

    chord_fit = None
    if "is_chord_tone" in melody_events.columns and not melody_events.empty:
        chord_fit = float(melody_events["is_chord_tone"].astype(bool).mean())

    metrics = {
        "duration_seconds": event_end_beat * 60 / bpm,
        "timeline_duration_seconds": total_beats * 60 / bpm,
        "events_per_stem": events.groupby("batch").size().to_dict(),
        "events_per_type": events.groupby("event_type").size().to_dict() if "event_type" in events.columns else {},
        "pitch_range_per_stem": events.groupby("batch")["pitch_midi"].agg(["min", "max"]).to_dict("index"),
        "melody_pitch_direction_balance": direction_balance,
        "melody_chord_tone_fit_rate": chord_fit,
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
