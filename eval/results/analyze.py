"""
Analyze a scored run with full diagnostic dump.

Usage:
    uv run python eval/results/analyze.py MODEL                      # Aggregate all runs for model
    uv run python eval/results/analyze.py MODEL/RUN_ID               # Specific run only
    uv run python eval/results/analyze.py MODEL --compare MODEL2     # Compare two models
"""

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from leaderboard import load_config as load_leaderboard_config


@dataclass
class TaskResult:
    """Parsed result for a single task."""

    task_id: str
    points_earned: float
    total_points: float
    score_percent: float
    criteria: list[dict]
    llm_gated: bool = False

    @property
    def credit_tier(self) -> str:
        if self.score_percent >= 90:
            return "full"
        elif self.score_percent >= 50:
            return "half"
        elif self.score_percent > 0:
            return "partial"
        else:
            return "fail"


def load_run(
    run_path: str, base_dir: Path | None = None
) -> tuple[dict, list[TaskResult]]:
    if base_dir is None:
        base_dir = Path(__file__).parent.parent

    parts = run_path.split("/")

    if len(parts) == 2:
        model, run_id = parts
        return _load_single_run(model, run_id, base_dir)
    elif len(parts) == 1:
        model = parts[0]
        return _load_all_runs_for_model(model, base_dir)
    else:
        raise ValueError(f"Expected MODEL or MODEL/RUN_ID format, got: {run_path}")


def _load_single_run(
    model: str, run_id: str, base_dir: Path
) -> tuple[dict, list[TaskResult]]:
    scores_dir = base_dir / "scores" / model / run_id
    responses_dir = base_dir / "responses" / model / run_id

    if not scores_dir.exists():
        raise FileNotFoundError(f"Scores not found: {scores_dir}")

    config = {}
    config_file = responses_dir / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)

    config["model"] = model
    config["run_id"] = run_id

    results = []
    for score_file in sorted(scores_dir.glob("*.json")):
        if score_file.name == "summary.json":
            continue
        with open(score_file) as f:
            data = json.load(f)
            results.append(
                TaskResult(
                    task_id=data["task_id"],
                    points_earned=data.get("points_earned", 0),
                    total_points=data.get("total_points", 100),
                    score_percent=data.get("score_percent", 0),
                    criteria=data.get("criteria", []),
                    llm_gated=data.get("llm_gated", False),
                )
            )

    return config, results


def _load_all_runs_for_model(
    model: str, base_dir: Path
) -> tuple[dict, list[TaskResult]]:
    model_scores_dir = base_dir / "scores" / model

    if not model_scores_dir.exists():
        raise FileNotFoundError(f"No scores found for model: {model}")

    run_dirs = sorted([d for d in model_scores_dir.iterdir() if d.is_dir()])
    if not run_dirs:
        raise FileNotFoundError(f"No runs found for model: {model}")

    scores_by_task: dict[str, dict] = {}
    for run_dir in run_dirs:
        for score_file in run_dir.glob("*.json"):
            if score_file.name == "summary.json":
                continue
            with open(score_file) as f:
                data = json.load(f)
                task_id = data.get("task_id")
                if task_id:
                    scores_by_task[task_id] = data

    config = {
        "model": model,
        "run_id": f"(aggregated from {len(run_dirs)} runs)",
    }

    results = []
    for data in scores_by_task.values():
        results.append(
            TaskResult(
                task_id=data["task_id"],
                points_earned=data.get("points_earned", 0),
                total_points=data.get("total_points", 100),
                score_percent=data.get("score_percent", 0),
                criteria=data.get("criteria", []),
                llm_gated=data.get("llm_gated", False),
            )
        )

    return config, sorted(results, key=lambda r: r.task_id)


DIFFICULTY_MAP = {"e": "easy", "m": "medium", "h": "hard"}


def get_difficulty(task_id: str) -> str:
    """Get difficulty tier from task ID prefix."""
    prefix = task_id.split("-")[0]
    return DIFFICULTY_MAP.get(prefix, "unknown")


def get_provider(model: str) -> str:
    """Infer provider from model name."""
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    if "gpt" in model_lower or "o1" in model_lower:
        return "openai"
    if "gemini" in model_lower:
        return "google"
    return "unknown"


def get_task_category(task_id: str) -> str:
    tasks_dir = Path(__file__).parent.parent / "tasks"
    task_dir = tasks_dir / task_id
    meta_file = task_dir / "meta.yaml"

    if meta_file.exists():
        import yaml

        with open(meta_file) as f:
            meta = yaml.safe_load(f)
            if isinstance(meta, dict):
                category = meta.get("task", {}).get("category", "unknown")
                if isinstance(category, list):
                    return category[0] if category else "unknown"
                return category
    return "unknown"


def print_header(title: str):
    """Print section header."""
    print(f"\n\033[1m▸ {title}\033[0m")


def print_separator():
    """Print major separator."""
    print("\n" + "═" * 70)


def calc_credits(task_results: list[TaskResult]) -> float:
    """Calculate total credits from task results."""
    credits = 0.0
    for r in task_results:
        if r.score_percent >= 90:
            credits += 1.0
        elif r.score_percent >= 50:
            credits += 0.5
    return credits


