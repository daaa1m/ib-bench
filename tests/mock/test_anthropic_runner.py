"""
Mock tests for AnthropicRunner.

Verifies response parsing, error handling, and file management
without making real API calls.

Run with: uv run pytest tests/mock/test_anthropic_runner.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import Task
from runners import AnthropicRunner, LLMResponse


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
    """Task with input file for file upload tests."""
    input_file = tmp_path / "input.xlsx"
    input_file.write_bytes(b"fake excel")

    return Task(
        id="test-002",
        task_dir=tmp_path,
        task_type="fix-error",
        category="financial-analysis",
        description="Test task with file",
        prompt="Analyze spreadsheet.",
        rubric={"criteria": {}, "total_points": 100},
        input_files=[input_file],
    )


@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Prevent actual sleeping during retry logic."""
    return mocker.patch("time.sleep")


class TestTextOnlyRequests:
    """Tests for text-only API calls (no file uploads)."""

    def test_parses_json_response(self, mocker, sample_task):
        """Successful response with JSON is parsed correctly."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.messages.create.return_value = mocker.Mock(
            content=[mocker.Mock(text='{"error": "Row 140"}')],
            usage=mocker.Mock(input_tokens=100, output_tokens=50),
            stop_reason="end_turn",
        )

        runner = AnthropicRunner(api_key="test-key", model="claude-test")
        result = runner.run(sample_task, input_files=[])

        assert result.parsed_json == {"error": "Row 140"}
        assert result.input_tokens == 100
        assert result.stop_reason == "end_turn"

    def test_handles_non_json_response(self, mocker, sample_task):
        """Response without JSON sets parsed_json to None."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.messages.create.return_value = mocker.Mock(
            content=[mocker.Mock(text="Plain text response")],
            usage=mocker.Mock(input_tokens=50, output_tokens=25),
            stop_reason="end_turn",
        )

        runner = AnthropicRunner(api_key="test-key", model="claude-test")
        result = runner.run(sample_task, input_files=[])

        assert result.raw_text == "Plain text response"
        assert result.parsed_json is None

    def test_content_filter_returns_blocked(self, mocker, sample_task):
        """Content policy exception returns content_filter stop reason."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.messages.create.side_effect = Exception(
            "Content blocked due to policy"
        )

        runner = AnthropicRunner(api_key="test-key", model="claude-test")
        result = runner.run(sample_task, input_files=[])

        assert result.stop_reason == "content_filter"
        assert result.raw_text == ""


class TestFileUploadRequests:
    """Tests for file upload with code execution (beta API)."""

    def test_uploads_and_cleans_up_files(self, mocker, sample_task_with_file):
        """Files are uploaded before request and deleted after."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value

        mock_file = mocker.Mock(id="file-123")
        mock_client.beta.files.upload.return_value = mock_file
        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[mocker.Mock(text='{"result": "ok"}', type="text")],
            usage=mocker.Mock(input_tokens=200, output_tokens=100),
            stop_reason="end_turn",
        )

        runner = AnthropicRunner(api_key="test-key", model="claude-test")
        result = runner.run(
            sample_task_with_file,
            input_files=sample_task_with_file.input_files,
        )

        mock_client.beta.files.upload.assert_called_once()
        mock_client.beta.files.delete.assert_called_once_with("file-123")
        assert result.parsed_json == {"result": "ok"}

    def test_extracts_stdout_from_code_execution(self, mocker, sample_task_with_file):
        """JSON in code execution stdout is extracted."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value

        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-456")

        # Text block - must have text attribute as string
        text_block = mocker.Mock(type="text", spec=["type", "text"])
        text_block.text = "Running..."

        # Code execution result with stdout
        code_block = mocker.Mock(
            type="code_execution_result", spec=["type", "container_id", "content"]
        )
        code_block.container_id = None
        code_block.content = [mocker.Mock(stdout='{"computed": 42}', text=None)]

        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[text_block, code_block],
            usage=mocker.Mock(input_tokens=300, output_tokens=150),
            stop_reason="end_turn",
        )

        runner = AnthropicRunner(api_key="test-key", model="claude-test")
        result = runner.run(
            sample_task_with_file,
            input_files=sample_task_with_file.input_files,
        )

        assert result.parsed_json == {"computed": 42}

    def test_cleans_up_files_on_content_filter(self, mocker, sample_task_with_file):
        """Uploaded files are deleted even on content filter."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value

        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-blocked")
        mock_client.beta.messages.create.side_effect = Exception(
            "Content blocked due to policy"
        )

        runner = AnthropicRunner(api_key="test-key", model="claude-test")
        result = runner.run(
            sample_task_with_file,
            input_files=sample_task_with_file.input_files,
        )

        assert result.stop_reason == "content_filter"
        mock_client.beta.files.delete.assert_called_once_with("file-blocked")


class TestInitialization:
    """Tests for runner initialization and configuration."""

    def test_requires_model(self):
        """Model parameter is required."""
        with pytest.raises(ValueError, match="model is required"):
            AnthropicRunner(api_key="test-key", model=None)

    def test_requires_api_key(self, mocker):
        """API key is required from param or environment."""
        mocker.patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            AnthropicRunner(api_key=None, model="claude-test")

    def test_lazy_client_creation(self, mocker):
        """Client is not created until first access."""
        mock_anthropic = mocker.patch("anthropic.Anthropic")

        runner = AnthropicRunner(api_key="test-key", model="claude-test")
        mock_anthropic.assert_not_called()

        _ = runner.client
        mock_anthropic.assert_called_once()
