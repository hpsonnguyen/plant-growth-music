from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from plant_music.pipeline import run_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/default.yml")
    args = parser.parse_args()
    print(run_all(args.config))


if __name__ == "__main__":
    main()
