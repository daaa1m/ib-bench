#!/usr/bin/env python3
"""
Squash multiple evaluation runs into a single run.

Usage:
    uv run python eval/squash_runs.py MODEL/RUN1 MODEL/RUN2 [MODEL/RUN3 ...]
    uv run python eval/squash_runs.py MODEL/RUN1 MODEL/RUN2 --output MODEL/NEW_RUN_ID

Examples:
    uv run python eval/squash_runs.py claude-opus-4-5-20251101/20251230_114140 claude-opus-4-5-20251101/20260101_094708
    uv run python eval/squash_runs.py opus/run1 opus/run2 opus/run3 --output opus/combined
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Squash multiple runs into a single run"
    )
    parser.add_argument(
        "runs",
        nargs="+",
        help="Run paths in format MODEL/RUN_ID (e.g., claude-opus-4-5-20251101/20251230_114140)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output path in format MODEL/RUN_ID. If not specified, creates new timestamped run.",
    )
    parser.add_argument(
        "--responses-dir",
        default="eval/responses",
        help="Base responses directory (default: eval/responses)",
    )
    parser.add_argument(
        "--scores-dir",
        default="eval/scores",
        help="Base scores directory (default: eval/scores)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without copying files",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete source run folders after squashing",
    )
    return parser.parse_args()


def load_config(run_path: Path) -> dict:
    config_path = run_path / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def get_task_files(run_path: Path) -> dict[str, list[Path]]:
    task_files: dict[str, list[Path]] = {}

    for f in run_path.glob("*.json"):
        if f.name == "config.json":
            continue
        task_id = f.stem
        task_files.setdefault(task_id, []).append(f)

    for f in run_path.iterdir():
        if f.suffix == ".json":
            continue
        if "_output_" in f.name:
            task_id = f.name.split("_output_")[0]
            task_files.setdefault(task_id, []).append(f)

    return task_files


def main():
    args = parse_args()
    responses_dir = Path(args.responses_dir)

    run_paths = []
    models = set()

    for run_spec in args.runs:
        parts = run_spec.split("/")
        if len(parts) != 2:
            print(
                f"Error: Invalid run path '{run_spec}'. Expected format: MODEL/RUN_ID"
            )
            return 1

        model, run_id = parts
        models.add(model)
        run_path = responses_dir / model / run_id

        if not run_path.exists():
            print(f"Error: Run path does not exist: {run_path}")
            return 1

        run_paths.append(run_path)

    if len(models) > 1:
        print(f"Warning: Squashing runs from different models: {models}")
        print("Continuing anyway...")

    model = list(models)[0]

    if args.output:
        out_parts = args.output.split("/")
        if len(out_parts) != 2:
            print(
                f"Error: Invalid output path '{args.output}'. Expected format: MODEL/RUN_ID"
            )
            return 1
        out_model, out_run_id = out_parts
        output_path = responses_dir / out_model / out_run_id
    else:
        out_run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_squashed"
        output_path = responses_dir / model / out_run_id

    if output_path.exists():
        print(f"Error: Output path already exists: {output_path}")
        return 1

    task_files: dict[str, list[Path]] = {}
    configs: list[tuple[str, dict]] = []

    print(
        f"Squashing {len(run_paths)} runs into {output_path.relative_to(responses_dir)}"
    )
    print()

    for run_path in run_paths:
        run_id = run_path.name
        config = load_config(run_path)
        if config:
            configs.append((run_id, config))

        run_task_files = get_task_files(run_path)
        print(f"  {run_path.relative_to(responses_dir)}: {len(run_task_files)} task(s)")

        for task_id, file_list in run_task_files.items():
            if task_id in task_files:
                print(f"    {task_id}: overwriting from previous run")
            task_files[task_id] = file_list

    print()
    print(f"Total unique tasks: {len(task_files)}")

    total_files = sum(len(files) for files in task_files.values())
    if args.dry_run:
        print()
        print("Dry run - no files copied")
        print(f"Would create: {output_path}")
        print(f"Would copy {total_files} files for {len(task_files)} tasks")
        print(f"Would save {len(configs)} source configs to _config/")
        if args.delete:
            print(
                f"Would MERGE scores and DELETE {len(run_paths)} source runs (responses + scores)"
            )
        return 0

    output_path.mkdir(parents=True, exist_ok=True)

    for task_id, file_list in sorted(task_files.items()):
        for src_path in file_list:
            dst_path = output_path / src_path.name
            shutil.copy2(src_path, dst_path)

    config_dir = output_path / "_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    for run_id, config in configs:
        with open(config_dir / f"{run_id}.json", "w") as f:
            json.dump(config, f, indent=2)

    first_config = configs[0][1] if configs else {}
    merged_config = {
        "provider": first_config.get("provider", "unknown"),
        "model": first_config.get("model", model),
        "task_ids": sorted(task_files.keys()),
        "config_file": "squashed",
        "started_at": first_config.get("started_at"),
        "completed_at": datetime.now().isoformat(),
        "squashed_from": [str(p.relative_to(responses_dir)) for p in run_paths],
        "results_summary": [
            {"task_id": task_id, "status": "success"}
            for task_id in sorted(task_files.keys())
        ],
    }

    with open(output_path / "config.json", "w") as f:
        json.dump(merged_config, f, indent=2)

    print()
    print(f"Created: {output_path}")
    print(f"  - {len(task_files)} tasks ({total_files} files)")
    print(f"  - _config/ ({len(configs)} source configs)")
    print("  - config.json")

    # --delete also merges scores from old runs and deletes both responses and scores
    if args.delete:
        scores_dir = Path(args.scores_dir)
        out_scores_path = scores_dir / output_path.relative_to(responses_dir)
        out_scores_path.mkdir(parents=True, exist_ok=True)

        print()
        print("Merging scores from source runs...")
        scores_merged = 0
        for run_path in run_paths:
            score_path = scores_dir / run_path.relative_to(responses_dir)
            if score_path.exists():
                for f in score_path.glob("*.json"):
                    if f.name != "summary.json":
                        shutil.copy2(f, out_scores_path / f.name)
                        scores_merged += 1
        print(
            f"  Merged {scores_merged} score files to {out_scores_path.relative_to(scores_dir)}"
        )

        print()
        print("Deleting source runs (responses + scores)...")
        for run_path in run_paths:
            print(f"  Deleting {run_path.relative_to(responses_dir)}")
            shutil.rmtree(run_path)
            score_path = scores_dir / run_path.relative_to(responses_dir)
            if score_path.exists():
                shutil.rmtree(score_path)
        print(f"Deleted {len(run_paths)} source runs")

    return 0


if __name__ == "__main__":
    exit(main())
