from __future__ import annotations

import numpy as np
import pandas as pd

from .config import output_path


def robust_minmax(series: pd.Series) -> pd.Series:
    q05 = series.quantile(0.05)
    q95 = series.quantile(0.95)
    if q95 == q05:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return ((series - q05) / (q95 - q05)).clip(0.0, 1.0)


def derive_signals(config: dict, beat_features: pd.DataFrame) -> pd.DataFrame:
    df = beat_features.copy().sort_values(["Random", "beat_index"])
    derived_config = config["derived_signals"]

    base_features = set()
    for spec in derived_config.values():
        if spec["method"] == "weighted_mean":
            base_features.update(spec["features"].keys())
        elif spec["method"] == "diff_abs":
            continue

    for feature in sorted(base_features):
        if feature not in df.columns:
            raise ValueError(f"Configured feature '{feature}' is not in beat features")
        df[f"{feature}_norm"] = robust_minmax(df[feature])

    for signal_name, spec in derived_config.items():
        if spec["method"] != "weighted_mean":
            continue
        total_weight = sum(float(w) for w in spec["features"].values())
        signal = np.zeros(len(df), dtype=float)
        for feature, weight in spec["features"].items():
            signal += df[f"{feature}_norm"].to_numpy() * (float(weight) / total_weight)
        df[signal_name] = pd.Series(signal, index=df.index).clip(0.0, 1.0)

    for signal_name, spec in derived_config.items():
        if spec["method"] != "diff_abs":
            continue
        source = spec["source"]
        if source not in df.columns:
            raise ValueError(f"Diff source '{source}' is not available")
        window = int(spec.get("smoothing_window", 1))
        smoothed = df.groupby("Random")[source].transform(lambda s: s.rolling(window, min_periods=1, center=True).mean())
        diff = smoothed.groupby(df["Random"]).diff().abs().fillna(0.0)
        df[signal_name] = diff.groupby(df["Random"]).transform(robust_minmax).clip(0.0, 1.0)

    velocity_cfg = config["mapping"].get("velocity", {})
    vel_signal = velocity_cfg.get("signal")
    if vel_signal in df.columns and int(velocity_cfg.get("smoothing_window", 1)) > 1:
        window = int(velocity_cfg["smoothing_window"])
        df[vel_signal] = df.groupby("Random")[vel_signal].transform(lambda s: s.rolling(window, min_periods=1, center=True).mean())

    destination = output_path(config, "processed", "beat_features.csv")
    df.to_csv(destination, index=False)
    return df
