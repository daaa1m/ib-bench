"""
Score responses from a run. Can re-run freely when rubrics change.

Usage:
    uv run python eval/score.py MODEL/RUN_ID                 # Score all
    uv run python eval/score.py MODEL/RUN_ID --tasks e-001   # Score specific
    uv run python eval/score.py MODEL/RUN_ID --rescore       # Rescore already-scored
    uv run python eval/score.py MODEL/RUN_ID --judge-model claude-opus-4-20250514  # Use specific judge
"""

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from helpers import load_tasks, LLMJudge, normalize_criteria, get_rubric_hash


@dataclass
class CriterionResult:
    """Result of evaluating a single criterion."""
    criterion_id: str
    passed: bool
    criterion_type: str  # "programmatic" or "llm_judge"
    match_type: str
    expected: str | list | dict
    actual: str
    details: str
    points: float = 0
    points_earned: float = 0


@dataclass
class TaskScore:
    """Complete score for a task."""
    task_id: str
    passed: bool
    criteria_results: list[CriterionResult]
    total_points: float
    points_earned: float
    score_percent: float
    llm_gated: bool = False  # True if LLM was skipped due to gate failure


def evaluate_substring_one_of(value: str, accepted_values: list[str]) -> tuple[bool, str]:
    """Check if any accepted value is a substring of the provided value."""
    value_upper = str(value).upper()
    for accepted in accepted_values:
        if accepted.upper() in value_upper:
            return True, f"Found '{accepted}' in response"
    return False, f"None of {accepted_values} found in '{value}'"


def evaluate_regex_pattern(
    value: str,
    patterns: list[str],
    required_elements: list[str] = None,
    forbidden_elements: list[str] = None
) -> tuple[bool, str]:
    """Check if value matches any regex pattern and contains required elements."""
    # Check forbidden elements first
    if forbidden_elements:
        for forbidden in forbidden_elements:
            if forbidden and forbidden in value:
                return False, f"Contains forbidden element: '{forbidden}'"

    # Check required elements
    if required_elements:
        missing = [req for req in required_elements if req not in value]
        if missing:
            return False, f"Missing required elements: {missing}"

    # Check regex patterns (if any match, pass)
    if patterns:
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True, f"Matched pattern: {pattern}"
        return False, f"No patterns matched in '{value}'"

    # If no patterns but required elements all present, pass
    return True, "All required elements present"


def get_evaluation_type(rubric: dict) -> str:
    """Determine evaluation type from rubric criteria.

    Returns:
        "programmatic" - only programmatic criteria
        "llm" - only llm_judge criteria
        "hybrid" - mix of both
    """
    criteria = normalize_criteria(rubric.get("criteria", {}))

    has_programmatic = any(c.get("type") == "programmatic" for c in criteria)
    has_llm = any(c.get("type") == "llm_judge" for c in criteria)

    if has_programmatic and has_llm:
        return "hybrid"
    elif has_llm:
        return "llm"
    else:
        return "programmatic"


