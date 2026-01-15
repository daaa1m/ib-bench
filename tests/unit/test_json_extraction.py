"""
Tests for JSON extraction from LLM responses.

Run with: uv run pytest tests/unit/test_json_extraction.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "eval"))

from helpers import extract_json


class TestExtractJson:
    def test_direct_json(self):
        """Parse raw JSON string."""
        text = '{"key": "value", "number": 42}'
        result = extract_json(text)
        assert result == {"key": "value", "number": 42}

    def test_json_with_whitespace(self):
        """Parse JSON with surrounding whitespace."""
        text = '   \n  {"key": "value"}  \n  '
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_json_in_code_block(self):
        """Extract JSON from markdown code block."""
        text = """
Here is my response:
```json
{"error_location": "A1", "formula": "=SUM(B1:B5)"}
```
That should fix the issue.
"""
        result = extract_json(text)
        assert result is not None
        assert result["error_location"] == "A1"
        assert result["formula"] == "=SUM(B1:B5)"

    def test_json_in_plain_code_block(self):
        """Extract JSON from code block without json tag."""
        text = """
```
{"value": 123}
```
"""
        result = extract_json(text)
        assert result == {"value": 123}

    def test_embedded_json(self):
        """Extract JSON embedded in prose."""
        text = 'The answer is {"result": "found", "cell": "B2"} as shown above.'
        result = extract_json(text)
        assert result is not None
        assert result["result"] == "found"
        assert result["cell"] == "B2"

    def test_no_json_returns_none(self):
        """Return None when no JSON found."""
        text = "This is just plain text with no JSON."
        result = extract_json(text)
        assert result is None

    def test_invalid_json_returns_none(self):
        """Return None for malformed JSON."""
        text = '{"key": "value", "broken"}'
        result = extract_json(text)
        assert result is None

    def test_nested_json(self):
        """Parse JSON with nested objects."""
        text = '{"outer": {"inner": {"deep": 42}}}'
        result = extract_json(text)
        assert result is not None
        assert result["outer"]["inner"]["deep"] == 42
