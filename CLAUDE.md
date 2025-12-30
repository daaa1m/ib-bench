# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project Overview

IB-bench is an LLM benchmark for testing investment banking analyst tasks (Excel
modeling, document analysis, data extraction). Inspired by SWE-bench but focused
on IB-specific work.

## Environment Setup

Create `.env` with API keys:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

## Commands

All Python scripts must be run with `uv run`:

```bash
# Run with config file (recommended)
uv run python eval/run.py --config configs/quick-test.yaml
uv run python eval/run.py --config configs/full-easy.yaml

# Override config with CLI args
uv run python eval/run.py --config configs/quick-test.yaml --model gpt-4o
uv run python eval/run.py --config configs/quick-test.yaml --parallel 5

# Run without config (all CLI args)
uv run python eval/run.py --tasks e-001 --model claude-sonnet-4-20250514
uv run python eval/run.py --tasks e-001 e-002 --model claude-sonnet-4-20250514
uv run python eval/run.py --filter e- --model claude-sonnet-4-20250514

# Use different providers
uv run python eval/run.py --tasks e-001 --provider openai --model gpt-4o
uv run python eval/run.py --tasks e-001 --provider gemini --model gemini-2.5-flash

# Run tasks in parallel (5 concurrent)
uv run python eval/run.py --filter e- --model gemini-2.5-flash --parallel 5

# Score responses from a run
uv run python eval/score.py RUN_ID
uv run python eval/score.py RUN_ID --tasks e-001
uv run python eval/score.py RUN_ID --rescore

# Generate leaderboard
uv run python eval/leaderboard.py                      # CLI table
uv run python eval/leaderboard.py --export results/    # Export JSON
uv run python eval/leaderboard.py --weights 25,35,40   # Custom weights

# Run tests
uv run pytest eval/test_eval.py -v
```

### Config Files

Config files live in `eval/configs/` and use YAML format:

```yaml
# eval/configs/quick-test.yaml
provider: anthropic
model: claude-sonnet-4-20250514
tasks:
  - e-001
  - e-002
parallel: 1
```

Available config options:
- `provider`: anthropic, openai, or gemini
- `model`: Model identifier
- `tasks`: List of task IDs
- `filter`: Task ID prefix (e.g., "e-" for all easy tasks)
- `parallel`: Number of concurrent tasks

## Architecture

### Core Principle: Separate Expensive from Cheap

- **Generation (`eval/run.py`)**: Slow, expensive LLM calls. Run once, cache
  responses.
- **Scoring (`eval/score.py`)**: Fast, cheap. Iterate on rubrics freely without
  re-running generation.

### Directory Structure

- `eval/tasks/` - Task definitions (one folder per task: `e-001/`, `m-001/`,
  `h-001/`)
- `eval/results/` - Run outputs organized by timestamp and model
- `data-factory/` - Source data (human-generated and synthetic) for creating
  tasks

### Task Anatomy

Each task folder contains:

- `prompt.md` (required) - Instructions for the model
- `input.*` - Input files, multiple allowed (auto-detected by `input*.<ext>`
  pattern, e.g., `input.xlsx`, `input_appendix.pdf`)
- `rubric.json` - Evaluation criteria (see Rubric Format below)
- `meta.yaml` - Metadata (see Meta Format below)

Task IDs follow naming: `{difficulty}-{number}` where difficulty is `e` (easy),
`m` (medium), or `h` (hard).

### Meta Format

```yaml
# Documentation
task:
  id: e-001
  type: fix-error # fix-error, summarise, extraction, creating
  category: excel # excel, pdf, web
  description:
    "Brief explanation of what the task requires. The error or problem (if
    applicable). Expected answer with specific values. What capability this
    tests."

prompt:
  notes: "Special instructions or context given to the LLM"

input:
  input-file-original: "$human/source.xlsx" # Path, list of paths, or None
  notes: "Modifications made or notable aspects of input"
```

**Path alias:** `$human` expands to `data-factory/human-generated/`

**Multiple inputs:** `input-file-original` can be a list:
```yaml
input:
  input-file-original:
    - "$human/report.pdf"
    - "$human/model.xlsx"
```

