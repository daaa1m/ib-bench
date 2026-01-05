"""
Score responses from a run. Can re-run freely when rubrics change.

Usage:
    uv run python eval/score.py MODEL/RUN_ID                 # Score specific run
    uv run python eval/score.py MODEL                        # Score latest run for model
    uv run python eval/score.py MODEL --all-runs             # Score all runs for model
    uv run python eval/score.py MODEL/RUN_ID --tasks e-001   # Score specific tasks
    uv run python eval/score.py MODEL/RUN_ID --rescore       # Rescore already-scored
    uv run python eval/score.py MODEL/RUN_ID --judge-model claude-opus-4-20250514  # Use specific judge
    uv run python eval/score.py MODEL/RUN_ID --human         # Generate templates for human scoring

Human scoring workflow:
    1. Run with --human to generate templates (judge="human-pending", score=null)
    2. Edit the score JSON files to fill in score (0.0-1.0) and reasoning
    3. Re-run without --human to validate and finalize (judge="human")
"""

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from helpers import (
    JudgeParseError,
    Rubric,
    RubricCriterion,
    Task,
    build_error_report,
    check_cell_value,
    get_rubric_hash,
    load_tasks,
)
from llm_judge import LLMJudge

EvalType = Literal["programmatic", "llm", "hybrid"]
ValidationResult = Literal["complete", "pending"]


# schema for each dict in the list of criteria for scoring
class CriterionData(TypedDict, total=False):
    id: str
    passed: bool
    type: str
    match_type: str
    points: float
    points_earned: float
    actual: str
    details: str
    score: float | None
    reasoning: str
    description: str


# schema for scores/{model}/{run-id}/{task.json}
class ScoreData(TypedDict, total=False):
    task_id: str
    rubric_hash: str
    scored_at: str
    passed: bool
    blocked: bool
    total_points: float
    points_earned: float
    score_percent: float
    llm_gated: bool
    judge: str
    criteria: list[CriterionData]


# schema for the scores/{model}/{run-id}/summary.json
class SummaryResult(TypedDict, total=False):
    task_id: str
    passed: bool
    blocked: bool
    points_earned: float
    total_points: float
    score_percent: float


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


def _build_json_parse_failure(
    task: Task, response_data: dict[str, Any], total_points: float
) -> TaskScore:
    """
    Build a TaskScore for JSON parse failures.

    :param task: Task metadata
    :param response_data: Raw response data dict
    :param total_points: Total rubric points
    :returns: TaskScore with a json_parse failure criterion
    """
    raw_preview = response_data.get("raw_response", "")[:100]
    return TaskScore(
        task_id=task.id,
        passed=False,
        criteria_results=[
            CriterionResult(
                criterion_id="json_parse",
                passed=False,
                criterion_type="programmatic",
                match_type="json",
                expected="valid JSON",
                actual=raw_preview,
                details="Failed to parse JSON from response",
                points=total_points,
                points_earned=0,
            )
        ],
        total_points=total_points,
        points_earned=0,
        score_percent=0,
    )


def _evaluate_excel_cell(
    criterion: RubricCriterion,
    output_files: list[str] | None,
    run_dir: Path | None,
) -> tuple[bool, Any, str, dict[str, Any]]:
    """
    Evaluate excel_cell_value criterion.

    :param criterion: Criterion spec with cell, expected, tolerance, sheet
    :param output_files: List of output file names
    :param run_dir: Directory containing output files
    :returns: (passed, actual_value, details, expected_dict)
    """
    cell = criterion.get("cell", "")
    expected_val = criterion.get("expected", 0)
    tolerance = criterion.get("tolerance", 0)
    sheet = criterion.get("sheet")
    expected = {"cell": cell, "expected": expected_val, "tolerance": tolerance}

    if not output_files or not run_dir:
        return False, None, "No output files available for excel check", expected

    xlsx_files = [f for f in output_files if f.endswith(".xlsx")]
    if not xlsx_files:
        return False, None, "No xlsx output file found", expected

    xlsx_path = run_dir / xlsx_files[0]
    if not xlsx_path.exists():
        return False, None, f"Output file not found: {xlsx_path}", expected

    passed, actual, details = check_cell_value(
        xlsx_path, cell, expected_val, sheet=sheet, tolerance=tolerance
    )
    return passed, actual, details, expected


