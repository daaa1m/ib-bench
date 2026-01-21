import json
from types import SimpleNamespace

import pytest

from eval.score import score_run


@pytest.mark.integration
def test_score_run_writes_scores_only(tmp_path, task_factory, sample_rubric, score_args, mocker):
    responses_dir = tmp_path / "responses"
    scores_dir = tmp_path / "scores"
    responses_dir.mkdir(parents=True)

    task = task_factory(task_id="e-000", rubric=sample_rubric)

    response_payload = {
        "task_id": task.id,
        "raw_response": "{}",
        "parsed_response": {"answer": "OK"},
        "output_files": [],
        "stop_reason": "end_turn",
    }
    (responses_dir / "e-000.json").write_text(json.dumps(response_payload))

    mocker.patch("eval.score.load_tasks", return_value=[task])

    score_run(responses_dir, scores_dir, score_args)

    score_file = scores_dir / "e-000.json"
    assert score_file.exists()

    data = json.loads(score_file.read_text())
    assert data["task_id"] == "e-000"
    assert data["passed"] is True
