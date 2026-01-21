from types import SimpleNamespace

import pytest

from eval.runners.openai import OpenAIRunner
from eval.runners.base import LLMResponse


@pytest.mark.unit
def test_openai_runner_handles_content_filter(mocker):
    runner = OpenAIRunner(model="gpt-4o", api_key="key")

    def fake_create(**_kwargs):
        raise RuntimeError("content policy violated")

    runner._client = SimpleNamespace(responses=SimpleNamespace(create=fake_create))

    response = runner.run(task=SimpleNamespace(prompt=""), input_files=[])

    assert isinstance(response, LLMResponse)
    assert response.stop_reason == "content_filter"


@pytest.mark.unit
def test_openai_runner_builds_tools_for_pdf_and_excel(mocker, tmp_path):
    runner = OpenAIRunner(model="gpt-4o", api_key="key")

    fake_response = SimpleNamespace(
        output_text="{}",
        output=[],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        stop_reason="end_turn",
    )

    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return fake_response

    runner._client = SimpleNamespace(
        responses=SimpleNamespace(create=fake_create),
        files=SimpleNamespace(
            create=lambda **_k: SimpleNamespace(id="f1"), delete=lambda *_a, **_k: None
        ),
        vector_stores=SimpleNamespace(
            create=lambda **_k: SimpleNamespace(id="vs1"),
            files=SimpleNamespace(create=lambda **_k: None),
            retrieve=lambda *_a, **_k: SimpleNamespace(
                file_counts=SimpleNamespace(completed=1, failed=0)
            ),
            delete=lambda *_a, **_k: None,
        ),
        containers=SimpleNamespace(
            files=SimpleNamespace(list=lambda **_k: SimpleNamespace(data=[]))
        ),
    )

    pdf = tmp_path / "input.pdf"
    pdf.write_text("x")
    xlsx = tmp_path / "input.xlsx"
    xlsx.write_text("x")

    runner.run(task=SimpleNamespace(prompt="hi"), input_files=[pdf, xlsx])

    tool_types = [tool["type"] for tool in captured["tools"]]
    assert "file_search" in tool_types
    assert "code_interpreter" in tool_types
