"""
Export leaderboard to JSON for frontend consumption.

Usage:
    uv run python eval/export-scripts/export_leaderboard.py              # Export to tmp/
    uv run python eval/export-scripts/export_leaderboard.py output/      # Export to output/
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "results"))

from leaderboard import build_leaderboard, export_json, load_config


def main():
    parser = argparse.ArgumentParser(description="Export leaderboard to JSON")
    parser.add_argument(
        "output_dir", nargs="?", default="tmp", help="Output directory (default: tmp)"
    )
    args = parser.parse_args()

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config = load_config()
    entries = build_leaderboard()

    if not entries:
        print("No scored runs found.")
        return

    export_json(entries, config["weights"], output_path)


if __name__ == "__main__":
    main()