def _evaluate_programmatic_criteria(
    parsed_response: dict[str, Any],
    criteria: dict[str, RubricCriterion],
    output_files: list[str] | None = None,
    run_dir: Path | None = None,
) -> tuple[list[CriterionResult], bool]:
    """
    Evaluate programmatic criteria and track LLM gating.

    :param parsed_response: Parsed JSON response
    :param criteria: Programmatic criteria mapping
    :param output_files: List of output file names (for excel checks)
    :param run_dir: Directory containing output files
    :returns: (criterion results, gate_failed)
    """
    results: list[CriterionResult] = []
    gate_failed = False

    for criterion_id, criterion in criteria.items():
        match_type = criterion.get("match_type") or "unknown"
        points = criterion.get("points", 0)
        gates_llm = criterion.get("gates_llm", False)
        search_full_response = criterion.get("search_full_response", False)

        if search_full_response:
            actual_value = json.dumps(parsed_response)
        else:
            actual_value = str(parsed_response.get(criterion_id, ""))

        if match_type == "excel_cell_value":
            passed, actual_value, details, expected = _evaluate_excel_cell(
                criterion, output_files, run_dir
            )

        elif match_type == "substring_one_of":
            accepted_values = criterion.get("accepted_values", [])
            forbidden = criterion.get("forbidden_elements", [])
            passed, details = evaluate_substring_one_of(
                actual_value, accepted_values, forbidden
            )
            expected = accepted_values

        elif match_type == "regex_pattern":
            patterns = criterion.get("valid_patterns", [])
            required = criterion.get("required_elements", [])
            forbidden = criterion.get("forbidden_elements", [])
            passed, details = evaluate_regex_pattern(
                actual_value, patterns, required, forbidden
            )
            expected = {
                "patterns": patterns,
                "required": required,
                "forbidden": forbidden,
            }

        else:
            passed = False
            details = f"Unknown match_type: {match_type}"
            expected = dict(criterion)

        if not passed and gates_llm:
            gate_failed = True
            details += " [GATES LLM]"

        results.append(
            CriterionResult(
                criterion_id=criterion_id,
                passed=passed,
                criterion_type="programmatic",
                match_type=match_type,
                expected=expected,
                actual=actual_value,
                details=details,
                points=points,
                points_earned=points if passed else 0,
            )
        )

    return results, gate_failed


def evaluate_substring_one_of(
    value: str,
    accepted_values: list[str],
    forbidden_elements: list[str] | None = None,
) -> tuple[bool, str]:
    """Check if any accepted value is a substring of the provided value."""
    # Check forbidden elements first
    if forbidden_elements:
        for forbidden in forbidden_elements:
            if forbidden and forbidden in value:
                return False, f"Contains forbidden element: '{forbidden}'"

    value_upper = str(value).upper()
    for accepted in accepted_values:
        if accepted.upper() in value_upper:
            return True, f"Found '{accepted}' in response"
    return False, f"None of {accepted_values} found in '{value}'"


