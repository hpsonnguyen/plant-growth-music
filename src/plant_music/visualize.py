from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import output_path


SHOWCASE_FIGURES = {
    "growth_to_intensity.png",
    "leaf_to_register.png",
    "harmony_to_accompaniment.png",
}


def _try_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def make_visualizations(config: dict, features: pd.DataFrame, events: pd.DataFrame, harmony_plan: pd.DataFrame | None = None) -> None:
    figures = output_path(config, "figures")
    figures.mkdir(parents=True, exist_ok=True)
    _remove_old_figures(figures)
    plt = _try_matplotlib()
    if plt is None:
        _write_fallback_tables(figures, features, events, harmony_plan)
    else:
        _set_style(plt)
        _plot_growth_to_intensity(plt, figures, features, events)
        _plot_leaf_to_register(plt, figures, features, events)
        if harmony_plan is not None and not harmony_plan.empty:
            _plot_harmony_to_accompaniment(plt, figures, events, harmony_plan)
    _write_metrics(config, features, events)


def _set_style(plt) -> None:
    plt.rcParams.update({
        "figure.facecolor": "#fbfaf6",
        "axes.facecolor": "#fbfaf6",
        "axes.edgecolor": "#d8d0c3",
        "axes.labelcolor": "#2d2a26",
        "axes.titlecolor": "#1f1b16",
        "xtick.color": "#4b4640",
        "ytick.color": "#4b4640",
        "grid.color": "#e7dfd3",
        "font.family": "DejaVu Sans",
    })


def _remove_old_figures(figures) -> None:
    stale = [
        "growth_signals.png", "piano_roll.png", "pitch_vs_growth.png", "velocity_density.png",
        "stem_comparison.png", "harmony_timeline.png", "chord_piano_roll.png", "melody_chord_fit.png",
        "growth_mass.svg", "leaf_energy.svg", "root_energy.svg", "vitality.svg", "growth_speed.svg",
        "piano_roll.csv", "README.txt",
    ]
    for name in stale:
        path = figures / name
        if path.exists() and name not in SHOWCASE_FIGURES:
            path.unlink()