def analyze_run(config: dict, results: list[TaskResult], total_tasks: int):
    """Print full analysis of a run."""

    # ══════════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════════
    print_separator()
    print(f"RUN ANALYSIS: {config['model']}/{config['run_id']}")
    print_separator()

    # ══════════════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════════════
    print_header("METADATA")
    print(f"  Model:      {config['model']}")
    print(f"  Provider:   {get_provider(config['model'])}")

    started = config.get("started_at", "unknown")
    if started != "unknown":
        try:
            dt = datetime.fromisoformat(started)
            started = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    print(f"  Run Date:   {started}")
    print(f"  Tasks:      {len(results)} attempted / {total_tasks} total")

    # ══════════════════════════════════════════════════════════════════
    # SCORE SUMMARY
    # ══════════════════════════════════════════════════════════════════
    print_header("SCORE SUMMARY")

    # Group by difficulty
    by_difficulty: dict[str, list[TaskResult]] = {"easy": [], "medium": [], "hard": []}
    for r in results:
        diff = get_difficulty(r.task_id)
        if diff in by_difficulty:
            by_difficulty[diff].append(r)

    # Count task totals per difficulty
    task_counts = {"easy": 0, "medium": 0, "hard": 0}
    tasks_dir = Path(__file__).parent.parent / "tasks"
    for task_path in tasks_dir.iterdir():
        if not task_path.is_dir() or task_path.name.startswith("_"):
            continue
        diff = get_difficulty(task_path.name)
        if diff in task_counts:
            task_counts[diff] += 1

    # Calculate scores
    leaderboard_config = load_leaderboard_config()
    weights = leaderboard_config.get(
        "weights", {"easy": 0.20, "medium": 0.35, "hard": 0.45}
    )
    tier_scores = {}
    for diff in ["easy", "medium", "hard"]:
        tasks = by_difficulty[diff]
        if tasks:
            credits = calc_credits(tasks)
            score = (credits / len(tasks)) * 100
            tier_scores[diff] = score
        else:
            tier_scores[diff] = None

    # Overall
    overall = 0
    for diff, weight in weights.items():
        if tier_scores[diff] is not None:
            overall += tier_scores[diff] * weight

    print(f"  Overall:    {overall:.1f} / 100")

    for diff in ["easy", "medium", "hard"]:
        tasks = by_difficulty[diff]
        if tasks:
            credits = calc_credits(tasks)
            print(
                f"  {diff.capitalize():<9} {tier_scores[diff]:.1f}  ({credits:.1f} credits / {len(tasks)} tasks)"
            )
        else:
            print(f"  {diff.capitalize():<9} -     (0 tasks attempted)")

    # Credit counts
    full = sum(1 for r in results if r.credit_tier == "full")
    half = sum(1 for r in results if r.credit_tier == "half")
    partial = sum(1 for r in results if r.credit_tier == "partial")
    fail = sum(1 for r in results if r.credit_tier == "fail")

    print(f"\n  Full: {full} | Half: {half} | Partial: {partial} | Fail: {fail}")

    # ══════════════════════════════════════════════════════════════════
    # HEALTH WARNINGS
    # ══════════════════════════════════════════════════════════════════
    print_header("HEALTH WARNINGS")

    warnings = []

    # Check for 0% scores
    zero_scores = [r for r in results if r.score_percent == 0]
    if zero_scores:
        warnings.append(
            f"⚠ {len(zero_scores)} tasks scored 0% - check rubrics or model output"
        )

    # Check for LLM judge issues
    llm_skipped = []
    for r in results:
        for c in r.criteria:
            if (
                c.get("type") == "llm_judge"
                and "not scored" in c.get("details", "").lower()
            ):
                llm_skipped.append(r.task_id)
                break
    if llm_skipped:
        task_list = ", ".join(llm_skipped[:5])
        if len(llm_skipped) > 5:
            task_list += f" (+{len(llm_skipped) - 5} more)"
        warnings.append(f"⚠ LLM judge skipped on {task_list}")

    # Check for JSON parse failures
    json_failures = [
        r for r in results if any(c.get("id") == "json_parse" for c in r.criteria)
    ]
    if json_failures:
        warnings.append(f"⚠ {len(json_failures)} tasks failed JSON parsing")

    # Check for gated LLM
    gated = [r for r in results if r.llm_gated]
    if gated:
        warnings.append(
            f"⚠ {len(gated)} tasks had LLM evaluation gated (programmatic prereq failed)"
        )

    if warnings:
        for w in warnings:
            print(f"  {w}")
    else:
        print("  ✓ No warnings detected")

    # ══════════════════════════════════════════════════════════════════
    # TASK BREAKDOWNS BY CREDIT TIER
    # ══════════════════════════════════════════════════════════════════

    tiers = [
        ("FULL CREDIT", "full", [r for r in results if r.credit_tier == "full"]),
        ("HALF CREDIT", "half", [r for r in results if r.credit_tier == "half"]),
        ("PARTIAL FAIL", "partial", [r for r in results if r.credit_tier == "partial"]),
        ("FULL FAIL", "fail", [r for r in results if r.credit_tier == "fail"]),
    ]

    for title, tier, tier_results in tiers:
        print_header(f"{title} ({len(tier_results)} tasks)")

        if not tier_results:
            print("  (none)")
            continue

        for r in tier_results:
            print(f"\n  {r.task_id} [{r.points_earned:.0f} pts] " + "─" * 40)

            # Sort criteria: passed first, then failed
            passed = [c for c in r.criteria if c.get("passed")]
            failed = [c for c in r.criteria if not c.get("passed")]

            for c in passed:
                ctype = c.get("type", "")[:4]
                pts = c.get("points", 0)
                details = c.get("details", "")[:50]
                print(f"    \033[32m✓\033[0m {c['id']} ({ctype}, {pts}pts): {details}")

            for c in failed:
                ctype = c.get("type", "")[:4]
                pts = c.get("points", 0)
                details = c.get("details", "")
                print(
                    f"    \033[31m✗\033[0m {c['id']} ({ctype}, {pts}pts): {details[:50]}"
                )

                # Show expected vs actual for programmatic failures
                if c.get("type") == "programmatic":
                    actual = str(c.get("actual", ""))
                    if len(actual) > 60:
                        actual = actual[:60] + "..."
                    print(f'      Actual: "{actual}"')

    # ══════════════════════════════════════════════════════════════════
    # PATTERNS
    # ══════════════════════════════════════════════════════════════════
    print_header("PATTERNS")

    # By criteria type
    print("\n  By criteria type:")
    by_type = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        for c in r.criteria:
            ctype = c.get("type", "unknown")
            by_type[ctype]["total"] += 1
            if c.get("passed"):
                by_type[ctype]["passed"] += 1

    for ctype, counts in sorted(by_type.items()):
        passed = counts["passed"]
        total = counts["total"]
        pct = (passed / total * 100) if total > 0 else 0
        flag = " ← low" if pct < 30 and total >= 3 else ""
        print(f"    {ctype}: {passed}/{total} passed ({pct:.0f}%){flag}")

    # By task category
    print("\n  By task category:")
    by_cat = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        cat = get_task_category(r.task_id)
        by_cat[cat]["total"] += 1
        if r.credit_tier in ["full", "half"]:
            by_cat[cat]["passed"] += 1

    for cat, counts in sorted(by_cat.items()):
        passed = counts["passed"]
        total = counts["total"]
        pct = (passed / total * 100) if total > 0 else 0
        flag = " ← low" if pct < 30 and total >= 2 else ""
        print(f"    {cat}: {passed}/{total} passed ({pct:.0f}%){flag}")

    print()


