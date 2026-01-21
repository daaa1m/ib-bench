from types import SimpleNamespace

import pytest

from eval.runners.gemini import GeminiRunner
from eval.runners.base import LLMResponse


@pytest.mark.unit
def test_gemini_runner_handles_safety_finish_reason(mocker):
    runner = GeminiRunner(model="gemini-2.0-flash", api_key="key")

    fake_response = SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason="SAFETY")],
        usage_metadata=SimpleNamespace(prompt_token_count=1, candidates_token_count=0),
    )

    runner._client = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_k: fake_response)
    )
    response = runner.run(task=SimpleNamespace(prompt="hi"), input_files=[])

    assert isinstance(response, LLMResponse)
    assert response.stop_reason == "content_filter"


@pytest.mark.unit
def test_gemini_runner_extracts_inline_data(mocker, tmp_path):
    runner = GeminiRunner(model="gemini-2.0-flash", api_key="key")

    inline = SimpleNamespace(mime_type="application/octet-stream", data=b"data")
    part = SimpleNamespace(text="answer", inline_data=inline)
    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(content=SimpleNamespace(parts=[part]), finish_reason="STOP")
        ],
        usage_metadata=SimpleNamespace(prompt_token_count=1, candidates_token_count=1),
    )

    runner._client = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_k: fake_response)
    )

    response = runner.run(task=SimpleNamespace(prompt="hi"), input_files=[])

    assert response.output_files
    assert response.output_files[0].content == b"data"