def evaluate_regex_pattern(
    value: str,
    patterns: list[str],
    required_elements: list[str] | None = None,
    forbidden_elements: list[str] | None = None,
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


def get_evaluation_type(rubric: Rubric) -> EvalType:
    criteria = rubric.get("criteria", {})

    has_programmatic = any(c.get("type") == "programmatic" for c in criteria.values())
    has_llm = any(c.get("type") == "llm_judge" for c in criteria.values())

    if has_programmatic and has_llm:
        return "hybrid"
    elif has_llm:
        return "llm"
    else:
        return "programmatic"


def score_task(
    task: Task,
    response_data: dict[str, Any],
    judge: LLMJudge | None = None,
    human_judge: bool = False,
    run_dir: Path | None = None,
) -> TaskScore:
    """Score a response using rubric criteria.

    Scoring flow:
    1. Run ALL programmatic checks (regardless of failures)
    2. Check if any gates_llm=true criteria failed
    3. If gates passed, run LLM judge criteria (or generate human templates)
    4. Calculate final score based on points
    """
    rubric = task.rubric
    criteria = rubric.get("criteria", {})
    total_points = rubric.get("total_points", 100)
    parsed_response = response_data.get("parsed_response", {})

    # Handle JSON parse failure
    if not parsed_response:
        return _build_json_parse_failure(task, response_data, total_points)

    results: list[CriterionResult] = []

    # Separate criteria by type
    # Human judge replaces LLM judge at runtime (same criteria, different evaluator).
    # Renaming llm_judge->judge would require rubric schema changes + migration.
    # Current naming is clearer: rubric says "llm_judge", score output shows actual
    # evaluator used ("human" vs model name). Keep as-is unless doing broader refactor.
    programmatic_criteria = {
        cid: spec
        for cid, spec in criteria.items()
        if spec.get("type") == "programmatic"
    }
    llm_criteria = {
        cid: spec for cid, spec in criteria.items() if spec.get("type") == "llm_judge"
    }

    # Step 1: Run ALL programmatic checks
    output_files = response_data.get("output_files", [])
    programmatic_results, gate_failed = _evaluate_programmatic_criteria(
        parsed_response, programmatic_criteria, output_files, run_dir
    )
    results.extend(programmatic_results)

    llm_gated = False
    if llm_criteria:
        if gate_failed:
            llm_gated = True
            print("  LLM evaluation GATED - programmatic gate criteria failed")
            for criterion_id, criterion in llm_criteria.items():
                results.append(
                    CriterionResult(
                        criterion_id=criterion_id,
                        passed=False,
                        criterion_type="llm_judge",
                        match_type="llm_judge",
                        expected=criterion.get("core_concepts", []),
                        actual="[SKIPPED - gated]",
                        details="Skipped due to programmatic gate failure",
                        points=criterion.get("points", 0),
                        points_earned=0,
                    )
                )
        elif human_judge:
            print("  Generating human judge templates...")
            for criterion_id, criterion in llm_criteria.items():
                results.append(
                    CriterionResult(
                        criterion_id=criterion_id,
                        passed=False,
                        criterion_type="human_judge",
                        match_type="human_judge",
                        expected=criterion.get("description", ""),
                        actual="[PENDING]",
                        details=f"Human scoring required. Points: {criterion.get('points', 0)}",
                        points=criterion.get("points", 0),
                        points_earned=0,
                    )
                )
        elif not judge:
            print("  LLM evaluation SKIPPED - no judge provided")
            for criterion_id, criterion in llm_criteria.items():
                results.append(
                    CriterionResult(
                        criterion_id=criterion_id,
                        passed=False,
                        criterion_type="llm_judge",
                        match_type="llm_judge",
                        expected=criterion.get("core_concepts", []),
                        actual="[SKIPPED - no judge]",
                        details="Skipped - no LLM judge provided",
                        points=criterion.get("points", 0),
                        points_earned=0,
                    )
                )
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


def score_llm_criteria(
    task: Task,
    parsed_response: dict[str, Any],
    criteria: dict[str, RubricCriterion],
    judge: LLMJudge,
) -> list[CriterionResult]:
    """Score LLM judge criteria."""
    results = []

    source_files = [
        f for f in task.input_files if f.suffix in [".pdf", ".xlsx", ".xls"]
    ]
    # to be explicit, we expect LLM Judge to always need an input to refer to
    # LLMJudge is never asked to judge a no-input-file task
    # might need to change if input task is all web-based
    if not source_files:
        raise ValueError(
            f"Task {task.id} has LLM judge criteria but no source document (PDF/Excel). "
            "Check task configuration."
        )

    llm_rubric = cast(Rubric, {"criteria": criteria})
    response_text = json.dumps(parsed_response, indent=2)

    try:
        judge_result = judge.score(llm_rubric, source_files, response_text, task.prompt)
    except JudgeParseError as e:
        print(f"  ERROR: {e}")
        for cid, criterion in criteria.items():
            results.append(
                CriterionResult(
                    criterion_id=cid,
                    passed=False,
                    criterion_type="llm_judge",
                    match_type="llm_judge",
                    expected=criterion.get("core_concepts", []),
                    actual="[JUDGE_ERROR]",
                    details=f"Judge parse failed: {str(e)[:100]}",
                    points=criterion.get("points", 0),
                    points_earned=0,
                )
            )
        return results

    scores = judge_result.get("scores", {})

    for cid, criterion in criteria.items():
        points = criterion.get("points", 0)

        if cid in scores:
            score_val = scores[cid].get("score", 0)
            reasoning = scores[cid].get("reasoning", "")
            passed = score_val >= 0.6
            points_earned = points * score_val
            details = f"Score: {score_val:.2f} - {reasoning}"
        else:
            score_val = 0
            passed = False
            points_earned = 0
            details = "Criterion not scored by judge"

        results.append(
            CriterionResult(
                criterion_id=cid,
                passed=passed,
                criterion_type="llm_judge",
                match_type="llm_judge",
                expected=criterion.get("core_concepts", []),
                actual=f"{score_val:.2f}",
                details=details,
                points=points,
                points_earned=points_earned,
            )
        )

    return results


def validate_human_scores(score_file: Path, existing_score: dict) -> str:
    """Validate and finalize human-pending scores.

    Returns:
        "complete" - all scores filled, file updated with judge="human"
        "pending" - some scores still null
    """
    criteria = existing_score.get("criteria", [])
    human_criteria = [c for c in criteria if c.get("type") == "human_judge"]

    if not human_criteria:
        return "complete"

    all_filled = all(c.get("score") is not None for c in human_criteria)

    if not all_filled:
        return "pending"

    for c in criteria:
        if c.get("type") == "human_judge":
            score_val = c.get("score", 0)
            c["passed"] = score_val >= 0.6
            c["points_earned"] = c["points"] * score_val
            c["actual"] = f"{score_val:.2f}"
            c["details"] = f"Human score: {score_val:.2f} - {c.get('reasoning', '')}"

    total_points = existing_score.get("total_points", 100)
    points_earned = sum(c.get("points_earned", 0) for c in criteria)
    score_percent = (points_earned / total_points * 100) if total_points > 0 else 0
    passed = score_percent >= 60

    existing_score["judge"] = "human"
    existing_score["points_earned"] = points_earned
    existing_score["score_percent"] = score_percent
    existing_score["passed"] = passed
    existing_score["scored_at"] = datetime.now().isoformat()

    with open(score_file, "w") as f:
        json.dump(existing_score, f, indent=2)

    return "complete"


def find_runs(
    eval_dir: Path, run_path: str, all_runs: bool = False
) -> list[tuple[Path, Path]]:
    """Resolve run path to list of (responses_dir, scores_dir) tuples.

    Args:
        eval_dir: Base eval directory containing responses/ and scores/
        run_path: Either "MODEL/RUN_ID" or just "MODEL"
        all_runs: If True and run_path is just MODEL, return all runs

    Returns:
        List of (responses_dir, scores_dir) tuples
    """
    responses_base = eval_dir / "responses"
    scores_base = eval_dir / "scores"

    # Check if it's MODEL/RUN_ID or just MODEL
    if "/" in run_path:
        # Specific run
        responses_dir = responses_base / run_path
        scores_dir = scores_base / run_path
        if not responses_dir.exists():
            return []
        return [(responses_dir, scores_dir)]

    # Just model name - find runs
    model_dir = responses_base / run_path
    if not model_dir.exists():
        return []

    # Get all run directories (sorted by name = timestamp)
    run_dirs = sorted([d for d in model_dir.iterdir() if d.is_dir()])

    if not run_dirs:
        return []

    if all_runs:
        # Return all runs
        return [
            (run_dir, scores_base / run_path / run_dir.name) for run_dir in run_dirs
        ]
    else:
        # Return only latest run
        latest = run_dirs[-1]
        return [(latest, scores_base / run_path / latest.name)]


def score_run(responses_dir: Path, scores_dir: Path, args):
    """Score a single run."""
    if not responses_dir.exists():
        print(f"Responses directory not found: {responses_dir}")
        return

    # Create scores directory
    scores_dir.mkdir(parents=True, exist_ok=True)

    # Find response files to score (exclude config.json)
    response_files = [
        f for f in responses_dir.glob("*.json") if f.name != "config.json"
    ]

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
        "blocked": 0,  # Content filter blocked
        "skipped": 0,
        "total_points": 0,
        "points_earned": 0,
        "results": [],
    }

    for response_file in response_files:
        task_id = response_file.stem
        score_file = scores_dir / f"{task_id}.json"

        if score_file.exists():
            with open(score_file) as f:
                existing_score = json.load(f)

            if existing_score.get("judge") == "human-pending":
                result = validate_human_scores(score_file, existing_score)
                if result == "complete":
                    print(f"\n{task_id}: Human scores validated and finalized")
                    summary["total"] += 1
                    summary["passed"] += 1 if existing_score.get("passed") else 0
                    summary["failed"] += 0 if existing_score.get("passed") else 1
                    summary["total_points"] += existing_score.get("total_points", 0)
                    summary["points_earned"] += existing_score.get("points_earned", 0)
                    summary["results"].append(
                        {
                            "task_id": task_id,
                            "passed": existing_score.get("passed"),
                            "points_earned": existing_score.get("points_earned", 0),
                            "total_points": existing_score.get("total_points", 0),
                            "score_percent": existing_score.get("score_percent", 0),
                        }
                    )
                    continue
                elif result == "pending":
                    print(
                        f"Skipping {task_id} (human scores pending - fill in score file)"
                    )
                    summary["skipped"] += 1
                    continue

            if not args.rescore:
                print(f"Skipping {task_id} (already scored, use --rescore to override)")
                summary["skipped"] += 1
                continue

        # Load response
        with open(response_file) as f:
            response_data = json.load(f)

        # Check for content filter block
        stop_reason = response_data.get("stop_reason", "")
        if stop_reason == "content_filter":
            print(f"\n{task_id}: BLOCKED (content filter)")
            summary["total"] += 1
            summary["blocked"] += 1

            # Get task for total_points
            task = task_map.get(task_id)
            total_points = task.rubric.get("total_points", 100) if task else 100

            # Save blocked score
            score_data = {
                "task_id": task_id,
                "rubric_hash": get_rubric_hash(task.rubric) if task else "unknown",
                "scored_at": datetime.now().isoformat(),
                "passed": False,
                "blocked": True,
                "total_points": total_points,
                "points_earned": 0,
                "score_percent": 0,
                "criteria": [],
            }
            with open(score_file, "w") as f:
                json.dump(score_data, f, indent=2)

            summary["total_points"] += total_points
            summary["results"].append(
                {
                    "task_id": task_id,
                    "passed": False,
                    "blocked": True,
                    "points_earned": 0,
                    "total_points": total_points,
                    "score_percent": 0,
                }
            )
            continue

        # Get task rubric
        task = task_map.get(task_id)
        if not task:
            print(f"  Warning: No task found for {task_id}")
            continue

        # Determine evaluation type from rubric
        eval_type = get_evaluation_type(task.rubric)

        if eval_type in ["llm", "hybrid"] and judge is None and not args.human:
            print(f"Initializing LLM judge with model: {args.judge_model}")
            judge = LLMJudge(model=args.judge_model)

        print(f"\nScoring {task_id} (eval_type: {eval_type})...")
        try:
            score = score_task(
                task,
                response_data,
                judge=judge,
                human_judge=args.human,
                run_dir=responses_dir,
            )
        except Exception as e:
            details, error_summary, next_steps = build_error_report(e, args.verbose)

            print(f"\n{task_id}: ERROR during scoring")
            print(f"  {error_summary}")
            if next_steps:
                print("  Next steps:")
                for step in next_steps:
                    print(f"    - {step}")
            if args.verbose:
                print("  Details:")
                print(json.dumps(details, indent=2))
            raise
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
        print(
            f"Result: {status} ({score.points_earned:.1f}/{score.total_points:.1f} points, {score.score_percent:.1f}%){gated_note}"
        )

        # Print criterion details
        for result in score.criteria_results:
            icon = "+" if result.passed else "-"
            type_tag = f"[{result.criterion_type[:4]}]"
            print(
                f"    [{icon}] {type_tag} {result.criterion_id}: {result.details} ({result.points_earned:.1f}/{result.points:.1f})"
            )
            if not result.passed and result.actual != "[SKIPPED - gated]":
                actual_preview = (
                    result.actual[:80] + "..."
                    if len(result.actual) > 80
                    else result.actual
                )
                print(f"        Actual: {actual_preview}")

        has_human_judge = any(
            r.criterion_type == "human_judge" for r in score.criteria_results
        )
        if has_human_judge:
            judge_field = "human-pending"
        elif args.human:
            judge_field = None
        else:
            judge_field = args.judge_model

        criteria_data = []
        for r in score.criteria_results:
            criterion_entry = {
                "id": r.criterion_id,
                "passed": r.passed,
                "type": r.criterion_type,
                "match_type": r.match_type,
                "points": r.points,
                "points_earned": r.points_earned,
                "actual": r.actual,
                "details": r.details,
            }
            if r.criterion_type == "human_judge":
                criterion_entry["score"] = None
                criterion_entry["reasoning"] = ""
                criterion_entry["description"] = r.expected
            criteria_data.append(criterion_entry)

        score_data = {
            "task_id": score.task_id,
            "rubric_hash": get_rubric_hash(task.rubric),
            "scored_at": datetime.now().isoformat(),
            "passed": score.passed,
            "total_points": score.total_points,
            "points_earned": score.points_earned,
            "score_percent": score.score_percent,
            "llm_gated": score.llm_gated,
            "criteria": criteria_data,
        }
        if judge_field:
            score_data["judge"] = judge_field

        with open(score_file, "w") as f:
            json.dump(score_data, f, indent=2)

        summary["results"].append(
            {
                "task_id": task_id,
                "passed": score.passed,
                "points_earned": score.points_earned,
                "total_points": score.total_points,
                "score_percent": score.score_percent,
            }
        )

    # Save summary
    summary_file = scores_dir / "summary.json"
    overall_percent = (
        (summary["points_earned"] / summary["total_points"] * 100)
        if summary["total_points"] > 0
        else 0
    )
    summary["overall_percent"] = overall_percent
    summary["rubric_hashes"] = {
        r["task_id"]: get_rubric_hash(task_map[r["task_id"]].rubric)
        for r in summary["results"]
        if r["task_id"] in task_map
    }

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 50}")
    print(
        f"Summary: {summary['passed']}/{summary['total']} passed ({overall_percent:.1f}%)"
    )
    print(f"Points: {summary['points_earned']:.1f}/{summary['total_points']:.1f}")
    if summary["blocked"]:
        print(f"Blocked: {summary['blocked']} (content filter)")
    if summary["skipped"]:
        print(f"Skipped: {summary['skipped']}")
    print(f"Scores saved to: {scores_dir}")