def score_task(task, response_data: dict, judge: LLMJudge = None) -> TaskScore:
    """Score a response using rubric criteria.

    Scoring flow:
    1. Run ALL programmatic checks (regardless of failures)
    2. Check if any gates_llm=true criteria failed
    3. If gates passed, run LLM judge criteria
    4. Calculate final score based on points
    """
    rubric = task.rubric
    criteria = normalize_criteria(rubric.get("criteria", {}))
    total_points = rubric.get("total_points", 100)
    parsed_response = response_data.get("parsed_response", {})

    # Handle JSON parse failure
    if not parsed_response:
        return TaskScore(
            task_id=task.id,
            passed=False,
            criteria_results=[CriterionResult(
                criterion_id="json_parse",
                passed=False,
                criterion_type="programmatic",
                match_type="json",
                expected="valid JSON",
                actual=response_data.get("raw_response", "")[:100],
                details="Failed to parse JSON from response",
                points=total_points,
                points_earned=0,
            )],
            total_points=total_points,
            points_earned=0,
            score_percent=0,
        )

    results = []
    gate_failed = False

    # Separate criteria by type
    programmatic_criteria = [c for c in criteria if c.get("type") == "programmatic"]
    llm_criteria = [c for c in criteria if c.get("type") == "llm_judge"]

    # Step 1: Run ALL programmatic checks
    for criterion in programmatic_criteria:
        criterion_id = criterion["id"]
        match_type = criterion.get("match_type")
        points = criterion.get("points", 0)
        gates_llm = criterion.get("gates_llm", False)
        search_full_response = criterion.get("search_full_response", False)

        # Get value to evaluate: full response JSON or specific field
        if search_full_response:
            actual_value = json.dumps(parsed_response)
        else:
            actual_value = str(parsed_response.get(criterion_id, ""))

        # Evaluate based on match type
        if match_type == "substring_one_of":
            accepted_values = criterion.get("accepted_values", [])
            passed, details = evaluate_substring_one_of(actual_value, accepted_values)
            expected = accepted_values

        elif match_type == "regex_pattern":
            patterns = criterion.get("valid_patterns", [])
            required = criterion.get("required_elements", [])
            forbidden = criterion.get("forbidden_elements", [])
            passed, details = evaluate_regex_pattern(actual_value, patterns, required, forbidden)
            expected = {"patterns": patterns, "required": required, "forbidden": forbidden}

        else:
            passed = False
            details = f"Unknown match_type: {match_type}"
            expected = criterion

        # Check if this failure gates LLM
        if not passed and gates_llm:
            gate_failed = True
            details += " [GATES LLM]"

        results.append(CriterionResult(
            criterion_id=criterion_id,
            passed=passed,
            criterion_type="programmatic",
            match_type=match_type,
            expected=expected,
            actual=actual_value,
            details=details,
            points=points,
            points_earned=points if passed else 0,
        ))

    # Step 2: Run LLM criteria if gates passed
    llm_gated = False
    if llm_criteria:
        if gate_failed:
            llm_gated = True
            print(f"    LLM evaluation GATED - programmatic gate criteria failed")
            # Add skipped LLM criteria with 0 points
            for criterion in llm_criteria:
                results.append(CriterionResult(
                    criterion_id=criterion["id"],
                    passed=False,
                    criterion_type="llm_judge",
                    match_type="llm_judge",
                    expected=criterion.get("core_concepts", []),
                    actual="[SKIPPED - gated]",
                    details="Skipped due to programmatic gate failure",
                    points=criterion.get("points", 0),
                    points_earned=0,
                ))
        else:
            # Run LLM judge if available
            if not judge:
                # No judge provided - skip LLM criteria with 0 points
                print(f"    LLM evaluation SKIPPED - no judge provided")
                for criterion in llm_criteria:
                    results.append(CriterionResult(
                        criterion_id=criterion["id"],
                        passed=False,
                        criterion_type="llm_judge",
                        match_type="llm_judge",
                        expected=criterion.get("core_concepts", []),
                        actual="[SKIPPED - no judge]",
                        details="Skipped - no LLM judge provided",
                        points=criterion.get("points", 0),
                        points_earned=0,
                    ))
            else:
                llm_results = score_llm_criteria(task, parsed_response, llm_criteria, judge)
                results.extend(llm_results)

    # Calculate final score
    points_earned = sum(r.points_earned for r in results)
    score_percent = (points_earned / total_points * 100) if total_points > 0 else 0

    # Task passes if score >= 60%
    passed = score_percent >= 60

    return TaskScore(
        task_id=task.id,
        passed=passed,
        criteria_results=results,
        total_points=total_points,
        points_earned=points_earned,
        score_percent=score_percent,
        llm_gated=llm_gated,
    )


def score_llm_criteria(task, parsed_response: dict, criteria: list, judge: LLMJudge) -> list[CriterionResult]:
    """Score LLM judge criteria."""
    results = []

    # Find source document for judge
    source_file = None
    for input_file in task.input_files:
        if input_file.suffix in [".pdf", ".xlsx", ".xls"]:
            source_file = input_file
            break

    if not source_file:
        # No source file - return failures
        for criterion in criteria:
            results.append(CriterionResult(
                criterion_id=criterion["id"],
                passed=False,
                criterion_type="llm_judge",
                match_type="llm_judge",
                expected="source document",
                actual="none found",
                details="No source document found for LLM judge",
                points=criterion.get("points", 0),
                points_earned=0,
            ))
        return results

    # Build mini-rubric for just LLM criteria
    llm_rubric = {
        "criteria": {c["id"]: c for c in criteria}
    }

    # Get the response text to evaluate (use logical_explanation or full response)
    response_text = json.dumps(parsed_response, indent=2)

    # Call LLM judge
    judge_result = judge.score(llm_rubric, source_file, response_text)
    scores = judge_result.get("scores", {})

    for criterion in criteria:
        cid = criterion["id"]
        points = criterion.get("points", 0)

        if cid in scores:
            score_val = scores[cid].get("score", 0)
            reasoning = scores[cid].get("reasoning", "")
            # Consider passed if score >= 0.6
            passed = score_val >= 0.6
            points_earned = points * score_val  # Partial credit based on score
            details = f"Score: {score_val:.2f} - {reasoning}"
        else:
            score_val = 0
            passed = False
            points_earned = 0
            details = "Criterion not scored by judge"

        results.append(CriterionResult(
            criterion_id=cid,
            passed=passed,
            criterion_type="llm_judge",
            match_type="llm_judge",
            expected=criterion.get("core_concepts", []),
            actual=f"{score_val:.2f}",
            details=details,
            points=points,
            points_earned=points_earned,
        ))

    return results


