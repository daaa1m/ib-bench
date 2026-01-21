"""Regenerate summary.json from existing score files."""

import argparse
import json
from pathlib import Path


def _load_score(path: Path) -> dict:
    return json.loads(path.read_text())


def _build_summary(scores_dir: Path) -> dict:
    score_files = sorted(
        f for f in scores_dir.glob("*.json") if f.name != "summary.json"
    )

    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0,
        "total_points": 0,
        "points_earned": 0,
        "results": [],
        "overall_percent": 0.0,
        "rubric_hashes": {},
    }

    results = []
    rubric_hashes = {}

    for score_file in score_files:
        score = _load_score(score_file)
        task_id = score.get("task_id", score_file.stem)
        total_points = score.get("total_points", 0)
        points_earned = score.get("points_earned", 0)
        score_percent = score.get("score_percent", 0)
        passed = bool(score.get("passed", False))
        blocked = bool(score.get("blocked", False))

        summary["total"] += 1
        summary["total_points"] += total_points
        summary["points_earned"] += points_earned

        if blocked:
            summary["blocked"] += 1
        elif passed:
            summary["passed"] += 1
        else:
            summary["failed"] += 1

        result_entry = {
            "task_id": task_id,
            "passed": passed,
            "points_earned": points_earned,
            "total_points": total_points,
            "score_percent": score_percent,
        }
        if blocked:
            result_entry["blocked"] = True
        results.append(result_entry)

        rubric_hash = score.get("rubric_hash")
        if rubric_hash:
            rubric_hashes[task_id] = rubric_hash

    if summary["total_points"]:
        summary["overall_percent"] = (
            summary["points_earned"] / summary["total_points"] * 100
        )

    summary["results"] = sorted(results, key=lambda item: item["task_id"])
    summary["rubric_hashes"] = rubric_hashes

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate summary.json from score files in a run directory."
    )
    parser.add_argument("scores_dir", help="Path to eval/scores/<model>/<run>")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary instead of writing summary.json",
    )
    args = parser.parse_args()

    scores_dir = Path(args.scores_dir).resolve()
    if not scores_dir.exists():
        print(f"Scores directory not found: {scores_dir}")
        return 1

    summary = _build_summary(scores_dir)
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0

    summary_path = scores_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