### Rubric Format

Rubrics are self-describing - evaluation type is derived from criteria types:

```json
{
  "task_id": "e-001",
  "version": "1.0",
  "total_points": 100,
  "criteria": {
    "error_location": {
      "description": "Must identify the error row",
      "type": "programmatic",
      "match_type": "substring_one_of",
      "accepted_values": ["Row 140", "L140"],
      "points": 42,
      "gates_llm": true
    },
    "explanation": {
      "description": "Must explain the fix",
      "type": "llm_judge",
      "core_concepts": ["Maintenance Capex", "excluded"],
      "points": 15
    }
  }
}
```

**Key fields:**

- `type`: `"programmatic"` or `"llm_judge"` (determines evaluation method)
- `match_type`: For programmatic - `"substring_one_of"` or `"regex_pattern"`
- `points`: Score weight for this criterion
- `gates_llm`: If `true` and this criterion fails, LLM criteria are skipped
  (saves cost). Only use when rubric has LLM judge criteria.

**Criterion ID alignment:**
- **Programmatic criteria**: ID must match the JSON output key exactly
- **LLM-judge criteria**: Can be evaluation dimensions (e.g., `summary_synthesis`,
  `summary_drivers`) that assess qualities of an output field like `summary`

### Evaluation Types

Derived automatically from rubric criteria:

- **Programmatic**: All criteria have `type: "programmatic"`
- **LLM Judge**: All criteria have `type: "llm_judge"`
- **Hybrid**: Mix of both types

### Model Runners

`eval/helpers.py` contains three runner classes:

| Runner | Provider | File Handling | Tools |
|--------|----------|---------------|-------|
| `AnthropicRunner` | Anthropic | Files API | Code execution |
| `OpenAIRunner` | OpenAI | Files API + Assistants | file_search, code_interpreter |
| `GeminiRunner` | Google | Files API | Code execution |

All runners support native file upload - no manual conversion needed.

## File Handling

All providers handle files natively via their respective APIs:

| Type | Anthropic | OpenAI | Gemini |
|------|-----------|--------|--------|
| `.pdf` | Files API | file_search | Files API |
| `.xlsx` | Code execution | code_interpreter | Code execution |
| `.png/.jpg` | Native vision | code_interpreter | Files API |

## Results Directory

```
eval/results/
├── responses/          # LLM outputs (expensive, preserve)
│   └── {model}/
│       └── {run_id}/
│           ├── config.json
│           └── {task-id}.json
└── scores/             # Scoring outputs (cheap, regenerable)
    └── {model}/
        └── {run_id}/
            ├── {task-id}.json  # includes rubric_hash, scored_at
            └── summary.json
```

Responses are cached and reused. Scores can be regenerated freely when rubrics
change. Score files include `rubric_hash` for audit trail.

When using `--resume` or scoring, specify path as `MODEL/RUN_ID` (e.g.,
`claude-opus-4-5-20251101/20251230_114140`).

## Leaderboard

The leaderboard aggregates scores across models and calculates a weighted overall
score (max 100).

**Per-task credit:**
- 0 credit: < 50 points
- 0.5 credit (half): 50-99 points
- 1.0 credit (full): 100 points

**Tier score:** `(total credits / tasks completed) × 100`

**Overall score:** `Easy×0.20 + Medium×0.35 + Hard×0.45`

Weights are configurable in `eval/leaderboard_config.yaml` or via `--weights` CLI
flag.

**JSON export** (`--export`) produces `leaderboard.json` suitable for frontend
integration.

## Task Workflow

### Creating Tasks

Use `.claude/skills/create-ib-task.md`:

1. Populate `meta.yaml` with task details and expected answer
2. Run the skill to generate `prompt.md` and `rubric.json`

The skill ensures criterion IDs match JSON output keys and proper point
allocation.

### Reviewing Tasks

Use `.claude/skills/review-ib-task.md` to validate task quality:

- Structural completeness (all required files exist)
- Criterion ID alignment between prompt and rubric
- Rubric quality (points sum, accepted_values variants)
- Prompt quality (all required sections)
- Category-input consistency
- Expected answer traceability
- Overall coherence
