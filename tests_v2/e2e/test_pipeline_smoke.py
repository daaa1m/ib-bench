import json
from types import SimpleNamespace

import pytest

from eval.run import run_task
from eval.runners.base import LLMResponse
from eval.score import score_task


@pytest.mark.slow
def test_e2e_smoke_run_and_score(tmp_path, task_factory):
    task = task_factory(
        task_id="e-000",
        rubric={
            "task_id": "e-000",
            "total_points": 100,
            "criteria": {
                "answer": {
                    "type": "programmatic",
                    "match_type": "substring_one_of",
                    "accepted_values": ["OK"],
                    "points": 100,
                }
            },
        },
    )

    class FakeRunner:
        model = "fake"

        def run(self, _task, input_files=None):
            return LLMResponse(
                raw_text='{"answer": "OK"}',
                parsed_json={"answer": "OK"},
                model="fake",
                input_tokens=1,
                output_tokens=1,
                latency_ms=1.0,
                stop_reason="end_turn",
                output_files=None,
            )

    run_dir = tmp_path / "responses"
    run_dir.mkdir()

    response_data = run_task(task, FakeRunner(), run_dir)
    assert response_data["parsed_response"]["answer"] == "OK"

    score = score_task(task, response_data, judge=None, run_dir=run_dir)
    assert score.passed is True
