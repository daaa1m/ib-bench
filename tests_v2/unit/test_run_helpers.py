import json
from pathlib import Path

import pytest

from eval.run import _build_response_data, _select_input_files
from eval.runners.base import LLMResponse, OutputFile


@pytest.mark.unit
def test_select_input_files_filters_supported_suffixes(task_factory):
    task = task_factory(inputs=["input.xlsx", "input.pdf", "input.txt", "input.xls"])
    selected = _select_input_files(task)
    assert [f.name for f in selected] == ["input.xlsx", "input.pdf", "input.xls"]


@pytest.mark.unit
def test_build_response_data_includes_usage_fields():
    response = LLMResponse(
        raw_text="raw",
        parsed_json={"answer": "OK"},
        model="model",
        input_tokens=1,
        output_tokens=2,
        latency_ms=3.0,
        stop_reason="end_turn",
        output_files=[OutputFile(filename="out.txt", content=b"x")],
    )

    data = _build_response_data("e-000", response, [], ["out.txt"])

    assert data["usage"]["input_tokens"] == 1
    assert data["usage"]["output_tokens"] == 2
    assert data["usage"]["latency_ms"] == 3.0
    assert data["output_files"] == ["out.txt"]


@pytest.mark.unit
def test_build_response_data_serializable():
    response = LLMResponse(
        raw_text="raw",
        parsed_json=None,
        model="model",
        input_tokens=0,
        output_tokens=0,
        latency_ms=0.0,
        stop_reason="end_turn",
        output_files=None,
    )
    data = _build_response_data("e-000", response, [], [])
    json.dumps(data)
    assert data["task_id"] == "e-000"
