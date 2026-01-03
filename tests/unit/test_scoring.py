"""
Tests for scoring functions and evaluation logic.

Run with: uv run pytest tests/unit/test_scoring.py -v
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import Task
from score import (
    CriterionResult,
    TaskScore,
    evaluate_regex_pattern,
    evaluate_substring_one_of,
    get_evaluation_type,
    score_task,
)


# =============================================================================
# Test: Substring Matching
# =============================================================================


class TestEvaluateSubstringOneOf:
    def test_exact_match(self):
        """Exact value matches."""
        passed, details = evaluate_substring_one_of("L140", ["L140", "M140"])
        assert passed is True
        assert "L140" in details

    def test_substring_match(self):
        """Value contains accepted substring."""
        passed, details = evaluate_substring_one_of(
            "The error is in Row 140 of the sheet", ["Row 140", "L140"]
        )
        assert passed is True

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        passed, details = evaluate_substring_one_of("row 140", ["Row 140"])
        assert passed is True

    def test_no_match(self):
        """No accepted values match."""
        passed, details = evaluate_substring_one_of("Cell A1", ["B2", "C3"])
        assert passed is False
        assert "None of" in details

    def test_empty_value(self):
        """Empty value doesn't match."""
        passed, details = evaluate_substring_one_of("", ["A1", "B2"])
        assert passed is False

    def test_empty_accepted_values(self):
        """Empty accepted values list never matches."""
        passed, details = evaluate_substring_one_of("anything", [])
        assert passed is False

    def test_forbidden_elements_fail(self):
        """Fails if forbidden element is present, even if accepted value matches."""
        passed, details = evaluate_substring_one_of(
            "=SUM(A138:A140) + #REF!", ["138"], ["#REF!"]
        )
        assert passed is False
        assert "forbidden" in details.lower()

    def test_forbidden_elements_pass(self):
        """Passes if accepted value matches and no forbidden elements."""
        passed, details = evaluate_substring_one_of(
            "=SUM(A138:A140)", ["138"], ["#REF!"]
        )
        assert passed is True


# =============================================================================
# Test: Regex Pattern Matching
# =============================================================================


class TestEvaluateRegexPattern:
    def test_simple_pattern_match(self):
        """Basic regex pattern matches."""
        passed, details = evaluate_regex_pattern(
            "=SUM(A135:A139)", patterns=["SUM\\(.*135.*139.*\\)"]
        )
        assert passed is True

    def test_required_elements_present(self):
        """All required elements found."""
        passed, details = evaluate_regex_pattern(
            "=SUM(A138+A139)", patterns=[], required_elements=["138", "139"]
        )
        assert passed is True

    def test_required_elements_missing(self):
        """Missing required element fails."""
        passed, details = evaluate_regex_pattern(
            "=SUM(A135:A139)", patterns=[], required_elements=["138"]
        )
        assert passed is False
        assert "Missing" in details

    def test_forbidden_elements_fail(self):
        """Forbidden element causes failure."""
        passed, details = evaluate_regex_pattern(
            "=SUM(A1:A10) #REF!",
            patterns=["SUM.*"],
            forbidden_elements=["#REF!"],
        )
        assert passed is False
        assert "forbidden" in details.lower()

    def test_forbidden_empty_string_skipped(self):
        """Empty string in forbidden list is skipped."""
        passed, details = evaluate_regex_pattern(
            "=SUM(A138:A139)",
            patterns=["SUM.*138.*"],
            forbidden_elements=["", "#REF!"],
        )
        assert passed is True

    def test_multiple_patterns_any_match(self):
        """Any pattern matching is sufficient."""
        passed, details = evaluate_regex_pattern(
            "A138+A139",
            patterns=["SUM\\(.*\\)", "\\+.*138", "138.*\\+"],
        )
        assert passed is True

    def test_no_patterns_match(self):
        """No patterns match fails."""
        passed, details = evaluate_regex_pattern(
            "A1+A2",
            patterns=["SUM\\(.*\\)", "138"],
        )
        assert passed is False

    def test_case_insensitive_pattern(self):
        """Pattern matching is case-insensitive."""
        passed, details = evaluate_regex_pattern(
            "=sum(a1:a10)", patterns=["SUM\\(.*\\)"]
        )
        assert passed is True


# =============================================================================
# Test: Evaluation Type Detection
# =============================================================================


class TestGetEvaluationType:
    def test_programmatic_only(self):
        """Rubric with only programmatic criteria."""
        rubric = {
            "criteria": {
                "check1": {"type": "programmatic", "match_type": "substring_one_of"},
                "check2": {"type": "programmatic", "match_type": "regex_pattern"},
            }
        }
        assert get_evaluation_type(rubric) == "programmatic"

    def test_llm_only(self):
        """Rubric with only llm_judge criteria."""
        rubric = {
            "criteria": {
                "quality": {"type": "llm_judge", "points": 50},
                "accuracy": {"type": "llm_judge", "points": 50},
            }
        }
        assert get_evaluation_type(rubric) == "llm"

    def test_hybrid(self):
        """Rubric with both programmatic and llm_judge criteria."""
        rubric = {
            "criteria": {
                "check1": {"type": "programmatic", "match_type": "substring_one_of"},
                "quality": {"type": "llm_judge", "points": 20},
            }
        }
        assert get_evaluation_type(rubric) == "hybrid"

    def test_empty_criteria(self):
        """Empty criteria defaults to programmatic."""
        rubric = {"criteria": {}}
        assert get_evaluation_type(rubric) == "programmatic"


