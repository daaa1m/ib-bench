import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "eval"
LLM_JUDGE_DIR = EVAL_DIR / "llm-judge"

for path in (REPO_ROOT, EVAL_DIR, LLM_JUDGE_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from eval.helpers import Task


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "slow: slow tests")


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False)
    parser.addoption("--integration", action="store_true", default=False)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture
def sample_rubric():
    return {
        "task_id": "e-000",
        "version": "1.0",
        "total_points": 100,
        "criteria": {
            "answer": {
                "description": "Provide the expected answer",
                "type": "programmatic",
                "match_type": "substring_one_of",
                "accepted_values": ["OK"],
                "points": 100,
            }
        },
    }


@pytest.fixture
def task_factory(tmp_path):
    def _create_task(
        task_id="e-000",
        rubric=None,
        prompt="## Task\nReturn JSON.",
        meta=None,
        inputs=None,
    ):
        task_dir = tmp_path / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        meta_payload = meta or {
            "task": {
                "id": task_id,
                "type": "extraction",
                "category": "document-review",
                "input_type": "pdf",
                "description": "Test task",
            }
        }
        (task_dir / "meta.yaml").write_text(yaml.safe_dump(meta_payload))
        (task_dir / "prompt.md").write_text(prompt)

        if rubric is not None:
            (task_dir / "rubric.json").write_text(json.dumps(rubric))

        input_files = []
        for name in inputs or []:
            file_path = task_dir / name
            file_path.write_text("fixture")
            input_files.append(file_path)

        return Task(
            id=task_id,
            task_dir=task_dir,
            task_type=meta_payload["task"]["type"],
            category=meta_payload["task"]["category"],
            description=meta_payload["task"].get("description", ""),
            prompt=prompt,
            rubric=rubric or {},
            input_files=input_files,
        )

    return _create_task


@pytest.fixture
def response_data_factory():
    def _make(parsed_response=None, output_files=None, stop_reason="end_turn"):
        return {
            "raw_response": "{}",
            "parsed_response": parsed_response,
            "output_files": output_files or [],
            "stop_reason": stop_reason,
        }

    return _make


@pytest.fixture
def score_args():
    return SimpleNamespace(
        tasks=None,
        rescore=True,
        judge_model="gpt-5.2-chat",
        judge_provider="azure-v2",
        human=False,
        verbose=False,
    )
