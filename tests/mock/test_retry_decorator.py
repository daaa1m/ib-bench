"""
Mock tests for retry_on_rate_limit decorator.

Verifies retry logic, exponential backoff, and error handling
without actual waiting.

Run with: uv run pytest tests/mock/test_retry_decorator.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import retry_on_rate_limit


@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Prevent actual sleeping during retry logic."""
    return mocker.patch("time.sleep")


class TestRetryBehavior:
    """Tests for retry logic."""

    def test_returns_on_success(self, mock_sleep):
        """Successful call returns immediately without retry."""

        @retry_on_rate_limit(max_retries=3)
        def successful_func():
            return "success"

        result = successful_func()

        assert result == "success"
        mock_sleep.assert_not_called()

    def test_retries_on_429_error(self, mock_sleep):
        """Retries when error contains '429'."""
        call_count = 0

        @retry_on_rate_limit(max_retries=3, initial_wait=10)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Error 429: Rate limit exceeded")
            return "success"

        result = fails_then_succeeds()

        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    def test_retries_on_rate_limit_text(self, mock_sleep):
        """Retries when error contains 'rate_limit'."""
        call_count = 0

        @retry_on_rate_limit(max_retries=3)
        def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("rate_limit_exceeded error")
            return "success"

        result = rate_limited_func()

        assert result == "success"
        assert call_count == 2

    def test_raises_non_rate_limit_errors(self, mock_sleep):
        """Non-rate-limit errors are raised immediately."""

        @retry_on_rate_limit(max_retries=3)
        def fails_with_other_error():
            raise ValueError("Some other error")

        with pytest.raises(ValueError, match="Some other error"):
            fails_with_other_error()

        mock_sleep.assert_not_called()

    def test_raises_after_max_retries(self, mock_sleep):
        """Raises after exhausting all retries."""

        @retry_on_rate_limit(max_retries=2, initial_wait=10)
        def always_rate_limited():
            raise Exception("429 Too Many Requests")

        with pytest.raises(Exception, match="429"):
            always_rate_limited()

        assert mock_sleep.call_count == 2


class TestExponentialBackoff:
    """Tests for exponential backoff timing."""

    def test_doubles_wait_time(self, mock_sleep):
        """Wait time doubles after each retry."""
        call_count = 0

        @retry_on_rate_limit(max_retries=3, initial_wait=10)
        def fails_multiple_times():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("429 rate limit")
            return "success"

        fails_multiple_times()

        # Wait times: 10, 20, 40
        assert mock_sleep.call_args_list[0][0][0] == 10
        assert mock_sleep.call_args_list[1][0][0] == 20
        assert mock_sleep.call_args_list[2][0][0] == 40

    def test_respects_initial_wait(self, mock_sleep):
        """Initial wait time is configurable."""
        call_count = 0

        @retry_on_rate_limit(max_retries=1, initial_wait=30)
        def rate_limited_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429")
            return "success"

        rate_limited_once()

        mock_sleep.assert_called_once_with(30)


class TestFunctionPreservation:
    """Tests that decorated function metadata is preserved."""

    def test_preserves_function_name(self):
        """Decorated function keeps original name."""

        @retry_on_rate_limit()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"

    def test_preserves_docstring(self):
        """Decorated function keeps original docstring."""

        @retry_on_rate_limit()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__doc__ == "My docstring."

    def test_preserves_arguments(self, mock_sleep):
        """Arguments and kwargs are passed through."""

        @retry_on_rate_limit()
        def func_with_args(a, b, c=None):
            return (a, b, c)

        result = func_with_args(1, 2, c=3)

        assert result == (1, 2, 3)
