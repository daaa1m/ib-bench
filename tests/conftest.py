"""
Shared fixtures and configuration for all tests.

This module provides:
- VCR configuration for integration tests
- Mock response factories for API runners
- Sample task/rubric fixtures for unit and mock tests
"""

import json
import sys
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

# Add eval directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))

from helpers import Task
from runners import LLMResponse, OutputFile


# =============================================================================
# VCR Configuration (for integration tests)
# =============================================================================


@pytest.fixture(scope="module")
def vcr_config():
    """VCR configuration for recording/replaying API calls."""
    return {
        "filter_headers": [
            ("authorization", "REDACTED"),
            ("x-api-key", "REDACTED"),
            ("api-key", "REDACTED"),
        ],
        "filter_post_data_parameters": [
            ("api_key", "REDACTED"),
        ],
        "record_mode": "once",  # Record once, replay forever
        "match_on": ["method", "scheme", "host", "port", "path"],
        "cassette_library_dir": str(
            Path(__file__).parent / "integration" / "cassettes"
        ),
    }


@pytest.fixture(scope="module")
def vcr_cassette_dir():
    """Directory for VCR cassettes."""
    return str(Path(__file__).parent / "integration" / "cassettes")


# =============================================================================
# Sample Task Fixtures
# =============================================================================


@pytest.fixture
def sample_rubric() -> dict[str, Any]:
    """Sample rubric with programmatic criteria."""
    return {
        "task_id": "test-001",
        "version": "1.0",
        "total_points": 100,
        "criteria": {
            "error_location": {
                "description": "Must identify the error location",
                "type": "programmatic",
                "match_type": "substring_one_of",
                "accepted_values": ["Row 140", "L140", "M140"],
                "points": 50,
            },
            "corrected_formula": {
                "description": "Must provide corrected formula",
                "type": "programmatic",
                "match_type": "regex_pattern",
                "valid_patterns": [r"SUM\(.*138.*\)"],
                "required_elements": ["138"],
                "points": 50,
            },
        },
    }


@pytest.fixture
def sample_rubric_with_llm_judge() -> dict[str, Any]:
    """Sample rubric with both programmatic and LLM judge criteria."""
    return {
        "task_id": "test-002",
        "version": "1.0",
        "total_points": 100,
        "criteria": {
            "error_location": {
                "description": "Must identify the error location",
                "type": "programmatic",
                "match_type": "substring_one_of",
                "accepted_values": ["Row 140", "L140"],
                "points": 42,
                "gates_llm": True,
            },
            "explanation_quality": {
                "description": "Must explain the error clearly",
                "type": "llm_judge",
                "core_concepts": ["Maintenance Capex", "excluded"],
                "points": 58,
            },
        },
    }


@pytest.fixture
def sample_task(tmp_path, sample_rubric) -> Task:
    """Create a sample Task with temporary files."""
    task_dir = tmp_path / "test-001"
    task_dir.mkdir()

    # Create meta.yaml
    meta = {
        "task": {
            "id": "test-001",
            "title": "Test Task",
            "type": "fix-error",
            "category": "financial-analysis",
            "input_type": "excel",
            "description": "A test task for unit testing",
        }
    }
    (task_dir / "meta.yaml").write_text(yaml.dump(meta))

    # Create prompt.md
    prompt = """# Test Task

Find the error in the spreadsheet and fix it.

## Output Format
```json
{
    "error_location": "...",
    "corrected_formula": "..."
}
```
"""
    (task_dir / "prompt.md").write_text(prompt)

    # Create rubric.json
    (task_dir / "rubric.json").write_text(json.dumps(sample_rubric))

    # Create dummy input file
    (task_dir / "input.xlsx").write_bytes(b"fake excel content")

    return Task(
        id="test-001",
        task_dir=task_dir,
        task_type="fix-error",
        category="financial-analysis",
        description="A test task for unit testing",
        prompt=prompt,
        rubric=sample_rubric,
        input_files=[task_dir / "input.xlsx"],
    )


