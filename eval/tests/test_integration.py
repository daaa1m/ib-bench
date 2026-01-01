# Integration tests for IB-bench evaluation pipeline
# These tests make actual API calls and require valid API keys
#
# Run with: uv run pytest eval/tests/test_integration.py -v
#
# Note: These tests are slow and may incur API costs.
# They are kept separate from unit tests for faster CI.

import pytest


# Placeholder for future integration tests
# Examples of what could go here:
# - Test actual model responses with AnthropicRunner, OpenAIRunner, GeminiRunner
# - Test LLMJudge.score() with real Claude API calls
# - End-to-end tests running a task through run.py and score.py
