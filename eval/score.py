"""
Score responses from a run. Can re-run freely when rubrics change.

Usage:
    uv run python eval/score.py RUN_ID                 # Score all
    uv run python eval/score.py RUN_ID --tasks e-001   # Score specific
    uv run python eval/score.py RUN_ID --rescore       # Rescore already-scored
"""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from helpers import load_tasks


# Map rubric criterion IDs to LLM response fields
CRITERION_TO_FIELD = {
    "key_1_location": "error_location",
    "key_3_formula": "corrected_formula",
    "key_4_explanation": "logical_explanation",
}


@dataclass
class CriterionResult:
    """Result of evaluating a single criterion."""
    criterion_id: str
    passed: bool
    match_type: str
    expected: str | list | dict
    actual: str
    details: str


@dataclass
class TaskScore:
    """Complete score for a task."""
    task_id: str
    passed: bool
    criteria_results: list[CriterionResult]
    total_criteria: int
    passed_criteria: int


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


def score_response(task, response_data: dict) -> TaskScore:
    """Score a response against the task's rubric."""
    rubric = task.rubric
    criteria = rubric.get("criteria", {})
    parsed_response = response_data.get("parsed_response", {})

    if not parsed_response:
        return TaskScore(
            task_id=task.id,
            passed=False,
            criteria_results=[CriterionResult(
                criterion_id="json_parse",
                passed=False,
                match_type="json",
                expected="valid JSON",
                actual=response_data.get("raw_response", "")[:100],
                details="Failed to parse JSON from response"
            )],
            total_criteria=len(criteria),
            passed_criteria=0,
        )

    results = []

    for criterion_id, criterion_spec in criteria.items():
        match_type = criterion_spec.get("match_type")

        # Skip LLM judge criteria for now
        if match_type == "llm_judge":
            print(f"    Skipping {criterion_id} (llm_judge not implemented)")
            continue

        # Get the response field to check
        response_field = CRITERION_TO_FIELD.get(criterion_id, criterion_id)
        actual_value = str(parsed_response.get(response_field, ""))

        # Evaluate based on match type
        if match_type == "substring_one_of":
            accepted_values = criterion_spec.get("accepted_values", [])
            passed, details = evaluate_substring_one_of(actual_value, accepted_values)
            expected = accepted_values

        elif match_type == "regex_pattern":
            patterns = criterion_spec.get("valid_patterns", [])
            required = criterion_spec.get("required_elements", [])
            forbidden = criterion_spec.get("forbidden_elements", [])
            passed, details = evaluate_regex_pattern(actual_value, patterns, required, forbidden)
            expected = {"patterns": patterns, "required": required, "forbidden": forbidden}

        else:
            passed = False
            details = f"Unknown match_type: {match_type}"
            expected = criterion_spec

        results.append(CriterionResult(
            criterion_id=criterion_id,
            passed=passed,
            match_type=match_type,
            expected=expected,
            actual=actual_value,
            details=details,
        ))

    passed_count = sum(1 for r in results if r.passed)

    return TaskScore(
        task_id=task.id,
        passed=passed_count == len(results) and len(results) > 0,
        criteria_results=results,
        total_criteria=len(results),
        passed_criteria=passed_count,
    )


def main():
    parser = argparse.ArgumentParser(description="Score IB-bench responses")
    parser.add_argument("run_id", help="Run ID to score")
    parser.add_argument("--tasks", nargs="+", help="Specific task IDs to score")
    parser.add_argument("--rescore", action="store_true", help="Rescore already-scored tasks")
    args = parser.parse_args()

    # Find run directory
    results_dir = Path(__file__).parent / "results"
    run_dir = results_dir / args.run_id

    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}")
        return

    responses_dir = run_dir / "responses"
    scores_dir = run_dir / "scores"

    # Find response files to score
    response_files = list(responses_dir.glob("*.json"))

    if args.tasks:
        response_files = [f for f in response_files if f.stem in args.tasks]

    if not response_files:
        print("No response files found to score")
        return

    print(f"Scoring {len(response_files)} response(s)...")

    # Load all tasks for rubrics
    all_tasks = load_tasks()
    task_map = {t.id: t for t in all_tasks}

    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
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

        # Score
        print(f"\nScoring {task_id}...")
        score = score_response(task, response_data)
        summary["total"] += 1

        if score.passed:
            summary["passed"] += 1
            status = "PASS"
        else:
            summary["failed"] += 1
            status = "FAIL"

        print(f"  Result: {status} ({score.passed_criteria}/{score.total_criteria} criteria)")

        # Print criterion details
        for result in score.criteria_results:
            icon = "+" if result.passed else "-"
            print(f"    [{icon}] {result.criterion_id}: {result.details}")
            if not result.passed:
                print(f"        Actual: {result.actual[:80]}...")

        # Save score
        score_data = {
            "task_id": score.task_id,
            "passed": score.passed,
            "passed_criteria": score.passed_criteria,
            "total_criteria": score.total_criteria,
            "criteria": [
                {
                    "id": r.criterion_id,
                    "passed": r.passed,
                    "match_type": r.match_type,
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
        })

    # Save summary
    summary_file = run_dir / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Summary: {summary['passed']}/{summary['total']} passed")
    if summary['skipped']:
        print(f"Skipped: {summary['skipped']}")
    print(f"Results saved to: {run_dir}")


if __name__ == "__main__":
    main()
