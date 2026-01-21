from pathlib import Path

import pytest

from llm_judge import LLMJudge


class FakeJudgeRunner:
    def __init__(self, response_text: str):
        self._response_text = response_text
        self.model = "fake"
        self.calls = []

    def judge(self, prompt: str, files: list[Path]) -> str:
        self.calls.append({"prompt": prompt, "files": files})
        return self._response_text


@pytest.mark.unit
def test_llm_judge_builds_prompt_includes_criteria(task_factory):
    task = task_factory(prompt="## Task\nDo X")
    rubric = {
        "criteria": {
            "accuracy": {"points": 50, "description": "Correct"},
            "clarity": {"points": 50, "description": "Clear"},
        }
    }
    runner = FakeJudgeRunner(
        '{"scores": {"accuracy": {"score": 1, "reasoning": "ok"}}}'
    )
    judge = LLMJudge(runner=runner)

    result = judge.score(rubric, [Path("file.pdf")], '{"answer": 1}', "Task text")

    assert "accuracy" in runner.calls[0]["prompt"]
    assert "clarity" in runner.calls[0]["prompt"]
    assert result["scores"]["accuracy"]["score"] == 1


@pytest.mark.unit
def test_llm_judge_parses_prose_scores_when_json_missing():
    runner = FakeJudgeRunner("accuracy: 0.8")
    judge = LLMJudge(runner=runner)

    rubric = {"criteria": {"accuracy": {"points": 100, "description": "Accurate"}}}
    result = judge.score(rubric, [], "{}", "Task text")

    assert result["scores"]["accuracy"]["score"] == pytest.approx(0.8)


@pytest.mark.unit
def test_llm_judge_handles_unparseable_response():
    runner = FakeJudgeRunner("nonsense")
    judge = LLMJudge(runner=runner)

    rubric = {"criteria": {"accuracy": {"points": 100, "description": "Accurate"}}}
    result = judge.score(rubric, [], "{}", "Task text")

    assert result["scores"] == {}
