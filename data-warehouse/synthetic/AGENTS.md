# Repository Guidelines

## Project Structure & Module Organization
- Top-level: `eval/` (evaluation runner/tests), `data-warehouse/` (datasets), `reference-files/` (docs), `pyproject.toml` + `uv.lock` (dependencies).
- Within `data-warehouse/`: `synthetic/` holds generated spreadsheets, `human-generated/` stores source PDFs/XLSX, `financial-modelling/` contains modeling plans/notes.
- Tests live in `eval/test_eval.py`; task configs/assets live in `eval/tasks/`; cached outputs under `eval/results/`.
- Keep large binary inputs in `data-warehouse/`; avoid checking binaries into `eval/` code paths.

## Build, Test, and Development Commands
- `uv run pytest eval/test_eval.py -v` — run the full test suite.
- `uv run pytest eval/test_eval.py -v -k "<pattern>"` — target a subset while iterating.
- `uv run python eval/run.py --tasks e-001 --model claude-sonnet-4-20250514` — execute benchmark tasks; results cached in `eval/results/`.
- `uv run python eval/score.py RUN_ID` — score a completed run; add `--rescore` to recompute.
- Wrap Python invocations with `uv run`; add `-s` to surface print debugging.

## Coding Style & Naming Conventions
- Python 3.10+ type hints (`list[str]`, `dict[str, Any]`, `str | None`); prefer `@dataclass` for data containers.
- Imports grouped standard library / third-party / local, each alphabetized and separated by a blank line.
- 4-space indentation, ~100-character soft line limit, double quotes for strings, trailing commas in multiline literals, no trailing whitespace.
- Functions/variables use `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE_CASE`; task IDs follow `e-001`, `m-001`, `h-001`.
- Use `pathlib.Path` for filesystem work; avoid `os.path` unless necessary.

## Testing Guidelines
- Add or update tests in `eval/test_eval.py` near the behavior being changed; favor pytest fixtures and classes for shared setup.
- Use descriptive test names; include task IDs or rubric names when relevant.
- Run `uv run pytest ...` locally before submitting; keep coverage for new parsing/scoring branches in sync with the rubric.

## Commit & Pull Request Guidelines
- Write concise, imperative commit subjects (e.g., "Add substring scorer helper"); add body context for non-trivial changes.
- PRs should summarize the change, list validation commands run, call out affected tasks/models, and attach screenshots or logs when outputs change.
- Link related issues or TODOs; note follow-ups and data dependencies; avoid committing large binaries unless essential and documented.

## Security & Configuration Tips
- Keep API keys (Anthropic/OpenAI/Gemini) in `.env`; loaded via `python-dotenv`; never commit secrets.
- Treat `eval/results/` outputs and `data-warehouse/` sources as sensitive; scrub or regenerate before sharing externally.
- Document provenance when adding files to `human-generated/` or `synthetic/`; ensure redistribution rights and size appropriateness for the repo.