def main():
    parser = argparse.ArgumentParser(description="Score IB-bench responses")
    parser.add_argument(
        "run_path", help="MODEL/RUN_ID for specific run, or MODEL for latest run"
    )
    parser.add_argument(
        "--all-runs",
        action="store_true",
        help="Score all runs for a model (when only MODEL is specified)",
    )
    parser.add_argument("--tasks", nargs="+", help="Specific task IDs to score")
    parser.add_argument(
        "--rescore", action="store_true", help="Rescore already-scored tasks"
    )
    parser.add_argument(
        "--judge-model",
        default="claude-sonnet-4-5-20250929",
        help="Model to use for LLM-as-judge scoring",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Generate templates for human scoring instead of LLM judge",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full API error details on failure",
    )
    args = parser.parse_args()

    # Find directories (responses/ and scores/ are directly under eval/)
    eval_dir = Path(__file__).parent
    runs = find_runs(eval_dir, args.run_path, args.all_runs)

    if not runs:
        print(f"No runs found for: {args.run_path}")
        return

    print(f"Found {len(runs)} run(s) to score")

    # Score each run
    for responses_dir, scores_dir in runs:
        run_id = f"{responses_dir.parent.name}/{responses_dir.name}"
        print(f"\n{'=' * 60}")
        print(f"Scoring run: {run_id}")
        print(f"{'=' * 60}")
        score_run(responses_dir, scores_dir, args)


if __name__ == "__main__":
    main()
