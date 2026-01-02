"""
Export task metadata to JSON for frontend consumption.

Usage:
    uv run python eval/export_tasks.py                 # Export to tmp/tasks.json
    uv run python eval/export_tasks.py output/         # Export to output/tasks.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml


def export_tasks_meta(output_dir: str = "tmp") -> Path:
    tasks_dir = Path(__file__).parent / "tasks"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tasks = []

    for task_path in sorted(tasks_dir.iterdir()):
        if not task_path.is_dir() or task_path.name.startswith(("_", ".")):
            continue

        task_id = task_path.name
        meta_file = task_path / "meta.yaml"

        if not meta_file.exists():
            tasks.append(
                {
                    "id": task_id,
                    "title": "TBD",
                    "type": "TBD",
                    "category": [],
                    "input_type": "TBD",
                }
            )
            continue

        with open(meta_file) as f:
            content = f.read().strip()

        if not content or content.startswith("//") or len(content) < 20:
            tasks.append(
                {
                    "id": task_id,
                    "title": "TBD",
                    "type": "TBD",
                    "category": [],
                    "input_type": "TBD",
                }
            )
            continue

        try:
            meta = yaml.safe_load(content)
            task_meta = meta.get("task", {})

            category = task_meta.get("category", [])
            if isinstance(category, str):
                category = [category]

            tasks.append(
                {
                    "id": task_meta.get("id", task_id),
                    "title": task_meta.get("title", "TBD"),
                    "type": task_meta.get("type", "TBD"),
                    "category": category if category else [],
                    "input_type": task_meta.get("input_type", "TBD"),
                }
            )
        except yaml.YAMLError:
            tasks.append(
                {
                    "id": task_id,
                    "title": "TBD",
                    "type": "TBD",
                    "category": [],
                    "input_type": "TBD",
                }
            )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"tasks-{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump({"tasks": tasks, "count": len(tasks)}, f, indent=2)

    print(f"Exported {len(tasks)} tasks to {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Export task metadata to JSON")
    parser.add_argument(
        "output_dir", nargs="?", default="tmp", help="Output directory (default: tmp)"
    )
    args = parser.parse_args()

    export_tasks_meta(args.output_dir)


if __name__ == "__main__":
    main()
