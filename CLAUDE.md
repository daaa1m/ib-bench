## Project Overview

IB-bench is an LLM benchmark for testing investment banking analyst tasks (Excel
modeling, document analysis, data extraction). Inspired by SWE-bench but focused
on IB-specific work.

## Core Development Rules

- NEVER run a script with an API call, namely eval/run.py or eval/score.py (with
  an LLM judge) without specific instructions from the user

## Package Management

- Always run scripts using: `uv run script.py`
- Always add packages using: `uv add package`
- Upgrading: `uv add --dev package --upgrade-package package`
- Running tools: `uv run tool`
- FORBIDDEN: `uv pip install`, `@latest` syntax

### Testing framework

- Framework `uv run pytest`
- Test after a big change in code and before pushing to origin
- Async testing: use anyio, not asyncio
- Coverage: test edge cases and errors
- New features require tests
- Bug fixes require regression tests

### Notification System

- If you a complete a task, or encounter an error, or need my input use the
  notify via Telegram MCP with
  - type: completed | waiting | error | info
  - task: brief description
  - details: what was done
  - nextSteps: what you need from me (if anything)
- Only send a Telegram notification for when the task takes longer than 3
  minutes - do not send notifications for quick tasks or routine completions
- NEVER push to main `git push origin main` without explicit permission from the
  user

## Architecture

### Core Principle: Separate Expensive from Cheap

- **Generation (`eval/run.py`)**: Slow, expensive LLM calls. Run once, cache
  responses.
- **Scoring (`eval/score.py`)**: Fast, cheap. Iterate on rubrics freely without
  re-running generation.

### Directory Structure

- `eval/tasks/` - Task definitions (one folder per task: `e-001/`, `m-001/`,
  `h-001/`)
- `eval/responses/` - LLM outputs (expensive, preserve)
- `eval/scores/` - Scoring outputs (cheap, regenerable)
- `tests/` - Test suite (unit/, mock/, integration/, live/)
- `data-warehouse/` - Source data (human-generated and synthetic) for creating
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
  title: "Find the balance sheet error in an LBO model"
  type: fix-error # fix-error, summarise, extraction, creating
  category: # IB domain(s) - can have multiple
    - financial-analysis
  input_type: excel # excel, pdf, web, multi
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

**Fields:**

- `title`: Human-readable task summary for frontend display
- `category`: IB domain(s) - `financial-analysis`, `due-diligence`,
  `document-review`, `data-extraction`
- `input_type`: Input format - `excel`, `pdf`, `web`, `multi` (for mixed inputs)

**Path alias:** `$human` expands to `data-warehouse/human-generated/`

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
- `match_type`: For programmatic - `"substring_one_of"`, `"regex_pattern"`,
  `"excel_cell_value"`, or `"excel_formatting"`
- `points`: Score weight for this criterion
- `gates_llm`: If `true` and this criterion fails, LLM criteria are skipped
  (saves cost). Only use when rubric has LLM judge criteria.

**Criterion ID alignment:**

- **Programmatic criteria**: ID must match the JSON output key exactly
- **LLM-judge criteria**: Can be evaluation dimensions (e.g.,
  `summary_synthesis`, `summary_drivers`) that assess qualities of an output
  field like `summary`

**Excel-specific match types:**

```json
{
  "cell_check": {
    "type": "programmatic",
    "match_type": "excel_cell_value",
    "cell": "K8",
    "expected": 1572,
    "tolerance": 1,
    "sheet": "Marine DCF",
    "points": 20
  },
  "formatting": {
    "type": "programmatic",
    "match_type": "excel_formatting",
    "sheet": "LBO",
    "points": 10
  }
}
```

**IB Formatting Conventions** (checked by `excel_formatting`):

