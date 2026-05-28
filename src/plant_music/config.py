from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = project_root() / config_path
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    validate_config(config)
    config["_config_path"] = str(config_path)
    config["_root"] = str(project_root())
    return config


def validate_config(config: dict[str, Any]) -> None:
    required = ["project", "timeline", "scale", "stems", "derived_signals", "mapping"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing config sections: {missing}")
    for key in ["bpm", "bars", "beats_per_bar", "rows_per_beat", "ticks_per_beat"]:
        if key not in config["timeline"]:
            raise ValueError(f"Missing timeline.{key}")
    if not config["stems"]:
        raise ValueError("Config must define at least one stem")


def resolve_path(config: dict[str, Any], path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return Path(config["_root"]) / value


def output_path(config: dict[str, Any], *parts: str) -> Path:
    return resolve_path(config, config["project"]["output_dir"]).joinpath(*parts)


def ensure_output_dirs(config: dict[str, Any]) -> None:
    for name in ["midi", "audio", "events", "processed", "figures"]:
        output_path(config, name).mkdir(parents=True, exist_ok=True)
