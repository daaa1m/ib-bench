"""
Tests for task loading and run directory creation.

Run with: uv run pytest tests/unit/test_task_loading.py -v
"""

import json
import sys
import time
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import LLMResponse, Task, create_run_directory, load_task, load_tasks


# =============================================================================
# Test: Task Loading
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
        assert resp.parsed_json is not None
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

    def test_response_with_output_files(self):
        """Response with output files from code execution."""
        from helpers import OutputFile

        output_file = OutputFile(
            filename="output.xlsx",
            content=b"fake excel",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = LLMResponse(
            raw_text='{"result": "ok"}',
            parsed_json={"result": "ok"},
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1000,
            output_files=[output_file],
        )
        assert resp.output_files is not None
        assert len(resp.output_files) == 1
        assert resp.output_files[0].filename == "output.xlsx"