def compare_runs(
    config1: dict, results1: list[TaskResult], config2: dict, results2: list[TaskResult]
):
    """Print comparison between two runs."""
    print_header("COMPARISON")
    print(f"  Run 1: {config1['model']}/{config1['run_id']}")
    print(f"  Run 2: {config2['model']}/{config2['run_id']}")

    # Build lookup by task_id
    r1_map = {r.task_id: r for r in results1}
    r2_map = {r.task_id: r for r in results2}

    all_tasks = sorted(set(r1_map.keys()) | set(r2_map.keys()))

    print(f"\n  {'Task':<10} {'Run 1':>10} {'Run 2':>10} {'Delta':>10}")
    print("  " + "-" * 45)

    total_delta = 0
    for task_id in all_tasks:
        r1 = r1_map.get(task_id)
        r2 = r2_map.get(task_id)

        s1 = r1.score_percent if r1 else None
        s2 = r2.score_percent if r2 else None

        s1_str = f"{s1:.0f}%" if s1 is not None else "-"
        s2_str = f"{s2:.0f}%" if s2 is not None else "-"

        if s1 is not None and s2 is not None:
            delta = s2 - s1
            total_delta += delta
            delta_str = f"{delta:+.0f}%"
            if delta > 0:
                delta_str = f"\033[32m{delta_str}\033[0m"
            elif delta < 0:
                delta_str = f"\033[31m{delta_str}\033[0m"
        else:
            delta_str = "-"

        print(f"  {task_id:<10} {s1_str:>10} {s2_str:>10} {delta_str:>10}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Analyze IB-bench run results")
    parser.add_argument("run_path", help="Run path as MODEL/RUN_ID")
    parser.add_argument("--compare", help="Compare with another run (MODEL/RUN_ID)")
    args = parser.parse_args()

    # Count total tasks
    tasks_dir = Path(__file__).parent.parent / "tasks"
    total_tasks = sum(
        1 for p in tasks_dir.iterdir() if p.is_dir() and not p.name.startswith("_")
    )

    # Load primary run
    config, results = load_run(args.run_path)

    # Analyze
    analyze_run(config, results, total_tasks)

    # Compare if requested
    if args.compare:
        config2, results2 = load_run(args.compare)
        compare_runs(config, results, config2, results2)


if __name__ == "__main__":
    main()