@pytest.fixture
def sample_task_text_only(tmp_path) -> Task:
    """Create a sample Task without input files (text-only prompt)."""
    task_dir = tmp_path / "test-text"
    task_dir.mkdir()

    meta = {
        "task": {
            "id": "test-text",
            "title": "Text Only Task",
            "type": "summarise",
            "category": "document-review",
            "description": "A text-only test task",
        }
    }
    (task_dir / "meta.yaml").write_text(yaml.dump(meta))

    prompt = "Summarize the following: The quick brown fox jumps over the lazy dog."
    (task_dir / "prompt.md").write_text(prompt)

    rubric = {
        "task_id": "test-text",
        "version": "1.0",
        "total_points": 100,
        "criteria": {
            "summary": {
                "type": "programmatic",
                "match_type": "substring_one_of",
                "accepted_values": ["fox", "dog"],
                "points": 100,
            }
        },
    }
    (task_dir / "rubric.json").write_text(json.dumps(rubric))

    return Task(
        id="test-text",
        task_dir=task_dir,
        task_type="summarise",
        category="document-review",
        description="A text-only test task",
        prompt=prompt,
        rubric=rubric,
        input_files=[],
    )


# =============================================================================
# Mock Response Factories
# =============================================================================


@pytest.fixture
def make_llm_response() -> Callable[..., LLMResponse]:
    """Factory for creating LLMResponse objects."""

    def _make_response(
        raw_text: str = '{"result": "ok"}',
        parsed_json: dict[str, Any] | None = None,
        model: str = "test-model",
        input_tokens: int = 100,
        output_tokens: int = 50,
        latency_ms: float = 1000.0,
        stop_reason: str = "end_turn",
        output_files: list[OutputFile] | None = None,
    ) -> LLMResponse:
        if parsed_json is None and raw_text.startswith("{"):
            try:
                parsed_json = json.loads(raw_text)
            except json.JSONDecodeError:
                parsed_json = None

        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed_json,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            stop_reason=stop_reason,
            output_files=output_files,
        )

    return _make_response


@pytest.fixture
def mock_anthropic_message(mocker):
    """Factory for creating mock Anthropic message responses."""

    def _make_message(
        text: str = '{"result": "ok"}',
        input_tokens: int = 100,
        output_tokens: int = 50,
        stop_reason: str = "end_turn",
    ):
        return mocker.Mock(
            content=[mocker.Mock(text=text)],
            usage=mocker.Mock(input_tokens=input_tokens, output_tokens=output_tokens),
            stop_reason=stop_reason,
        )

    return _make_message


@pytest.fixture
def mock_anthropic_beta_message(mocker):
    """Factory for creating mock Anthropic beta message responses (with code execution)."""

    def _make_message(
        text: str = '{"result": "ok"}',
        input_tokens: int = 100,
        output_tokens: int = 50,
        stop_reason: str = "end_turn",
        container_id: str | None = None,
        stdout: str | None = None,
    ):
        content = [mocker.Mock(text=text, type="text")]

        if container_id or stdout:
            code_result = mocker.Mock(type="code_execution_result")
            code_result.container_id = container_id
            if stdout:
                code_result.content = [mocker.Mock(stdout=stdout, text=None)]
            else:
                code_result.content = []
            content.append(code_result)

        return mocker.Mock(
            content=content,
            usage=mocker.Mock(input_tokens=input_tokens, output_tokens=output_tokens),
            stop_reason=stop_reason,
        )

    return _make_message


@pytest.fixture
def mock_openai_response(mocker):
    """Factory for creating mock OpenAI Responses API responses."""

    def _make_response(
        text: str = '{"result": "ok"}',
        input_tokens: int = 100,
        output_tokens: int = 50,
        stop_reason: str = "stop",
    ):
        response = mocker.Mock()
        response.output_text = text
        response.usage = mocker.Mock(
            input_tokens=input_tokens, output_tokens=output_tokens
        )
        response.stop_reason = stop_reason
        response.output = []  # No tool outputs by default
        return response

    return _make_response


@pytest.fixture
def mock_gemini_response(mocker):
    """Factory for creating mock Gemini generate_content responses."""

    def _make_response(
        text: str = '{"result": "ok"}',
        input_tokens: int = 100,
        output_tokens: int = 50,
        finish_reason: str = "STOP",
    ):
        part = mocker.Mock()
        part.text = text
        part.inline_data = None

        candidate = mocker.Mock()
        candidate.content = mocker.Mock(parts=[part])
        candidate.finish_reason = finish_reason

        response = mocker.Mock()
        response.candidates = [candidate]
        response.usage_metadata = mocker.Mock(
            prompt_token_count=input_tokens,
            candidates_token_count=output_tokens,
        )
        return response

    return _make_response


# =============================================================================
# Test Markers Configuration
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "live: mark test as requiring live API access")
    config.addinivalue_line("markers", "vcr: mark test as using VCR cassettes")
    config.addinivalue_line("markers", "slow: mark test as slow running")
