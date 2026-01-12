"""
Export task results with scores per model for analysis.

Usage:
    uv run eval/export-scripts/export_task_results.py
        # Export to eval/export-scripts/task-results/task_results-<timestamp>.json
    uv run eval/export-scripts/export_task_results.py output/
        # Export to output/task_results-<timestamp>.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml


def load_all_task_meta(tasks_dir: Path) -> dict[str, dict]:
    """Load metadata for all tasks.

    Returns:
        Dict mapping task_id to metadata dict.
    """
    tasks = {}

    for task_path in sorted(tasks_dir.iterdir()):
        if not task_path.is_dir() or task_path.name.startswith(("_", ".")):
            continue

        task_id = task_path.name
        meta_file = task_path / "meta.yaml"

        if not meta_file.exists():
            continue

        try:
            with open(meta_file) as f:
                content = f.read().strip()

            if not content or len(content) < 20:
                continue

            meta = yaml.safe_load(content)
            if not isinstance(meta, dict):
                continue

            task_meta = meta.get("task", {})

            category = task_meta.get("category", [])
            if isinstance(category, str):
                category = [category]

            tasks[task_id] = {
                "id": task_meta.get("id", task_id),
                "title": task_meta.get("title", "TBD"),
                "type": task_meta.get("type", "TBD"),
                "category": category if category else [],
                "input_type": task_meta.get("input_type", "TBD"),
                "description": task_meta.get("description", None),
            }
        except (yaml.YAMLError, ValueError):
            continue

    return tasks


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = (
            Path(__file__).parent / "configs" / "export_task_results_config.yaml"
        )

    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}

    return {}


def get_provider_from_model(model: str) -> str:
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    elif "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
        return "openai"
    elif "gemini" in model_lower:
        return "google"
    return "unknown"


def determine_error_type(score_data: dict, response_data: dict | None) -> str | None:
    """Derive error_type from score/response data.

    Returns:
        None (no error), "refused_by_provider", "incorrect_answer",
        "failed_by_llm_judge", or "other_error"
    """
    if score_data.get("blocked", False):
        return "refused_by_provider"

    if response_data:
        stop_reason = response_data.get("stop_reason", "")
        if stop_reason == "content_filter":
            return "refused_by_provider"

    score_percent = score_data.get("score_percent", 0)
    if score_percent >= 90:
        return None

    criteria = score_data.get("criteria", [])
    has_programmatic_failure = False
    has_llm_judge_failure = False

    for criterion in criteria:
        criterion_type = criterion.get("type", "")
        passed = criterion.get("passed", True)

        if not passed:
            if criterion_type == "programmatic":
                has_programmatic_failure = True
            elif criterion_type == "llm_judge":
                has_llm_judge_failure = True

    if has_programmatic_failure:
        return "incorrect_answer"
    elif has_llm_judge_failure:
        return "failed_by_llm_judge"

    if response_data:
        stop_reason = response_data.get("stop_reason", "")
        if stop_reason == "max_tokens":
            return "other_error"

        if response_data.get("parsed_response") is None and response_data.get(
            "raw_response", ""
        ):
            return "other_error"

    if score_percent < 90:
        return "other_error"

    return None


def load_run_config(run_dir: Path) -> dict:
    """Load config.json from a run directory."""
    config_file = run_dir / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)
    return {}


def parse_run_date(run_id: str, config: dict) -> str:
    """Extract run date from run_id (YYYYMMDD_HHMMSS) or config.started_at."""
    try:
        return datetime.strptime(run_id.split("_")[0], "%Y%m%d").strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        pass

    started_at = config.get("started_at", "")
    if started_at:
        try:
            return datetime.fromisoformat(started_at).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return "unknown"


def get_model_results(
    model_dir: Path, scores_dir: Path, responses_dir: Path
) -> list[dict]:
    """Get all task results for a model, aggregated across runs (latest per task)."""
    model = model_dir.name
    model_scores_dir = scores_dir / model
    model_responses_dir = responses_dir / model

    if not model_scores_dir.exists():
        return []

    runs = sorted([d for d in model_scores_dir.iterdir() if d.is_dir()])
    if not runs:
        return []

    results_by_task: dict[str, dict] = {}

    for run_dir in runs:
        run_id = run_dir.name
        responses_run_dir = model_responses_dir / run_id
        config = load_run_config(responses_run_dir)
        provider = config.get("provider") or get_provider_from_model(model)
        run_date = parse_run_date(run_id, config)

        for score_file in run_dir.glob("*.json"):
            if score_file.name == "summary.json":
                continue

            task_id = score_file.stem

            try:
                with open(score_file) as f:
                    score_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            response_data = None
            response_file = responses_run_dir / f"{task_id}.json"
            if response_file.exists():
                try:
                    with open(response_file) as f:
                        response_data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass

            execution_time_ms = None
            if response_data and "usage" in response_data:
                execution_time_ms = response_data["usage"].get("latency_ms")
                if execution_time_ms is not None:
                    execution_time_ms = round(execution_time_ms)

            error_type = determine_error_type(score_data, response_data)

            results_by_task[task_id] = {
                "task_id": task_id,
                "model": model,
                "provider": provider,
                "score": round(score_data.get("score_percent", 0)),
                "execution_time_ms": execution_time_ms,
                "run_id": run_id,
                "run_date": run_date,
                "error_type": error_type,
            }

    return list(results_by_task.values())


def export_task_results(output_dir: str | None = None) -> Path:
    """Export task results with scores per model. Returns path to exported file."""
    eval_dir = Path(__file__).resolve().parents[1]
    tasks_dir = eval_dir / "tasks"
    scores_dir = eval_dir / "scores"
    responses_dir = eval_dir / "responses"

    default_output_dir = Path(__file__).parent / "task-results"
    output_path = Path(output_dir) if output_dir else default_output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    config = load_config()
    allowed_models = config.get("models")

    task_meta = load_all_task_meta(tasks_dir)
    all_results: dict[str, list[dict]] = {task_id: [] for task_id in task_meta}
    models_seen = set()

    if scores_dir.exists():
        for model_dir in scores_dir.iterdir():
            if not model_dir.is_dir():
                continue

            if allowed_models and model_dir.name not in allowed_models:
                continue

            model_results = get_model_results(model_dir, scores_dir, responses_dir)

            for result in model_results:
                task_id = result.pop("task_id")
                models_seen.add(result["model"])

                if task_id in all_results:
                    all_results[task_id].append(result)

    tasks = []
    for task_id, meta in sorted(task_meta.items()):
        task_entry = {
            "id": meta["id"],
            "title": meta["title"],
            "type": meta["type"],
            "category": meta["category"],
            "input_type": meta["input_type"],
            "description": meta["description"],
            "results": sorted(all_results.get(task_id, []), key=lambda x: x["model"]),
        }
        tasks.append(task_entry)

    output = {
        "tasks": tasks,
        "generated_at": datetime.now().isoformat(),
        "task_count": len(tasks),
        "model_count": len(models_seen),
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"task_results-{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Exported {len(tasks)} tasks with results from {len(models_seen)} models")
    print(f"Output: {output_file}")

    return output_file


def main():
    default_output_dir = Path(__file__).parent / "task-results"
    parser = argparse.ArgumentParser(
        description="Export task results with scores per model"
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help=f"Output directory (default: {default_output_dir})",
    )
    args = parser.parse_args()

    export_task_results(args.output_dir)


if __name__ == "__main__":
    main()
