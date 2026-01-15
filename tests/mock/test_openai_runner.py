"""
Mock tests for OpenAIRunner.

Verifies response parsing, file handling, and error management
without making real API calls.

Run with: uv run pytest tests/mock/test_openai_runner.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import Task
from runners import OpenAIRunner


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
def sample_task_with_excel(tmp_path) -> Task:
    """Task with Excel file for code_interpreter tests."""
    input_file = tmp_path / "input.xlsx"
    input_file.write_bytes(b"fake excel")

    return Task(
        id="test-002",
        task_dir=tmp_path,
        task_type="fix-error",
        category="financial-analysis",
        description="Test with Excel",
        prompt="Analyze spreadsheet.",
        rubric={"criteria": {}, "total_points": 100},
        input_files=[input_file],
    )


@pytest.fixture
def sample_task_with_pdf(tmp_path) -> Task:
    """Task with PDF file for file_search tests."""
    input_file = tmp_path / "input.pdf"
    input_file.write_bytes(b"fake pdf")

    return Task(
        id="test-003",
        task_dir=tmp_path,
        task_type="summarise",
        category="document-review",
        description="Test with PDF",
        prompt="Summarize document.",
        rubric={"criteria": {}, "total_points": 100},
        input_files=[input_file],
    )


@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Prevent actual sleeping during retry logic."""
    return mocker.patch("time.sleep")


class TestTextOnlyRequests:
    """Tests for text-only API calls."""

    def test_parses_json_response(self, mocker, sample_task):
        """Successful response with JSON is parsed correctly."""
        mock_client = mocker.patch("openai.OpenAI").return_value
        mock_client.responses.create.return_value = mocker.Mock(
            output_text='{"error": "Row 140"}',
            usage=mocker.Mock(input_tokens=100, output_tokens=50),
            stop_reason="stop",
            output=[],
        )

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        result = runner.run(sample_task, input_files=[])

        assert result.parsed_json == {"error": "Row 140"}
        assert result.input_tokens == 100
        assert result.stop_reason == "stop"

    def test_handles_non_json_response(self, mocker, sample_task):
        """Response without JSON sets parsed_json to None."""
        mock_client = mocker.patch("openai.OpenAI").return_value
        mock_client.responses.create.return_value = mocker.Mock(
            output_text="Plain text response",
            usage=mocker.Mock(input_tokens=50, output_tokens=25),
            stop_reason="stop",
            output=[],
        )

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        result = runner.run(sample_task, input_files=[])

        assert result.raw_text == "Plain text response"
        assert result.parsed_json is None

    def test_content_filter_returns_blocked(self, mocker, sample_task):
        """Content policy exception returns content_filter stop reason."""
        mock_client = mocker.patch("openai.OpenAI").return_value
        mock_client.responses.create.side_effect = Exception(
            "invalid_prompt: flagged by content filter"
        )

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        result = runner.run(sample_task, input_files=[])

        assert result.stop_reason == "content_filter"
        assert result.raw_text == ""

    def test_max_tokens_normalized(self, mocker, sample_task):
        """OpenAI 'length' stop reason is normalized to 'max_tokens'."""
        mock_client = mocker.patch("openai.OpenAI").return_value
        mock_client.responses.create.return_value = mocker.Mock(
            output_text='{"partial": "...',
            usage=mocker.Mock(input_tokens=100, output_tokens=16384),
            stop_reason="length",
            output=[],
        )

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        result = runner.run(sample_task, input_files=[])

        assert result.stop_reason == "max_tokens"


class TestFileUploadRequests:
    """Tests for file upload with code_interpreter and file_search."""

    def test_excel_uses_code_interpreter(self, mocker, sample_task_with_excel):
        """Excel files trigger code_interpreter tool."""
        mock_client = mocker.patch("openai.OpenAI").return_value

        # Mock file upload
        mock_client.files.create.return_value = mocker.Mock(id="file-excel-123")

        mock_client.responses.create.return_value = mocker.Mock(
            output_text='{"result": "analyzed"}',
            usage=mocker.Mock(input_tokens=200, output_tokens=100),
            stop_reason="stop",
            output=[],
        )

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        result = runner.run(
            sample_task_with_excel,
            input_files=sample_task_with_excel.input_files,
        )

        # Verify file was uploaded
        mock_client.files.create.assert_called_once()

        # Verify responses.create was called with tools
        call_kwargs = mock_client.responses.create.call_args.kwargs
        assert call_kwargs.get("tools") is not None

        # Verify cleanup
        mock_client.files.delete.assert_called_with("file-excel-123")

        assert result.parsed_json == {"result": "analyzed"}

    def test_pdf_uses_file_search(self, mocker, sample_task_with_pdf):
        """PDF files trigger file_search with vector store."""
        mock_client = mocker.patch("openai.OpenAI").return_value

        # Mock file upload
        mock_client.files.create.return_value = mocker.Mock(id="file-pdf-456")

        # Mock vector store creation and status
        mock_client.vector_stores.create.return_value = mocker.Mock(id="vs-789")
        mock_client.vector_stores.retrieve.return_value = mocker.Mock(
            file_counts=mocker.Mock(completed=1, failed=0)
        )

        mock_client.responses.create.return_value = mocker.Mock(
            output_text='{"summary": "Document content"}',
            usage=mocker.Mock(input_tokens=500, output_tokens=200),
            stop_reason="stop",
            output=[],
        )

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        result = runner.run(
            sample_task_with_pdf,
            input_files=sample_task_with_pdf.input_files,
        )

        # Verify vector store was created
        mock_client.vector_stores.create.assert_called_once()

        # Verify cleanup
        mock_client.vector_stores.delete.assert_called_with("vs-789")
        mock_client.files.delete.assert_called_with("file-pdf-456")

        assert result.parsed_json == {"summary": "Document content"}

    def test_cleans_up_on_error(self, mocker, sample_task_with_excel):
        """Files are cleaned up even when API call fails."""
        mock_client = mocker.patch("openai.OpenAI").return_value

        mock_client.files.create.return_value = mocker.Mock(id="file-cleanup")
        mock_client.responses.create.side_effect = Exception(
            "invalid_prompt: content flagged"
        )

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        result = runner.run(
            sample_task_with_excel,
            input_files=sample_task_with_excel.input_files,
        )

        # Should return content_filter, not raise
        assert result.stop_reason == "content_filter"

        # File should still be cleaned up
        mock_client.files.delete.assert_called_with("file-cleanup")


class TestInitialization:
    """Tests for runner initialization."""

    def test_requires_model(self):
        """Model parameter is required."""
        with pytest.raises(ValueError, match="model is required"):
            OpenAIRunner(api_key="test-key", model=None)

    def test_requires_api_key(self, mocker):
        """API key is required from param or environment."""
        mocker.patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False)

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAIRunner(api_key=None, model="gpt-test")

    def test_lazy_client_creation(self, mocker):
        """Client is not created until first access."""
        mock_openai = mocker.patch("openai.OpenAI")

        runner = OpenAIRunner(api_key="test-key", model="gpt-test")
        mock_openai.assert_not_called()

        _ = runner.client
        mock_openai.assert_called_once()
