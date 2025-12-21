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
```

## Commands

All Python scripts must be run with `uv run`:

```bash
# Run specific tasks (--model is required)
uv run python eval/run.py --tasks e-001 --model claude-sonnet-4-20250514
uv run python eval/run.py --tasks e-001 e-002 --model claude-sonnet-4-20250514

# Run tasks by difficulty prefix (e- = easy, m- = medium, h- = hard)
uv run python eval/run.py --filter e- --model claude-sonnet-4-20250514

# Use OpenAI instead of Anthropic
uv run python eval/run.py --tasks e-001 --provider openai --model gpt-4o

# Score responses from a run
uv run python eval/score.py RUN_ID
uv run python eval/score.py RUN_ID --tasks e-001
uv run python eval/score.py RUN_ID --rescore

# Run tests
uv run pytest eval/test_eval.py -v
```

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
task:
  id: e-001
  type: fix-error # fix-error, summarise, extraction
  category: excel # excel, pdf, web
  description: "What the task requires and expected answer"

input:
  input-file-original: "path/to/source.xlsx" # Source file path, or None for web tasks
  input-file-used: "how input was modified" # Or None
  notes: "Additional context" # Or None
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
  (saves cost)

**Criterion ID = Response JSON key**: The rubric criterion ID must match the
output field in the prompt's expected JSON format.

### Evaluation Types

Derived automatically from rubric criteria:

- **Programmatic**: All criteria have `type: "programmatic"`
- **LLM Judge**: All criteria have `type: "llm_judge"`
- **Hybrid**: Mix of both types

### Model Runners

`eval/helpers.py` contains `OpenAIRunner` and `AnthropicRunner` classes for API
calls.

## File Handling

| Type        | Processing                                            |
| ----------- | ----------------------------------------------------- |
| `.pdf`      | Native Claude document support                        |
| `.xlsx`     | Converted to JSON with formulas preserved (see below) |
| `.png/.jpg` | Native image support                                  |
| `.csv/.txt` | Sent as text                                          |

## Results Directory

```
eval/results/
├── responses/          # LLM outputs (expensive, preserve)
│   └── {timestamp}_{model}/
│       ├── config.json
│       └── {task-id}.json
└── scores/             # Scoring outputs (cheap, regenerable)
    └── {timestamp}_{model}/
        ├── {task-id}.json
        └── summary.json
```

Responses are cached and reused. Scores can be regenerated freely when rubrics
change.

## Task Creation

Use the skill at `.claude/skills/create-ib-task.md` to create new tasks:

1. Populate `meta.yaml` with task details and expected answer
2. Run the skill to generate `prompt.md` and `rubric.json`

The skill ensures criterion IDs match JSON output keys and proper point
allocation.