def _plot_growth_to_intensity(plt, figures, features: pd.DataFrame, events: pd.DataFrame) -> None:
    bar_features = features.groupby("bar_index", as_index=False).agg({"growth_speed": "mean", "vitality": "mean"})
    musical = events.groupby("bar_index", as_index=False).agg(notes=("event_id", "count"), velocity=("velocity", "mean"))
    fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharex=False)
    fig.suptitle("Growth Activity Becomes Musical Intensity", fontsize=18, fontweight="bold", y=1.03)

    axes[0].plot(bar_features["bar_index"], bar_features["growth_speed"], color="#547d49", linewidth=2.2, label="growth speed")
    axes[0].plot(bar_features["bar_index"], bar_features["vitality"], color="#9b5f2e", linewidth=2.2, label="vitality")
    axes[0].fill_between(bar_features["bar_index"], 0, bar_features["growth_speed"], color="#547d49", alpha=0.18)
    axes[0].set_title("Data: movement and vitality")
    axes[0].set_xlabel("Bar")
    axes[0].set_ylabel("Normalized signal")
    axes[0].set_ylim(0, 1.05)
    axes[0].legend(frameon=False)
    axes[0].grid(True, linewidth=0.8)

    axes[1].bar(musical["bar_index"], musical["notes"], color="#315f72", alpha=0.72, label="events per bar")
    ax2 = axes[1].twinx()
    ax2.plot(musical["bar_index"], musical["velocity"], color="#c86444", linewidth=2.2, label="mean velocity")
    axes[1].set_title("Music: density and dynamic force")
    axes[1].set_xlabel("Bar")
    axes[1].set_ylabel("Events per bar")
    ax2.set_ylabel("Mean MIDI velocity")
    axes[1].grid(True, axis="y", linewidth=0.8)
    lines, labels = axes[1].get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    axes[1].legend(lines + lines2, labels + labels2, frameon=False, loc="upper left")

    _shade_sections(config=None, axes=axes)
    fig.tight_layout()
    fig.savefig(figures / "growth_to_intensity.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_leaf_to_register(plt, figures, features: pd.DataFrame, events: pd.DataFrame) -> None:
    melody = events[events["event_type"].isin(["melody", "resolution"])].copy()
    bar_leaf = features.groupby("bar_index", as_index=False)["leaf_energy"].mean()
    melody_bar = melody.groupby("bar_index", as_index=False).agg(pitch=("pitch_midi", "mean"))
    fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharex=False)
    fig.suptitle("Leaf Energy Opens The Register", fontsize=18, fontweight="bold", y=1.03)

    axes[0].plot(bar_leaf["bar_index"], bar_leaf["leaf_energy"], color="#4c8c71", linewidth=2.4)
    axes[0].fill_between(bar_leaf["bar_index"], 0, bar_leaf["leaf_energy"], color="#4c8c71", alpha=0.2)
    axes[0].set_title("Data: leaf area, leaves, chlorophyll")
    axes[0].set_xlabel("Bar")
    axes[0].set_ylabel("Leaf energy")
    axes[0].set_ylim(0, 1.05)
    axes[0].grid(True, linewidth=0.8)

    for batch, group in melody[melody["batch"] != "ACCOMP"].groupby("batch"):
        axes[1].scatter(group["beat_start"] / 4 + 1, group["pitch_midi"], s=np.maximum(10, group["velocity"] / 4), alpha=0.58, label=batch)
    axes[1].plot(melody_bar["bar_index"], melody_bar["pitch"], color="#1d3557", linewidth=2.0, label="mean melody register")
    axes[1].set_title("Music: plant melody register")
    axes[1].set_xlabel("Bar")
    axes[1].set_ylabel("MIDI pitch")
    axes[1].legend(frameon=False, loc="upper left")
    axes[1].grid(True, linewidth=0.8)

    _shade_sections(config=None, axes=axes)
    fig.tight_layout()
    fig.savefig(figures / "leaf_to_register.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_harmony_to_accompaniment(plt, figures, events: pd.DataFrame, harmony_plan: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharex=False)
    fig.suptitle("Harmony Becomes A Flowing Broken-Chord Texture", fontsize=18, fontweight="bold", y=1.03)

    unique_chords = list(dict.fromkeys(harmony_plan["chord_symbol"].tolist()))
    chord_to_y = {chord: idx for idx, chord in enumerate(unique_chords)}
    colors = {"i": "#355c7d", "IV": "#2a9d8f", "VII": "#d6a542", "III": "#c9774d", "v": "#6d597a"}
    for _, row in harmony_plan.iterrows():
        y = chord_to_y[row["chord_symbol"]]
        start_bar = float(row["beat_start"]) / 4 + 1
        width = (float(row["beat_end"]) - float(row["beat_start"])) / 4
        axes[0].broken_barh([(start_bar, width)], (y - 0.38, 0.76), facecolors=colors.get(row["chord_function"], "#777777"), alpha=0.9)
    axes[0].set_yticks(range(len(unique_chords)))
    axes[0].set_yticklabels(unique_chords)
    axes[0].set_xlabel("Bar")
    axes[0].set_title("Data-shaped harmonic path")
    axes[0].grid(True, axis="x", linewidth=0.8)

    accomp = events[events["event_type"].isin(["accompaniment", "resolution"])]
    melody = events[events["event_type"] == "melody"]
    axes[1].scatter(accomp["beat_start"] / 4 + 1, accomp["pitch_midi"], s=8, color="#2a9d8f", alpha=0.42, label="broken-chord accompaniment")
    axes[1].scatter(melody["beat_start"] / 4 + 1, melody["pitch_midi"], s=16, color="#e76f51", alpha=0.45, label="plant melody")
    axes[1].set_xlabel("Bar")
    axes[1].set_ylabel("MIDI pitch")
    axes[1].set_title("Music: accompaniment under melody")
    axes[1].legend(frameon=False, loc="upper left")
    axes[1].grid(True, linewidth=0.8)

    _shade_sections(config=None, axes=axes)
    fig.tight_layout()
    fig.savefig(figures / "harmony_to_accompaniment.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _shade_sections(config, axes) -> None:
    sections = [
        (1, 16, "Germination"),
        (17, 40, "Growth"),
        (41, 60, "Bloom"),
        (61, 75, "Settling"),
    ]
    for ax in axes:
        ylim = ax.get_ylim()
        for start, end, name in sections:
            ax.axvspan(start, end, color="#d8d0c3", alpha=0.12, linewidth=0)
        ax.set_ylim(ylim)


def _write_fallback_tables(figures, features: pd.DataFrame, events: pd.DataFrame, harmony_plan: pd.DataFrame | None) -> None:
    features.groupby("bar_index", as_index=False).agg({"growth_speed": "mean", "vitality": "mean", "leaf_energy": "mean"}).to_csv(figures / "showcase_data_summary.csv", index=False)
    events[["event_type", "batch", "beat_start", "beat_duration", "pitch_midi", "velocity", "chord_symbol"]].to_csv(figures / "showcase_music_events.csv", index=False)
    if harmony_plan is not None:
        harmony_plan.to_csv(figures / "showcase_harmony.csv", index=False)
    (figures / "README.txt").write_text("matplotlib is not installed, so showcase PNG figures were not generated. CSV summary files are available here.\n", encoding="utf-8")


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
