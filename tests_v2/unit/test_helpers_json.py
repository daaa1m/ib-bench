import json

import pytest

from eval.helpers import (
    extract_json,
    extract_task_section,
    get_rubric_hash,
    retry_on_rate_limit,
)


@pytest.mark.unit
def test_extract_json_plain_object_parses():
    payload = {"answer": "OK"}
    text = json.dumps(payload)
    assert extract_json(text) == payload


@pytest.mark.unit
def test_extract_json_code_block_parses():
    text = """Here is JSON:\n```json\n{\"answer\": \"OK\"}\n```"""
    assert extract_json(text) == {"answer": "OK"}


@pytest.mark.unit
def test_extract_json_partial_object_closes_brace():
    text = '{"answer": "OK"'
    assert extract_json(text) == {"answer": "OK"}


@pytest.mark.unit
def test_extract_task_section_returns_content():
    prompt = "# Title\n\n## Task\nDo the thing\n\n## Output\nJSON"
    assert extract_task_section(prompt) == "Do the thing"


@pytest.mark.unit
def test_extract_task_section_missing_raises():
    with pytest.raises(ValueError):
        extract_task_section("# Title\nNo task section")


@pytest.mark.unit
def test_get_rubric_hash_deterministic():
    rubric = {"task_id": "e-000", "criteria": {"a": {"points": 1}}}
    assert get_rubric_hash(rubric) == get_rubric_hash(rubric)


@pytest.mark.unit
def test_retry_on_rate_limit_retries_then_succeeds(mocker):
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("429 rate limit")
        return "ok"

    sleeper = mocker.patch("eval.helpers.time.sleep")

    wrapped = retry_on_rate_limit(max_retries=3, initial_wait=1)(flaky)
    assert wrapped() == "ok"
    assert calls["count"] == 3
    assert sleeper.call_count == 2
