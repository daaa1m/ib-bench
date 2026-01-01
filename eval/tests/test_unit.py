"""
Unit tests for eval pipeline - no API calls required.

Run with: uv run pytest eval/tests/test_unit.py -v
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import (
    Task,
    LLMResponse,
    load_task,
    load_tasks,
    _extract_json,
    create_run_directory,
)
from score import (
    evaluate_substring_one_of,
    evaluate_regex_pattern,
    score_task,
    get_evaluation_type,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_task_dir(tmp_path):
    """Create a minimal task directory for testing."""
    task_dir = tmp_path / "e-test"
    task_dir.mkdir()

    # meta.yaml
    meta = {
        "task": {
            "id": "e-test",
            "type": "fix-error",
            "category": "excel",
            "description": "Test task description",
        },
    }
    (task_dir / "meta.yaml").write_text(yaml.dump(meta))

    # prompt.md
    (task_dir / "prompt.md").write_text("This is the test prompt.")

    # rubric.json
    rubric = {
        "task_id": "e-test",
        "version": "1.0",
        "total_points": 100,
        "criteria": {
            "test_criterion": {
                "description": "Must find the value",
                "type": "programmatic",
                "match_type": "substring_one_of",
                "accepted_values": ["A1", "B2", "C3"],
                "points": 100,
            }
        },
    }
    (task_dir / "rubric.json").write_text(json.dumps(rubric))

    # input file
    (task_dir / "input.txt").write_text("sample input")

    return task_dir


@pytest.fixture
def sample_response_data():
    """Sample LLM response data for scoring tests."""
    return {
        "task_id": "e-test",
        "model": "test-model",
        "raw_response": '{"error_location": "Cell A1", "corrected_formula": "=SUM(A1:A10)"}',
        "parsed_response": {
            "error_location": "Cell A1",
            "corrected_formula": "=SUM(A1:A10)",
        },
    }


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


# =============================================================================
# Test: JSON Extraction
# =============================================================================


class TestExtractJson:
    def test_direct_json(self):
        """Parse raw JSON string."""
        text = '{"key": "value", "number": 42}'
        result = _extract_json(text)
        assert result == {"key": "value", "number": 42}

    def test_json_with_whitespace(self):
        """Parse JSON with surrounding whitespace."""
        text = '   \n  {"key": "value"}  \n  '
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_json_in_code_block(self):
        """Extract JSON from markdown code block."""
        text = """
Here is my response:
```json
{"error_location": "A1", "formula": "=SUM(B1:B5)"}
```
That should fix the issue.
"""
        result = _extract_json(text)
        assert result["error_location"] == "A1"
        assert result["formula"] == "=SUM(B1:B5)"

    def test_json_in_plain_code_block(self):
        """Extract JSON from code block without json tag."""
        text = """