# =============================================================================
# Test: Task Scoring
# =============================================================================


@pytest.fixture
def e001_rubric():
    """Real rubric structure from e-001 task."""
    return {
        "task_id": "e-001",
        "version": "1.0",
        "total_points": 100,
        "criteria": {
            "error_location": {
                "description": "Must identify the Cash from Investing subtotal row or specific cells.",
                "type": "programmatic",
                "match_type": "substring_one_of",
                "accepted_values": [
                    "Row 140",
                    "140",
                    "L140",
                    "M140",
                    "N140",
                    "O140",
                    "P140",
                    "L140:P140",
                    "Range 140",
                ],
                "points": 42,
                "gates_llm": True,
            },
            "corrected_formula": {
                "description": "Must include Row 138 (Maintenance Capex) in the sum.",
                "type": "programmatic",
                "match_type": "regex_pattern",
                "required_elements": ["138"],
                "forbidden_elements": ["#REF!", ""],
                "valid_patterns": [
                    "SUM\\(.*138.*139.*\\)",
                    "SUM\\(.*135.*139.*\\)",
                    "\\+.*138",
                    "138.*\\+",
                ],
                "points": 43,
                "gates_llm": True,
            },
            "logical_explanation": {
                "description": "Must explain that Maintenance Capex was excluded.",
                "type": "llm_judge",
                "core_concepts": [
                    "Maintenance Capex",
                    "Row 138",
                    "missing",
                    "excluded",
                ],
                "points": 15,
            },
        },
    }


class TestScoreTask:
    def test_all_programmatic_pass(self, e001_rubric):
        """All programmatic criteria passing gives full programmatic points."""
        task = Task(
            id="e-001",
            task_dir=Path("."),
            task_type="fix-error",
            category="excel",
            description="Test",
            prompt="",
            rubric=e001_rubric,
            input_files=[],
        )
        response_data = {
            "parsed_response": {
                "error_location": "The error is in Row 140",
                "corrected_formula": "=SUM(L135:L139) includes 138",
            }
        }

        score = score_task(task, response_data, judge=None)

        # Programmatic: 42 + 43 = 85 points earned
        assert score.points_earned == 85
        assert score.score_percent == 85.0
        assert score.passed is True  # >= 60%

    def test_partial_criteria_fail(self, e001_rubric):
        """Some criteria failing gives partial score."""
        task = Task(
            id="e-001",
            task_dir=Path("."),
            task_type="fix-error",
            category="excel",
            description="Test",
            prompt="",
            rubric=e001_rubric,
            input_files=[],
        )
        response_data = {
            "parsed_response": {
                "error_location": "The error is in Row 140",
                "corrected_formula": "=SUM(A1:A10)",  # Missing 138
            }
        }

        score = score_task(task, response_data, judge=None)

        # Only location passes: 42 points
        assert score.points_earned == 42
        assert score.score_percent == 42.0
        assert score.passed is False  # < 60%

    def test_no_parsed_json_fails(self, e001_rubric):
        """Missing parsed_response fails immediately."""
        task = Task(
            id="e-001",
            task_dir=Path("."),
            task_type="fix-error",
            category="excel",
            description="Test",
            prompt="",
            rubric=e001_rubric,
            input_files=[],
        )
        response_data = {
            "parsed_response": None,
            "raw_response": "Some text without JSON",
        }

        score = score_task(task, response_data, judge=None)
        assert score.passed is False
        assert score.points_earned == 0

    def test_empty_rubric_criteria(self):
        """Empty criteria list means zero points."""
        task = Task(
            id="test",
            task_dir=Path("."),
            task_type="test",
            category="test",
            description="Test",
            prompt="",
            rubric={"criteria": {}, "total_points": 100},
            input_files=[],
        )
        response_data = {"parsed_response": {"some": "data"}}

        score = score_task(task, response_data, judge=None)
        assert score.passed is False
        assert score.points_earned == 0

    def test_gates_llm_when_programmatic_fails(self, e001_rubric):
        """LLM criteria are gated when gates_llm programmatic criteria fail."""
        task = Task(
            id="e-001",
            task_dir=Path("."),
            task_type="fix-error",
            category="excel",
            description="Test",
            prompt="",
            rubric=e001_rubric,
            input_files=[],
        )
        response_data = {
            "parsed_response": {
                "error_location": "Wrong location",  # Fails - gates LLM
                "corrected_formula": "=SUM(A1:A10)",  # Also fails
            }
        }

        score = score_task(task, response_data, judge=None)

        assert score.llm_gated is True
        assert score.points_earned == 0  # All failed

    def test_programmatic_only_rubric(self):
        """Rubric with only programmatic criteria."""
        rubric = {
            "task_id": "test",
            "total_points": 100,
            "criteria": {
                "check1": {
                    "type": "programmatic",
                    "match_type": "substring_one_of",
                    "accepted_values": ["yes"],
                    "points": 50,
                },
                "check2": {
                    "type": "programmatic",
                    "match_type": "substring_one_of",
                    "accepted_values": ["correct"],
                    "points": 50,
                },
            },
        }
        task = Task(
            id="test",
            task_dir=Path("."),
            task_type="test",
            category="test",
            description="Test",
            prompt="",
            rubric=rubric,
            input_files=[],
        )
        response_data = {
            "parsed_response": {
                "check1": "yes",
                "check2": "correct",
            }
        }

        score = score_task(task, response_data, judge=None)
        assert score.passed is True
        assert score.points_earned == 100
        assert score.score_percent == 100.0
