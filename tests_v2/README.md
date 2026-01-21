# tests_v2

Independent test suite for the IB-bench evaluation pipeline.

## Structure

- `tests_v2/unit/` - Fast, isolated tests with mocked dependencies
- `tests_v2/integration/` - Component boundary tests (mocked external APIs)
- `tests_v2/e2e/` - End-to-end smoke tests (mocked APIs, minimal data)
- `tests_v2/fixtures/` - Shared test data
- `tests_v2/conftest.py` - Shared pytest fixtures and marker config

## Running

```bash
uv run pytest tests_v2/
```

Run integration tests:

```bash
uv run pytest tests_v2/ --integration
```

Run slow tests (includes e2e):

```bash
uv run pytest tests_v2/ --runslow
```

## Notes

- All external API calls are mocked.
- Tests are written to validate behavior, not implementation details.
- Use `--integration` and `--runslow` to include broader coverage.
