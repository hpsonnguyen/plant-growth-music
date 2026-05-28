from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import output_path


SHOWCASE_FIGURES = {
    "growth_to_intensity.png",
    "leaf_to_register.png",
}

BATCH_COLORS = {"R1": "#355c7d", "R2": "#2a9d8f", "R3": "#e76f51"}


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
        "harmony_to_accompaniment.png",
        "growth_mass.svg", "leaf_energy.svg", "root_energy.svg", "vitality.svg", "growth_speed.svg",
        "piano_roll.csv", "README.txt",
    ]
    for name in stale:
        path = figures / name
        if path.exists() and name not in SHOWCASE_FIGURES:
            path.unlink()


def _plot_growth_to_intensity(plt, figures, features: pd.DataFrame, events: pd.DataFrame) -> None:
    melody = events[events["event_type"] == "melody"]
    batches = sorted(features["Random"].unique())
    fig, axes = plt.subplots(len(batches), 2, figsize=(16, 10), sharex="col")
    fig.suptitle("Growth Activity Becomes Musical Intensity", fontsize=18, fontweight="bold", y=1.01)

    for row_index, batch in enumerate(batches):
        color = BATCH_COLORS.get(batch, "#355c7d")
        batch_features = _batch_bar_features(features, batch, ["growth_speed", "vitality"])
        batch_music = _batch_bar_music(melody, batch)
        ax_data = axes[row_index, 0]
        ax_music = axes[row_index, 1]

        ax_data.plot(batch_features["bar_index"], batch_features["growth_speed"], color=color, linewidth=2.2, label="growth speed")
        ax_data.plot(batch_features["bar_index"], batch_features["vitality"], color="#9b5f2e", linewidth=1.8, alpha=0.88, label="vitality")
        ax_data.fill_between(batch_features["bar_index"], 0, batch_features["growth_speed"], color=color, alpha=0.18)
        ax_data.set_ylabel(f"{batch}\nData")
        ax_data.set_ylim(0, 1.05)
        ax_data.grid(True, linewidth=0.8)
        if row_index == 0:
            ax_data.set_title("Data: activity and force by batch")
            ax_data.legend(frameon=False, loc="upper left")

        ax_music.bar(batch_music["bar_index"], batch_music["notes"], color=color, alpha=0.55, label="melody notes/bar")
        ax_velocity = ax_music.twinx()
        ax_velocity.plot(batch_music["bar_index"], batch_music["velocity"], color="#c86444", linewidth=2.0, label="mean velocity")
        ax_music.set_ylabel("Notes")
        ax_velocity.set_ylabel("Velocity")
        ax_music.grid(True, axis="y", linewidth=0.8)
        if row_index == 0:
            ax_music.set_title("Music: melody density and dynamic response")
            lines, labels = ax_music.get_legend_handles_labels()
            lines2, labels2 = ax_velocity.get_legend_handles_labels()
            ax_music.legend(lines + lines2, labels + labels2, frameon=False, loc="upper left")
    axes[-1, 0].set_xlabel("Bar")
    axes[-1, 1].set_xlabel("Bar")
    _shade_sections(config=None, axes=axes)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(figures / "growth_to_intensity.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_leaf_to_register(plt, figures, features: pd.DataFrame, events: pd.DataFrame) -> None:
    melody = events[events["event_type"] == "melody"].copy()
    batches = sorted(features["Random"].unique())
    fig, axes = plt.subplots(len(batches), 2, figsize=(16, 10), sharex="col")
    fig.suptitle("Leaf Energy Opens Register", fontsize=18, fontweight="bold", y=1.01)

    for row_index, batch in enumerate(batches):
        color = BATCH_COLORS.get(batch, "#355c7d")
        batch_features = _batch_bar_features(features, batch, ["leaf_energy"])
        batch_melody = melody[melody["batch"] == batch]
        pitch_summary = _batch_register_summary(batch_melody, int(events["bar_index"].max()))
        ax_data = axes[row_index, 0]
        ax_music = axes[row_index, 1]

        ax_data.plot(batch_features["bar_index"], batch_features["leaf_energy"], color=color, linewidth=2.4)
        ax_data.fill_between(batch_features["bar_index"], 0, batch_features["leaf_energy"], color=color, alpha=0.2)
        ax_data.set_ylabel(f"{batch}\nLeaf energy")
        ax_data.set_ylim(0, 1.05)
        ax_data.grid(True, linewidth=0.8)
        if row_index == 0:
            ax_data.set_title("Data: leaf area, leaves, chlorophyll")

        ax_music.scatter(batch_melody["beat_start"] / 4 + 1, batch_melody["pitch_midi"], s=np.maximum(12, batch_melody["velocity"] / 3.8), color=color, alpha=0.48)
        ax_music.plot(pitch_summary["bar_index"], pitch_summary["rolling_median_pitch"], color="#1d3557", linewidth=2.3, label="rolling median register")
        ax_music.set_ylabel("Pitch")
        ax_music.grid(True, linewidth=0.8)
        if row_index == 0:
            ax_music.set_title("Music: same batch melody register")
            ax_music.legend(frameon=False, loc="upper left")
    axes[-1, 0].set_xlabel("Bar")
    axes[-1, 1].set_xlabel("Bar")
    _shade_sections(config=None, axes=axes)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(figures / "leaf_to_register.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _batch_bar_features(features: pd.DataFrame, batch: str, signals: list[str]) -> pd.DataFrame:
    return features[features["Random"] == batch].groupby("bar_index", as_index=False).agg({signal: "mean" for signal in signals})


def _batch_bar_music(events: pd.DataFrame, batch: str) -> pd.DataFrame:
    bars = pd.DataFrame({"bar_index": range(1, int(events["bar_index"].max()) + 1)})
    batch_events = events[events["batch"] == batch]
    summary = batch_events.groupby("bar_index", as_index=False).agg(notes=("event_id", "count"), velocity=("velocity", "mean"))
    return bars.merge(summary, on="bar_index", how="left").fillna({"notes": 0, "velocity": 0})


def _batch_register_summary(events: pd.DataFrame, max_bar: int) -> pd.DataFrame:
    bars = pd.DataFrame({"bar_index": range(1, max_bar + 1)})
    summary = events.groupby("bar_index", as_index=False).agg(median_pitch=("pitch_midi", "median"))
    summary = bars.merge(summary, on="bar_index", how="left")
    summary["median_pitch"] = summary["median_pitch"].interpolate(limit_direction="both")
    summary["rolling_median_pitch"] = summary["median_pitch"].rolling(8, center=True, min_periods=1).median()
    return summary


def _shade_sections(config, axes) -> None:
    sections = [
        (1, 16, "Germination"),
        (17, 40, "Growth"),
        (41, 60, "Bloom"),
        (61, 75, "Settling"),
    ]
    for ax in np.ravel(axes):
        ylim = ax.get_ylim()
        for start, end, name in sections:
            ax.axvspan(start, end, color="#d8d0c3", alpha=0.12, linewidth=0)
        ax.set_ylim(ylim)


def _write_fallback_tables(figures, features: pd.DataFrame, events: pd.DataFrame, harmony_plan: pd.DataFrame | None) -> None:
    features.groupby(["Random", "bar_index"], as_index=False).agg({"growth_speed": "mean", "vitality": "mean", "leaf_energy": "mean", "root_energy": "mean"}).to_csv(figures / "showcase_data_summary.csv", index=False)
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
