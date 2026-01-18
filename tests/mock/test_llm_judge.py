"""
Mock tests for LLMJudge.

Verifies scoring logic, JSON parsing, prose fallback, and file handling
without making real API calls.

Run with: uv run pytest tests/mock/test_llm_judge.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval" / "llm-judge"))

from llm_judge import LLMJudge


@pytest.fixture
def sample_rubric() -> dict:
    """Sample rubric with LLM judge criteria."""
    return {
        "criteria": {
            "accuracy": {
                "description": "Response accuracy",
                "points": 60,
            },
            "clarity": {
                "description": "Explanation clarity",
                "points": 40,
            },
        }
    }


@pytest.fixture
def sample_source_files(tmp_path) -> list[Path]:
    """Sample source files for judging."""
    pdf_file = tmp_path / "source.pdf"
    pdf_file.write_bytes(b"fake pdf content")
    return [pdf_file]


@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Prevent actual sleeping during retry logic."""
    return mocker.patch("time.sleep")


@pytest.fixture(autouse=True)
def mock_api_key(mocker):
    """Ensure tests don't require real API key."""
    mocker.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False)


class TestScoring:
    """Tests for LLMJudge.score() method."""

    def test_parses_json_scores(self, mocker, sample_rubric, sample_source_files):
        """Valid JSON scores are parsed correctly."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value

        # Mock file upload
        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-judge")

        # Mock response with JSON scores
        json_response = """
        {
            "scores": {
                "accuracy": {"score": 0.85, "reasoning": "Good accuracy"},
                "clarity": {"score": 0.90, "reasoning": "Very clear"}
            }
        }
        """
        text_block = mocker.Mock(type="text", spec=["type", "text"])
        text_block.text = json_response

        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[text_block],
        )

        judge = LLMJudge(model="claude-test")
        result = judge.score(
            sample_rubric, sample_source_files, '{"answer": "test"}', "Test task prompt"
        )

        assert "scores" in result
        assert result["scores"]["accuracy"]["score"] == 0.85
        assert result["scores"]["clarity"]["score"] == 0.90
        assert "weighted_total" in result

    def test_calculates_weighted_total(
        self, mocker, sample_rubric, sample_source_files
    ):
        """Weighted total is calculated from criterion points."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-wt")

        json_response = """
        {
            "scores": {
                "accuracy": {"score": 1.0, "reasoning": "Perfect"},
                "clarity": {"score": 0.5, "reasoning": "Okay"}
            }
        }
        """
        text_block = mocker.Mock(type="text", spec=["type", "text"])
        text_block.text = json_response

        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[text_block],
        )

        judge = LLMJudge(model="claude-test")
        result = judge.score(
            sample_rubric, sample_source_files, '{"answer": "test"}', "Test task prompt"
        )

        # accuracy: 1.0 * 60 = 60, clarity: 0.5 * 40 = 20
        # weighted = (60 + 20) / (60 + 40) = 0.8
        assert abs(result["weighted_total"] - 0.8) < 0.01

    def test_extracts_json_from_code_execution(
        self, mocker, sample_rubric, sample_source_files
    ):
        """JSON in code execution stdout is extracted."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-code")

        # Code execution result with stdout containing JSON
        code_block = mocker.Mock(type="code_execution_result", spec=["type", "content"])
        code_block.content = [
            mocker.Mock(
                stdout='{"scores": {"accuracy": {"score": 0.7, "reasoning": "ok"}}}',
                text=None,
            )
        ]

        # Text block without JSON
        text_block = mocker.Mock(type="text", spec=["type", "text"])
        text_block.text = "Running evaluation..."

        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[text_block, code_block],
        )

        judge = LLMJudge(model="claude-test")
        result = judge.score(
            {"criteria": {"accuracy": {"description": "Test accuracy", "points": 100}}},
            sample_source_files,
            '{"answer": "test"}',
            "Test task prompt",
        )

        assert result["scores"]["accuracy"]["score"] == 0.7

    def test_cleans_up_files(self, mocker, sample_rubric, sample_source_files):
        """Uploaded files are deleted after scoring."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-cleanup")

        text_block = mocker.Mock(type="text", spec=["type", "text"])
        text_block.text = '{"scores": {"accuracy": {"score": 0.5, "reasoning": "ok"}}}'

        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[text_block],
        )

        judge = LLMJudge(model="claude-test")
        judge.score(
            {"criteria": {"accuracy": {"description": "Test accuracy", "points": 100}}},
            sample_source_files,
            '{"answer": "test"}',
            "Test task prompt",
        )

        mock_client.beta.files.delete.assert_called_once_with("file-cleanup")


class TestProseFallback:
    """Tests for prose score parsing fallback."""

    def test_parses_prose_format(self, mocker, sample_rubric, sample_source_files):
        """Falls back to prose parsing when JSON fails."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-prose")

        # Response in prose format instead of JSON
        prose_response = """
        Here are my scores:
        
        **accuracy: 0.85/1.0** - Good job on accuracy
        **clarity: 0.70/1.0** - Could be clearer
        """
        text_block = mocker.Mock(type="text", spec=["type", "text"])
        text_block.text = prose_response

        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[text_block],
        )

        judge = LLMJudge(model="claude-test")
        result = judge.score(
            sample_rubric, sample_source_files, '{"answer": "test"}', "Test task prompt"
        )

        assert result["scores"]["accuracy"]["score"] == 0.85
        assert result["scores"]["clarity"]["score"] == 0.70

    def test_handles_missing_scores(self, mocker, sample_rubric, sample_source_files):
        """Returns empty scores when parsing completely fails."""
        mock_client = mocker.patch("anthropic.Anthropic").return_value
        mock_client.beta.files.upload.return_value = mocker.Mock(id="file-empty")

        # Response with no parseable scores
        text_block = mocker.Mock(type="text", spec=["type", "text"])
        text_block.text = "I cannot evaluate this response."

        mock_client.beta.messages.create.return_value = mocker.Mock(
            content=[text_block],
        )

        judge = LLMJudge(model="claude-test")
        result = judge.score(
            sample_rubric, sample_source_files, '{"answer": "test"}', "Test task prompt"
        )

        assert result["scores"] == {}
        assert result["weighted_total"] == 0.0


class TestInitialization:
    """Tests for LLMJudge initialization."""

    def test_requires_api_key(self, mocker):
        """API key is required from environment."""
        mocker.patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            LLMJudge(model="claude-test")

    def test_accepts_custom_runner(self, mocker, mock_api_key):
        from judge_runners import AnthropicJudge

        custom_runner = AnthropicJudge(model="custom-model")
        judge = LLMJudge(runner=custom_runner)
        assert judge.runner is custom_runner
