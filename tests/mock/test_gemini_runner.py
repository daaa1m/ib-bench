"""
Mock tests for GeminiRunner.

Verifies response parsing, file handling, and error management
without making real API calls.

Run with: uv run pytest tests/mock/test_gemini_runner.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import Task
from runners import GeminiRunner


@pytest.fixture
def sample_task(tmp_path) -> Task:
    """Minimal task for testing."""
    return Task(
        id="test-001",
        task_dir=tmp_path,
        task_type="fix-error",
        category="financial-analysis",
        description="Test task",
        prompt="Find the error.",
        rubric={"criteria": {}, "total_points": 100},
        input_files=[],
    )


@pytest.fixture
def sample_task_with_file(tmp_path) -> Task:
    """Task with input file for code execution tests."""
    input_file = tmp_path / "input.xlsx"
    input_file.write_bytes(b"fake excel")

    return Task(
        id="test-002",
        task_dir=tmp_path,
        task_type="fix-error",
        category="financial-analysis",
        description="Test with file",
        prompt="Analyze spreadsheet.",
        rubric={"criteria": {}, "total_points": 100},
        input_files=[input_file],
    )


@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Prevent actual sleeping during retry logic."""
    return mocker.patch("time.sleep")


def make_gemini_response(
    mocker,
    text: str,
    input_tokens: int = 100,
    output_tokens: int = 50,
    finish_reason: str = "STOP",
):
    """Helper to create mock Gemini response structure."""
    part = mocker.Mock(spec=["text", "inline_data"])
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


class TestTextOnlyRequests:
    """Tests for text-only API calls."""

    def test_parses_json_response(self, mocker, sample_task):
        """Successful response with JSON is parsed correctly."""
        mock_client = mocker.patch("google.genai.Client").return_value

        mock_client.models.generate_content.return_value = make_gemini_response(
            mocker, '{"error": "Row 140"}'
        )

        runner = GeminiRunner(api_key="test-key", model="gemini-test")
        result = runner.run(sample_task, input_files=[])

        assert result.parsed_json == {"error": "Row 140"}
        assert result.input_tokens == 100
        assert result.stop_reason == "stop"

    def test_handles_non_json_response(self, mocker, sample_task):
        """Response without JSON sets parsed_json to None."""
        mock_client = mocker.patch("google.genai.Client").return_value

        mock_client.models.generate_content.return_value = make_gemini_response(
            mocker, "Plain text response"
        )

        runner = GeminiRunner(api_key="test-key", model="gemini-test")
        result = runner.run(sample_task, input_files=[])

        assert result.raw_text == "Plain text response"
        assert result.parsed_json is None

    def test_safety_finish_reason_returns_blocked(self, mocker, sample_task):
        """SAFETY finish_reason returns content_filter stop reason."""
        mock_client = mocker.patch("google.genai.Client").return_value

        mock_client.models.generate_content.return_value = make_gemini_response(
            mocker, "", finish_reason="SAFETY"
        )

        runner = GeminiRunner(api_key="test-key", model="gemini-test")
        result = runner.run(sample_task, input_files=[])

        assert result.stop_reason == "content_filter"
        assert result.raw_text == ""

    def test_content_filter_exception(self, mocker, sample_task):
        """Safety exception returns content_filter stop reason."""
        mock_client = mocker.patch("google.genai.Client").return_value

        mock_client.models.generate_content.side_effect = Exception(
            "Content blocked by safety filters"
        )

        runner = GeminiRunner(api_key="test-key", model="gemini-test")
        result = runner.run(sample_task, input_files=[])

        assert result.stop_reason == "content_filter"
        assert result.raw_text == ""


class TestFileUploadRequests:
    """Tests for file upload with code execution."""

    def test_uploads_and_cleans_up_files(self, mocker, sample_task_with_file):
        """Files are uploaded before request and deleted after."""
        mock_client = mocker.patch("google.genai.Client").return_value

        mock_file = mocker.Mock(name="uploaded-file-123")
        mock_client.files.upload.return_value = mock_file

        mock_client.models.generate_content.return_value = make_gemini_response(
            mocker, '{"result": "ok"}'
        )

        runner = GeminiRunner(api_key="test-key", model="gemini-test")
        result = runner.run(
            sample_task_with_file,
            input_files=sample_task_with_file.input_files,
        )

        mock_client.files.upload.assert_called_once()
        mock_client.files.delete.assert_called_once()
        assert result.parsed_json == {"result": "ok"}

    def test_cleans_up_on_error(self, mocker, sample_task_with_file):
        """Files are cleaned up even when API call fails."""
        mock_client = mocker.patch("google.genai.Client").return_value

        mock_file = mocker.Mock(name="file-cleanup")
        mock_client.files.upload.return_value = mock_file

        mock_client.models.generate_content.side_effect = Exception(
            "Content blocked by safety"
        )

        runner = GeminiRunner(api_key="test-key", model="gemini-test")
        result = runner.run(
            sample_task_with_file,
            input_files=sample_task_with_file.input_files,
        )

        assert result.stop_reason == "content_filter"
        mock_client.files.delete.assert_called_once()


class TestInitialization:
    """Tests for runner initialization."""

    def test_requires_model(self):
        """Model parameter is required."""
        with pytest.raises(ValueError, match="model is required"):
            GeminiRunner(api_key="test-key", model=None)

    def test_requires_api_key(self, mocker):
        """API key is required from param or environment."""
        mocker.patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "",
                "GOOGLE_API_KEY": "",
            },
            clear=False,
        )

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            GeminiRunner(api_key=None, model="gemini-test")

    def test_lazy_client_creation(self, mocker):
        """Client is not created until first access."""
        mock_genai = mocker.patch("google.genai.Client")

        runner = GeminiRunner(api_key="test-key", model="gemini-test")
        mock_genai.assert_not_called()

        _ = runner.client
        mock_genai.assert_called_once()