- **Blue font**: Hardcoded numbers (values typed directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

**Excel scoring limitation:** Code execution environments (Claude, OpenAI,
Gemini) save Excel files without recalculating formulas. If the model's output
Excel shows `#VALUE!` errors but formulas are correct, prefer scoring via JSON
output using `regex_pattern` match type instead of `excel_cell_value`.

### Evaluation Types

Derived automatically from rubric criteria:

- **Programmatic**: All criteria have `type: "programmatic"`
- **LLM Judge**: All criteria have `type: "llm_judge"`
- **Hybrid**: Mix of both types

### Core Modules

| Module                        | Contents                                         |
| ----------------------------- | ------------------------------------------------ |
| `eval/helpers.py`             | Type definitions, task loading, utilities        |
| `eval/runners.py`             | LLM provider runners (Anthropic, OpenAI, Gemini) |
| `eval/llm-judge/llm_judge.py` | LLM-as-judge scorer for evaluation               |
| `eval/results/leaderboard.py` | Leaderboard generation and export                |
| `eval/results/analyze.py`     | Run analysis and comparison                      |

### Model Runners

`eval/runners.py` contains three runner classes:

| Runner            | Provider  | File Handling | Tools                         |
| ----------------- | --------- | ------------- | ----------------------------- |
| `AnthropicRunner` | Anthropic | Files API     | Code execution                |
| `OpenAIRunner`    | OpenAI    | Responses API | file_search, code_interpreter |
| `GeminiRunner`    | Google    | Files API     | Code execution                |

All runners support native file upload - no manual conversion needed.

## File Handling

All providers handle files natively via their respective APIs:

| Type        | Anthropic      | OpenAI           | Gemini         |
| ----------- | -------------- | ---------------- | -------------- |
| `.pdf`      | Files API      | file_search      | Files API      |
| `.xlsx`     | Code execution | code_interpreter | Code execution |
| `.png/.jpg` | Native vision  | code_interpreter | Files API      |

## Results Directory

```
eval/
├── responses/              # LLM outputs (expensive, preserve)
│   └── {model}/
│       └── {run_id}/
│           ├── config.json
│           ├── {task-id}.json
│           └── {task-id}_output_1.xlsx  # Output files from code execution
└── scores/                 # Scoring outputs (cheap, regenerable)
    └── {model}/
        └── {run_id}/
            ├── {task-id}.json  # includes rubric_hash, scored_at
            └── summary.json
```

Responses are cached and reused. Scores can be regenerated freely when rubrics
change. Score files include `rubric_hash` for audit trail.

### Output File Capture

When LLMs generate files via code execution (e.g., modified Excel spreadsheets),
these are automatically captured and saved:

- **AnthropicRunner**: Files from code execution container
- **OpenAIRunner**: Files from `code_interpreter` tool
- **GeminiRunner**: Inline data from responses

Output files are saved as `{task-id}_output_{n}.{ext}` and tracked in the
response JSON under `output_files`.

### Response JSON Fields

Each `{task-id}.json` contains:

| Field             | Description                                                                         |
| ----------------- | ----------------------------------------------------------------------------------- |
| `raw_response`    | Full text output from the model                                                     |
| `parsed_response` | Extracted JSON (if any)                                                             |
| `stop_reason`     | Why generation stopped: `end_turn`, `max_tokens`, `stop_sequence`, `content_filter` |
| `output_files`    | List of generated file names (if any)                                               |
| `usage`           | Token counts and latency                                                            |

### Content Filter Handling

Content filter blocks are handled automatically by runners. When triggered:

- Runners return `LLMResponse(stop_reason="content_filter")` instead of raising
- Response is saved normally with `stop_reason: "content_filter"`
- **Score phase**: Marked as `blocked: true`, 0 points, tracked separately
- **Leaderboard**: Shows blocked count separately (e.g., "5/6 (1 blocked)")

When using `--resume` or scoring, specify path as `MODEL/RUN_ID` (e.g.,
`claude-opus-4-5-20251101/20251230_114140`).

## Leaderboard

The leaderboard aggregates scores across models and calculates a weighted
overall score (max 100).

**Per-task credit:**

- 0 credit: < 50%
- 0.5 credit (half): 50-89%
- 1.0 credit (full): >= 90%

**Tier score:** `(total credits / tasks completed) × 100`

**Overall score:** `Easy×0.20 + Medium×0.35 + Hard×0.45`

Configuration is in `eval/configs/leaderboard_config.yaml`:

```yaml
weights:
  easy: 0.20
  medium: 0.35
  hard: 0.45

models: # Optional: filter to specific models
  - claude-opus-4-5-20251101
  - gpt-5.2-2025-12-11
```

**JSON export** (`--export`) produces `leaderboard.json` suitable for frontend
integration.

## Run Analysis

`eval/results/analyze.py` provides detailed diagnostics for a single run:

- **Metadata**: model, provider, date, task counts
- **Score Summary**: overall score, tier breakdown, credit counts
- **Health Warnings**: broken rubrics, missing judges, JSON parse failures
- **Task Breakdown**: grouped by credit tier (Full/Half/Partial/Fail)
- **Patterns**: failure rates by criteria type and task category

Use `--compare` to see score deltas between two runs.

## Task Workflow

### Creating Tasks

Use `.claude/skills/create-ib-task/SKILL.md`:

1. Populate `meta.yaml` with task details and expected answer
2. Run the skill to generate `prompt.md` and `rubric.json`

The skill ensures criterion IDs match JSON output keys and proper point
allocation.