def main():
    parser = argparse.ArgumentParser(description="Score IB-bench responses")
    parser.add_argument("run_id", help="Run ID to score")
    parser.add_argument("--tasks", nargs="+", help="Specific task IDs to score")
    parser.add_argument("--rescore", action="store_true", help="Rescore already-scored tasks")
    parser.add_argument("--judge-model", default="claude-sonnet-4-5-20250929",
                        help="Model to use for LLM-as-judge scoring")
    args = parser.parse_args()

    # Find directories
    results_dir = Path(__file__).parent / "results"
    responses_dir = results_dir / "responses" / args.run_id
    scores_dir = results_dir / "scores" / args.run_id

    if not responses_dir.exists():
        print(f"Responses directory not found: {responses_dir}")
        return

    # Create scores directory
    scores_dir.mkdir(parents=True, exist_ok=True)

    # Find response files to score (exclude config.json)
    response_files = [f for f in responses_dir.glob("*.json") if f.name != "config.json"]

    if args.tasks:
        response_files = [f for f in response_files if f.stem in args.tasks]

    if not response_files:
        print("No response files found to score")
        return

    print(f"Scoring {len(response_files)} response(s)...")

    # Load only the tasks we need (based on response files)
    task_ids_to_load = [f.stem for f in response_files]
    all_tasks = load_tasks(task_ids=task_ids_to_load, include_rubric=True)
    task_map = {t.id: t for t in all_tasks}

    # Initialize LLM judge lazily (only when needed)
    judge = None

    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total_points": 0,
        "points_earned": 0,
        "results": [],
    }

    for response_file in response_files:
        task_id = response_file.stem
        score_file = scores_dir / f"{task_id}.json"

        # Skip if already scored (unless --rescore)
        if score_file.exists() and not args.rescore:
            print(f"Skipping {task_id} (already scored, use --rescore to override)")
            summary["skipped"] += 1
            continue

        # Load response
        with open(response_file) as f:
            response_data = json.load(f)

        # Get task rubric
        task = task_map.get(task_id)
        if not task:
            print(f"Warning: No task found for {task_id}")
            continue

        # Determine evaluation type from rubric
        eval_type = get_evaluation_type(task.rubric)

        # Initialize judge if needed for LLM evaluation
        if eval_type in ["llm", "hybrid"] and judge is None:
            print(f"Initializing LLM judge with model: {args.judge_model}")
            judge = LLMJudge(model=args.judge_model)

        # Score
        print(f"\nScoring {task_id} (eval_type: {eval_type})...")
        score = score_task(task, response_data, judge=judge)
        summary["total"] += 1
        summary["total_points"] += score.total_points
        summary["points_earned"] += score.points_earned

        if score.passed:
            summary["passed"] += 1
            status = "PASS"
        else:
            summary["failed"] += 1
            status = "FAIL"

        # Show score details
        gated_note = " [LLM GATED]" if score.llm_gated else ""
        print(f"  Result: {status} ({score.points_earned:.1f}/{score.total_points:.1f} points, {score.score_percent:.1f}%){gated_note}")

        # Print criterion details
        for result in score.criteria_results:
            icon = "+" if result.passed else "-"
            type_tag = f"[{result.criterion_type[:4]}]"
            print(f"    [{icon}] {type_tag} {result.criterion_id}: {result.details} ({result.points_earned:.1f}/{result.points:.1f})")
            if not result.passed and result.actual != "[SKIPPED - gated]":
                actual_preview = result.actual[:80] + "..." if len(result.actual) > 80 else result.actual
                print(f"        Actual: {actual_preview}")

        # Save score
        score_data = {
            "task_id": score.task_id,
            "rubric_hash": get_rubric_hash(task.rubric),
            "scored_at": datetime.now().isoformat(),
            "passed": score.passed,
            "total_points": score.total_points,
            "points_earned": score.points_earned,
            "score_percent": score.score_percent,
            "llm_gated": score.llm_gated,
            "criteria": [
                {
                    "id": r.criterion_id,
                    "passed": r.passed,
                    "type": r.criterion_type,
                    "match_type": r.match_type,
                    "points": r.points,
                    "points_earned": r.points_earned,
                    "actual": r.actual,
                    "details": r.details,
                }
                for r in score.criteria_results
            ],
        }

        with open(score_file, "w") as f:
            json.dump(score_data, f, indent=2)

        summary["results"].append({
            "task_id": task_id,
            "passed": score.passed,
            "points_earned": score.points_earned,
            "total_points": score.total_points,
            "score_percent": score.score_percent,
        })

    # Save summary
    summary_file = scores_dir / "summary.json"
    overall_percent = (summary["points_earned"] / summary["total_points"] * 100) if summary["total_points"] > 0 else 0
    summary["overall_percent"] = overall_percent
    summary["rubric_hashes"] = {
        r["task_id"]: get_rubric_hash(task_map[r["task_id"]].rubric)
        for r in summary["results"]
        if r["task_id"] in task_map
    }

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Summary: {summary['passed']}/{summary['total']} passed ({overall_percent:.1f}%)")
    print(f"Points: {summary['points_earned']:.1f}/{summary['total_points']:.1f}")
    if summary['skipped']:
        print(f"Skipped: {summary['skipped']}")
    print(f"Scores saved to: {scores_dir}")


if __name__ == "__main__":
    main()
