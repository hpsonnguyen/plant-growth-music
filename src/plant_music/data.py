from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import output_path, resolve_path


REQUIRED_COLUMNS = {
    "Random", "ACHP", "PHR", "AWWGV", "ALAP", "ANPL", "ARD", "ADWR",
    "PDMVG", "ARL", "AWWR", "ADWV", "PDMRG", "Class",
}


def load_and_aggregate(config: dict) -> pd.DataFrame:
    input_csv = resolve_path(config, config["project"]["input_csv"])
    df = pd.read_csv(input_csv)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Input CSV is missing columns: {sorted(missing)}")

    timeline = config["timeline"]
    rows_per_beat = int(timeline["rows_per_beat"])
    total_beats = int(timeline["bars"]) * int(timeline["beats_per_bar"])

    df = df.copy()
    df["row_index"] = range(len(df))
    df["beat_index"] = df["row_index"] // rows_per_beat
    df = df[df["beat_index"] < total_beats]
    df["source_row_start"] = df["beat_index"] * rows_per_beat
    df["source_row_end"] = df["source_row_start"] + rows_per_beat - 1

    numeric_cols = [c for c in df.columns if c not in {"Random", "Class"} and pd.api.types.is_numeric_dtype(df[c])]
    grouped = df.groupby(["beat_index", "Random"], as_index=False)[numeric_cols].mean()
    grouped["bar_index"] = grouped["beat_index"] // int(timeline["beats_per_bar"]) + 1
    grouped["beat_in_bar"] = grouped["beat_index"] % int(timeline["beats_per_bar"]) + 1
    grouped["source_row_start"] = grouped["beat_index"] * rows_per_beat
    grouped["source_row_end"] = grouped["source_row_start"] + rows_per_beat - 1

    destination = output_path(config, "processed", "beat_features_raw.csv")
    grouped.to_csv(destination, index=False)
    return grouped
