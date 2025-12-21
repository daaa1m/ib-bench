# CODEX.md

## Project Summary
IB-bench is an LLM benchmark for investment banking analyst tasks (Excel modeling, document analysis, data extraction). The evaluation pipeline separates **generation** (expensive model calls) from **scoring** (cheap rubric iteration).

## Key Directories
- `data-factory/`: synthetic and human-generated data inputs
  - `financial-modelling/`, `human-generated/`, `synthetic/`
- `eval/`: evaluation pipeline
  - `run.py`: generation
  - `score.py`: scoring
  - `helpers.py`: model runners and file handling
  - `tasks/`: task definitions (`e-001/`, `m-001/`, `h-001/`)
  - `results/`: outputs (responses and scores)
- `reference-files/`: project docs (`IB-bench.md`, `architecture-design-draft.md`, `TODO.md`)

## Task Anatomy
Each task folder under `eval/tasks/` typically contains:
- `prompt.md` (required)
- `input*.<ext>` (optional inputs; `input.pdf`, `input.xlsx`, etc.)
- `rubric.json` (required for scoring)
- `meta.yaml` (optional metadata and scoring config)

Task IDs are `{difficulty}-{number}` where difficulty is `e`, `m`, or `h`.

## Running Commands
Always run Python via `uv run`.

```bash
# Run all tasks
uv run python eval/run.py

# Run specific tasks
uv run python eval/run.py --tasks e-001 e-002

# Filter by difficulty
uv run python eval/run.py --filter e-

# Score a run
uv run python eval/score.py RUN_ID
uv run python eval/score.py RUN_ID --tasks e-001
uv run python eval/score.py RUN_ID --rescore
```

## File Handling Notes
- `.pdf`, `.png`, `.jpg`: sent natively to the model
- `.csv`, `.txt`: sent as text
- `.xlsx`: not natively supported by major APIs; use converter

### Excel Converter
```bash
uv run python eval/xlsx_converter.py path/to/file.xlsx
uv run python eval/xlsx_converter.py path/to/file.xlsx --output output.json
```

## Evaluation Types
- `programmatic`: deterministic checks
- `llm_judge`: qualitative assessment
- `hybrid`: weighted combination

## Operational Principles
- Generation is slow/expensive; run once and cache responses.
- Scoring is cheap; iterate on rubrics without rerunning generation.

## Known Gaps / TODOs
- `status.py` is referenced in docs but not present.
- Consider rubric versioning in score outputs.
- Consider parallel task execution with rate limiting.

## Reference Docs
- `reference-files/IB-bench.md`
- `reference-files/architecture-design-draft.md`
- `reference-files/TODO.md`
- `CLAUDE.md`
- `README.md`
