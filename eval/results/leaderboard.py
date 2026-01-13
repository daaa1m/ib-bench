"""
Generate leaderboard from scored runs.

Usage:
    uv run python eval/results/leaderboard.py

Configuration (weights, models filter) is read from configs/leaderboard_config.yaml
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class TierScore:
    """Score for a difficulty tier."""

    score: float  # 0-100
    completed: int
    total: int


@dataclass
class LeaderboardEntry:
    """Single model entry on the leaderboard."""

    model: str
    provider: str
    overall_score: float
    easy: TierScore
    medium: TierScore
    hard: TierScore
    run_id: str
    run_date: str
    tasks_attempted: int
    tasks_total: int
    tasks_blocked: int = 0  # Content filter blocked


def load_config(config_path: Path | None = None) -> dict:
    """Load leaderboard configuration."""
    if config_path is None:
        config_path = (
            Path(__file__).parent.parent / "configs" / "leaderboard_config.yaml"
        )

    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)

    # Default config
    return {
        "weights": {"easy": 0.20, "medium": 0.35, "hard": 0.45},
        "benchmark_version": "1.0",
    }


def get_difficulty(task_id: str) -> str:
    """Extract difficulty from task ID (e-001 -> easy)."""
    prefix = task_id.split("-")[0]
    return {"e": "easy", "m": "medium", "h": "hard"}.get(prefix, "unknown")


def count_tasks_by_difficulty(tasks_dir: Path | None = None) -> dict[str, int]:
    """Count total tasks per difficulty tier."""
    if tasks_dir is None:
        tasks_dir = Path(__file__).parent.parent / "tasks"

    counts = {"easy": 0, "medium": 0, "hard": 0}

    for task_path in tasks_dir.iterdir():
        if not task_path.is_dir() or task_path.name.startswith("_"):
            continue

        # Extract task ID from directory name
        task_id = task_path.name.replace("-done", "").replace("-working", "")
        difficulty = get_difficulty(task_id)
        if difficulty in counts:
            counts[difficulty] += 1

    return counts


def find_all_runs(model_dir: Path) -> list[Path]:
    """Find all run directories for a model, sorted oldest to newest."""
    runs = [d for d in model_dir.iterdir() if d.is_dir()]
    return sorted(runs, key=lambda x: x.name)


def load_run_scores(run_dir: Path) -> list[dict]:
    """Load all score files from a run directory."""
    scores = []
    for score_file in run_dir.glob("*.json"):
        if score_file.name == "summary.json":
            continue
        with open(score_file) as f:
            scores.append(json.load(f))
    return scores


class HumanScoresPendingError(Exception):
    """Raised when human-pending scores are found in leaderboard generation."""

    def __init__(self, model: str, task_ids: list[str]):
        self.model = model
        self.task_ids = task_ids
        tasks = ", ".join(task_ids[:5])
        if len(task_ids) > 5:
            tasks += f"... and {len(task_ids) - 5} more"
        super().__init__(
            f"Model '{model}' has {len(task_ids)} task(s) with human-pending scores: {tasks}. "
            "Fill in scores and re-run scoring before generating leaderboard."
        )


def load_all_scores_for_model(model_dir: Path) -> tuple[list[dict], Path | None]:
    """Load scores from all runs, aggregating across runs.

    Later runs override earlier runs for the same task.
    Tasks only in earlier runs are kept.

    Returns:
        Tuple of (aggregated scores, latest run dir for metadata)

    Raises:
        HumanScoresPendingError: If any scores have judge="human-pending"
    """
    runs = find_all_runs(model_dir)
    if not runs:
        return [], None

    scores_by_task: dict[str, dict] = {}
    for run_dir in runs:
        for score in load_run_scores(run_dir):
            task_id = score.get("task_id")
            if task_id:
                scores_by_task[task_id] = score

    pending_tasks = [
        task_id
        for task_id, score in scores_by_task.items()
        if score.get("judge") == "human-pending"
    ]
    if pending_tasks:
        raise HumanScoresPendingError(model_dir.name, pending_tasks)

    return list(scores_by_task.values()), runs[-1]


def get_provider_from_model(model: str) -> str:
    """Infer provider from model name."""
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    elif "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
        return "openai"
    elif "gemini" in model_lower:
        return "google"
    return "unknown"


def task_credit(points_earned: float, total_points: float) -> float:
    """Calculate discrete credit for a task.

    Returns:
        0.0 if score < 50%
        0.5 if score >= 50% and < 90%
        1.0 if score >= 90%
    """
    if total_points == 0:
        return 0.0

    percent = (points_earned / total_points) * 100

    if percent >= 90:
        return 1.0
    elif percent >= 50:
        return 0.5
    else:
        return 0.0


def calculate_entry(
    model: str,
    model_dir: Path,
    task_counts: dict[str, int],
    weights: dict[str, float],
) -> LeaderboardEntry | None:
    """Calculate leaderboard entry from all runs for a model."""
    scores, latest_run = load_all_scores_for_model(model_dir)
    if not scores or not latest_run:
        return None

    run_dir = latest_run  # Use latest run for metadata

    # Aggregate credits by difficulty (0, 0.5, or 1 per task)
    tier_credits = {"easy": 0.0, "medium": 0.0, "hard": 0.0}
    tier_completed = {"easy": 0, "medium": 0, "hard": 0}
    tasks_blocked = 0

    for score in scores:
        task_id = score["task_id"]
        difficulty = get_difficulty(task_id)
        if difficulty not in tier_credits:
            continue

        # Count blocked tasks (content filter)
        if score.get("blocked", False):
            tasks_blocked += 1

        points_earned = score.get("points_earned", 0)
        total_points = score.get("total_points", 100)
        tier_credits[difficulty] += task_credit(points_earned, total_points)
        tier_completed[difficulty] += 1

    # Calculate tier scores (0-100) based on credits earned vs tasks completed
    def tier_score(difficulty: str) -> TierScore:
        completed = tier_completed[difficulty]
        if completed == 0:
            return TierScore(score=0.0, completed=0, total=task_counts[difficulty])
        # Score = (credits earned / tasks completed) * 100
        score = (tier_credits[difficulty] / completed) * 100
        return TierScore(
            score=round(score, 1),
            completed=completed,
            total=task_counts[difficulty],
        )

    easy = tier_score("easy")
    medium = tier_score("medium")
    hard = tier_score("hard")

    # Calculate weighted overall score
    overall_weights = weights
    if hard.completed == 0:
        overall_weights = {"easy": 0.35, "medium": 0.65, "hard": 0.0}

    overall = (
        easy.score * overall_weights["easy"]
        + medium.score * overall_weights["medium"]
        + hard.score * overall_weights["hard"]
    )

    # Extract run date from run_id (format: YYYYMMDD_HHMMSS)
    run_id = run_dir.name
    try:
        run_date = datetime.strptime(run_id.split("_")[0], "%Y%m%d").strftime(
            "%Y-%m-%d"
        )
    except (ValueError, IndexError):
        run_date = "unknown"

    # Total tasks attempted
    tasks_attempted = sum(tier_completed.values())
    tasks_total = sum(task_counts.values())

    return LeaderboardEntry(
        model=model,
        provider=get_provider_from_model(model),
        overall_score=round(overall, 1),
        easy=easy,
        medium=medium,
        hard=hard,
        run_id=run_id,
        run_date=run_date,
        tasks_attempted=tasks_attempted,
        tasks_total=tasks_total,
        tasks_blocked=tasks_blocked,
    )


def build_leaderboard(
    scores_dir: Path | None = None,
    weights: dict[str, float] | None = None,
    models: list[str] | None = None,
) -> list[LeaderboardEntry]:
    """Build leaderboard from all scored runs."""
    if scores_dir is None:
        scores_dir = Path(__file__).parent.parent / "scores"

    if not scores_dir.exists():
        return []

    config = load_config()
    if weights is None:
        weights = config["weights"]
    if models is None:
        models = config.get("models")

    assert weights is not None

    task_counts = count_tasks_by_difficulty()
    entries = []

    for model_dir in scores_dir.iterdir():
        if not model_dir.is_dir():
            continue

        model = model_dir.name
        if models and model not in models:
            continue

        entry = calculate_entry(model, model_dir, task_counts, weights)
        if entry:
            entries.append(entry)

    # Sort by overall score descending
    entries.sort(key=lambda x: x.overall_score, reverse=True)

    return entries


def print_cli_table(entries: list[LeaderboardEntry], weights: dict[str, float]):
    """Print leaderboard as CLI table."""
    print("\nIB-bench Leaderboard")
    print("=" * 90)
    print()

    if not entries:
        print("No scored runs found.")
        return

    # Header
    header = f"{'Rank':<5} {'Model':<35} {'Overall':>7} {'Easy':>6} {'Med':>6} {'Hard':>6} {'Tasks':>8}"
    print(header)
    print("-" * len(header))

    # Entries
    for i, entry in enumerate(entries, 1):
        easy_str = f"{entry.easy.score:.1f}" if entry.easy.completed > 0 else "-"
        med_str = f"{entry.medium.score:.1f}" if entry.medium.completed > 0 else "-"
        hard_str = f"{entry.hard.score:.1f}" if entry.hard.completed > 0 else "-"
        tasks_str = f"{entry.tasks_attempted}/{entry.tasks_total}"
        blocked_str = (
            f" ({entry.tasks_blocked} blocked)" if entry.tasks_blocked > 0 else ""
        )

        print(
            f"{i:<5} {entry.model:<35} {entry.overall_score:>7.1f} "
            f"{easy_str:>6} {med_str:>6} {hard_str:>6} {tasks_str:>8}{blocked_str}"
        )

    print()
    print(
        f"Weights: Easy={weights['easy'] * 100:.0f}% Medium={weights['medium'] * 100:.0f}% Hard={weights['hard'] * 100:.0f}%"
    )
    print()


def export_json(
    entries: list[LeaderboardEntry],
    weights: dict[str, float],
    output_path: Path,
    output_file: Path | None = None,
):
    """Export leaderboard as JSON."""
    config = load_config()
    task_counts = count_tasks_by_difficulty()

    data = {
        "leaderboard_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "benchmark_version": config.get("benchmark_version", "1.0"),
        "weights": weights,
        "task_counts": task_counts,
        "entries": [
            {
                "rank": i,
                "model": e.model,
                "provider": e.provider,
                "overall_score": e.overall_score,
                "scores_by_difficulty": {
                    "easy": {
                        "score": e.easy.score,
                        "completed": e.easy.completed,
                        "total": e.easy.total,
                    },
                    "medium": {
                        "score": e.medium.score,
                        "completed": e.medium.completed,
                        "total": e.medium.total,
                    },
                    "hard": {
                        "score": e.hard.score,
                        "completed": e.hard.completed,
                        "total": e.hard.total,
                    },
                },
                "run_id": e.run_id,
                "run_date": e.run_date,
                "tasks_attempted": e.tasks_attempted,
                "tasks_total": e.tasks_total,
                "tasks_blocked": e.tasks_blocked,
            }
            for i, e in enumerate(entries, 1)
        ],
    }

    resolved_output_file = output_file or (output_path / "leaderboard.json")
    with open(resolved_output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Exported to: {resolved_output_file}")


def main():
    config = load_config()
    entries = build_leaderboard()
    print_cli_table(entries, config["weights"])


if __name__ == "__main__":
    main()