```
{"value": 123}
```
"""
        result = _extract_json(text)
        assert result == {"value": 123}

    def test_embedded_json(self):
        """Extract JSON embedded in prose."""
        text = 'The answer is {"result": "found", "cell": "B2"} as shown above.'
        result = _extract_json(text)
        assert result["result"] == "found"
        assert result["cell"] == "B2"

    def test_no_json_returns_none(self):
        """Return None when no JSON found."""
        text = "This is just plain text with no JSON."
        result = _extract_json(text)
        assert result is None

    def test_invalid_json_returns_none(self):
        """Return None for malformed JSON."""
        text = '{"key": "value", "broken"}'
        result = _extract_json(text)
        assert result is None

    def test_nested_json(self):
        """Parse JSON with nested objects."""
        text = '{"outer": {"inner": {"deep": 42}}}'
        result = _extract_json(text)
        assert result["outer"]["inner"]["deep"] == 42


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
# Test: Task Loading
# =============================================================================


class TestLoadTask:
    def test_load_basic_task(self, sample_task_dir):
        """Load a minimal task from directory."""
        task = load_task(sample_task_dir)

        assert task.id == "e-test"
        assert task.task_type == "fix-error"
        assert task.category == "excel"
        assert "test prompt" in task.prompt
        assert len(task.input_files) == 1
        assert task.input_files[0].name == "input.txt"

    def test_load_task_with_rubric(self, sample_task_dir):
        """Rubric is loaded when include_rubric=True."""
        task = load_task(sample_task_dir, include_rubric=True)
        assert "test_criterion" in task.rubric.get("criteria", {})

    def test_load_task_without_rubric(self, sample_task_dir):
        """Rubric is empty when include_rubric=False."""
        task = load_task(sample_task_dir, include_rubric=False)
        assert task.rubric == {}

    def test_load_task_multiple_inputs(self, sample_task_dir):
        """Multiple input files are detected."""
        (sample_task_dir / "input_appendix.pdf").write_bytes(b"fake pdf")
        (sample_task_dir / "input_data.xlsx").write_bytes(b"fake xlsx")

        task = load_task(sample_task_dir)
        assert len(task.input_files) == 3
        names = [f.name for f in task.input_files]
        assert "input.txt" in names
        assert "input_appendix.pdf" in names
        assert "input_data.xlsx" in names


class TestLoadTasks:
    def test_load_all_tasks(self, tmp_path):
        """Load multiple tasks from directory."""
        for task_id in ["e-001", "e-002"]:
            task_dir = tmp_path / task_id
            task_dir.mkdir()
            meta = {"task": {"id": task_id, "type": "test", "category": "test"}}
            (task_dir / "meta.yaml").write_text(yaml.dump(meta))
            (task_dir / "prompt.md").write_text(f"Prompt for {task_id}")

        tasks = load_tasks(tasks_dir=tmp_path, include_rubric=False)
        assert len(tasks) == 2
        ids = [t.id for t in tasks]
        assert "e-001" in ids
        assert "e-002" in ids

    def test_filter_by_task_ids(self, tmp_path):
        """Filter to specific task IDs."""
        for task_id in ["e-001", "e-002", "m-001"]:
            task_dir = tmp_path / task_id
            task_dir.mkdir()
            meta = {"task": {"id": task_id, "type": "test", "category": "test"}}
            (task_dir / "meta.yaml").write_text(yaml.dump(meta))
            (task_dir / "prompt.md").write_text(f"Prompt for {task_id}")

        tasks = load_tasks(
            tasks_dir=tmp_path, task_ids=["e-001", "m-001"], include_rubric=False
        )
        assert len(tasks) == 2
        ids = [t.id for t in tasks]
        assert "e-001" in ids
        assert "m-001" in ids
        assert "e-002" not in ids

    def test_filter_by_pattern(self, tmp_path):
        """Filter by prefix pattern."""
        for task_id in ["e-001", "e-002", "m-001", "h-001"]:
            task_dir = tmp_path / task_id
            task_dir.mkdir()
            meta = {"task": {"id": task_id, "type": "test", "category": "test"}}
            (task_dir / "meta.yaml").write_text(yaml.dump(meta))
            (task_dir / "prompt.md").write_text(f"Prompt for {task_id}")

        tasks = load_tasks(
            tasks_dir=tmp_path, filter_pattern="e-", include_rubric=False
        )
        assert len(tasks) == 2
        for t in tasks:
            assert t.id.startswith("e-")


# =============================================================================
# Test: Task Scoring
# =============================================================================


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


# =============================================================================
# Test: Run Directory Creation
# =============================================================================


class TestCreateRunDirectory:
    def test_creates_directory(self, tmp_path):
        """Directory is created with timestamp and model name."""
        run_dir = create_run_directory("claude-sonnet-4", base_dir=tmp_path)
        assert run_dir.exists()
        assert run_dir.is_dir()
        # Structure is {base_dir}/{model}/{timestamp}
        assert run_dir.parent.name == "claude-sonnet-4"

    def test_sanitizes_model_name(self, tmp_path):
        """Special characters in model name are sanitized."""
        run_dir = create_run_directory("gpt-4o/latest:v2", base_dir=tmp_path)
        assert "/" not in run_dir.name
        assert ":" not in run_dir.name
        assert run_dir.exists()

    def test_unique_directories(self, tmp_path):
        """Multiple calls create unique directories."""
        import time

        run_dir1 = create_run_directory("model", base_dir=tmp_path)
        time.sleep(0.01)
        run_dir2 = create_run_directory("model", base_dir=tmp_path)
        assert run_dir1.exists()
        assert run_dir2.exists()


# =============================================================================
# Test: LLMResponse Dataclass
# =============================================================================


class TestLLMResponse:
    def test_create_response(self):
        """Create LLMResponse with all fields."""
        resp = LLMResponse(
            raw_text='{"result": "ok"}',
            parsed_json={"result": "ok"},
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1234.5,
        )
        assert resp.model == "test-model"
        assert resp.input_tokens == 100
        assert resp.parsed_json["result"] == "ok"

    def test_response_with_none_json(self):
        """Response with no parsed JSON."""
        resp = LLMResponse(
            raw_text="Plain text response",
            parsed_json=None,
            model="test-model",
            input_tokens=50,
            output_tokens=25,
            latency_ms=500,
        )
        assert resp.parsed_json is None
