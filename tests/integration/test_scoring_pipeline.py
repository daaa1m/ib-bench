"""
Integration tests for the scoring pipeline.

Tests the full flow from response files through scoring without
hitting real APIs. Uses mock LLM responses to verify the pipeline.

Run with: uv run pytest tests/integration/test_scoring_pipeline.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import Task
from score import score_task, get_evaluation_type


class TestScoringPipelineIntegration:
    """Tests for end-to-end scoring pipeline."""

    def test_programmatic_scoring_full_flow(self, sample_task):
        """Complete programmatic scoring flow produces correct results."""
        # Response data dict (as stored in response JSON files)
        response_data = {
            "raw_response": '{"error_location": "Row 140", "corrected_formula": "=SUM(A1:A138)"}',
            "parsed_response": {
                "error_location": "Row 140",
                "corrected_formula": "=SUM(A1:A138)",
            },
        }

        result = score_task(sample_task, response_data, judge=None)

        assert result.score_percent == 100
        assert all(cr.passed for cr in result.criteria_results)

    def test_partial_score_when_one_criterion_fails(self, sample_task):
        """Partial score when some criteria pass and others fail."""
        # Response that matches only error_location
        response_data = {
            "raw_response": '{"error_location": "L140", "corrected_formula": "wrong formula"}',
            "parsed_response": {
                "error_location": "L140",
                "corrected_formula": "wrong formula",
            },
        }

        result = score_task(sample_task, response_data, judge=None)

        assert result.score_percent == 50  # Only error_location (50 pts) passed
        # Find the criteria results by ID
        error_loc = next(
            cr for cr in result.criteria_results if cr.criterion_id == "error_location"
        )
        formula = next(
            cr
            for cr in result.criteria_results
            if cr.criterion_id == "corrected_formula"
        )
        assert error_loc.passed is True
        assert formula.passed is False

    def test_zero_score_when_json_parse_fails(self, sample_task):
        """Zero score when response has no parseable JSON."""
        response_data = {
            "raw_response": "I couldn't find any errors in the spreadsheet.",
            "parsed_response": None,
        }

        result = score_task(sample_task, response_data, judge=None)

        assert result.score_percent == 0
        assert result.passed is False

    def test_blocked_response_still_scores_zero(self, sample_task):
        """Content-filtered responses score zero."""
        response_data = {
            "raw_response": "",
            "parsed_response": None,
            "stop_reason": "content_filter",
        }

        result = score_task(sample_task, response_data, judge=None)

        assert result.score_percent == 0
        assert result.passed is False


class TestEvaluationTypeDetection:
    """Tests for automatic evaluation type detection."""

    def test_detects_programmatic_only(self, sample_rubric):
        """Rubric with only programmatic criteria detected correctly."""
        eval_type = get_evaluation_type(sample_rubric)
        assert eval_type == "programmatic"

    def test_detects_llm_judge_only(self):
        """Rubric with only LLM judge criteria detected correctly."""
        rubric = {
            "criteria": {
                "quality": {
                    "type": "llm_judge",
                    "description": "Quality assessment",
                    "points": 100,
                }
            }
        }
        eval_type = get_evaluation_type(rubric)
        assert eval_type == "llm"  # Returns "llm" not "llm_judge"

    def test_detects_hybrid(self, sample_rubric_with_llm_judge):
        """Rubric with mixed criteria detected as hybrid."""
        eval_type = get_evaluation_type(sample_rubric_with_llm_judge)
        assert eval_type == "hybrid"


class TestGatingBehavior:
    """Tests for gates_llm functionality."""

    def test_llm_criteria_skipped_when_gate_fails(
        self, sample_rubric_with_llm_judge, tmp_path
    ):
        """LLM judge criteria are skipped when gating criterion fails."""
        # Create task with hybrid rubric
        task_dir = tmp_path / "gate-test"
        task_dir.mkdir()

        (task_dir / "rubric.json").write_text(json.dumps(sample_rubric_with_llm_judge))
        (task_dir / "prompt.md").write_text("Test prompt")
        (task_dir / "meta.yaml").write_text("task:\n  id: gate-test")

        task = Task(
            id="gate-test",
            task_dir=task_dir,
            task_type="fix-error",
            category="financial-analysis",
            description="Test gating",
            prompt="Test prompt",
            rubric=sample_rubric_with_llm_judge,
            input_files=[],
        )

        # Response that fails the gating criterion
        response_data = {
            "raw_response": '{"error_location": "wrong location"}',
            "parsed_response": {"error_location": "wrong location"},
        }

        result = score_task(task, response_data, judge=None)

        # Gate failed, so LLM criteria should be skipped
        error_loc = next(
            cr for cr in result.criteria_results if cr.criterion_id == "error_location"
        )
        explanation = next(
            cr
            for cr in result.criteria_results
            if cr.criterion_id == "explanation_quality"
        )
        assert error_loc.passed is False
        assert (
            "skipped" in explanation.details.lower()
            or "gated" in explanation.details.lower()
        )


class TestMultipleCriteriaMatching:
    """Tests for various match types."""

    def test_substring_one_of_matches_any_variant(self, tmp_path):
        """substring_one_of passes if any accepted value is found."""
        rubric = {
            "criteria": {
                "location": {
                    "type": "programmatic",
                    "match_type": "substring_one_of",
                    "accepted_values": ["Row 140", "L140", "M140", "row 140"],
                    "points": 100,
                    "description": "Test",
                }
            }
        }

        task = Task(
            id="match-test",
            task_dir=tmp_path,
            task_type="test",
            category="test",
            description="Test",
            prompt="Test",
            rubric=rubric,
            input_files=[],
        )

        # Test different valid variants
        for location in ["Row 140", "L140", "M140", "row 140"]:
            response_data = {
                "raw_response": f'{{"location": "{location}"}}',
                "parsed_response": {"location": location},
            }
            result = score_task(task, response_data, judge=None)
            loc_result = next(
                cr for cr in result.criteria_results if cr.criterion_id == "location"
            )
            assert loc_result.passed is True, f"Failed for {location}"

    def test_regex_pattern_matches_correctly(self, tmp_path):
        """regex_pattern correctly matches valid patterns."""
        rubric = {
            "criteria": {
                "formula": {
                    "type": "programmatic",
                    "match_type": "regex_pattern",
                    "valid_patterns": [r"=SUM\([A-Z]+\d+:[A-Z]+\d+\)"],
                    "points": 100,
                    "description": "Test",
                }
            }
        }

        task = Task(
            id="regex-test",
            task_dir=tmp_path,
            task_type="test",
            category="test",
            description="Test",
            prompt="Test",
            rubric=rubric,
            input_files=[],
        )

        # Valid formula
        response_data = {
            "raw_response": '{"formula": "=SUM(A1:B10)"}',
            "parsed_response": {"formula": "=SUM(A1:B10)"},
        }
        result = score_task(task, response_data, judge=None)
        formula_result = next(
            cr for cr in result.criteria_results if cr.criterion_id == "formula"
        )
        assert formula_result.passed is True

        # Invalid formula
        response_data = {
            "raw_response": '{"formula": "=AVG(A1:B10)"}',
            "parsed_response": {"formula": "=AVG(A1:B10)"},
        }
        result = score_task(task, response_data, judge=None)
        formula_result = next(
            cr for cr in result.criteria_results if cr.criterion_id == "formula"
        )
        assert formula_result.passed is False
