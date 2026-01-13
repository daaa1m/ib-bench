"""
Export leaderboard to JSON for frontend consumption.

Usage:
    uv run eval/export-scripts/export_leaderboard.py
        # Export to eval/export-scripts/leaderboard/leaderboard-<timestamp>.json
    uv run eval/export-scripts/export_leaderboard.py output/
        # Export to output/leaderboard-<timestamp>.json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "results"))

from leaderboard import build_leaderboard, export_json, load_config


def main():
    default_output_dir = Path(__file__).parent / "leaderboard"
    parser = argparse.ArgumentParser(description="Export leaderboard to JSON")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help=f"Output directory (default: {default_output_dir})",
    )
    args = parser.parse_args()

    output_path = Path(args.output_dir) if args.output_dir else default_output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"leaderboard-{timestamp}.json"

    config = load_config()
    entries = build_leaderboard()

    if not entries:
        print("No scored runs found.")
        return

    export_json(entries, config["weights"], output_path, output_file)


if __name__ == "__main__":
    main()
