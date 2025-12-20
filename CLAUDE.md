# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IB-bench is an LLM benchmark for testing investment banking analyst tasks (Excel modeling, document analysis, data extraction). Inspired by SWE-bench but focused on IB-specific work.

## Commands

All Python scripts must be run with `uv run`:

```bash
# Run evaluation on all tasks
uv run python eval/run.py

# Run specific tasks
uv run python eval/run.py --tasks e-001 e-002

# Run tasks by difficulty prefix (e- = easy, m- = medium, h- = hard)
uv run python eval/run.py --filter e-

# Score responses from a run
uv run python eval/score.py RUN_ID
uv run python eval/score.py RUN_ID --tasks e-001
uv run python eval/score.py RUN_ID --rescore
```

## Architecture

### Core Principle: Separate Expensive from Cheap

- **Generation (`eval/run.py`)**: Slow, expensive LLM calls. Run once, cache responses.
- **Scoring (`eval/score.py`)**: Fast, cheap. Iterate on rubrics freely without re-running generation.

### Directory Structure

- `eval/tasks/` - Task definitions (one folder per task: `e-001/`, `m-001/`, `h-001/`)
- `eval/results/` - Run outputs organized by timestamp and model
- `data-factory/` - Source data (human-generated and synthetic) for creating tasks

### Task Anatomy

Each task folder contains:
- `prompt.md` (required) - Instructions for the model
- `input.*` - Input files, multiple allowed (auto-detected by `input*.<ext>` pattern, e.g., `input.xlsx`, `input_appendix.pdf`)
- `rubric.json` - Evaluation criteria (programmatic, llm_judge, or hybrid)
- `meta.yaml` - Metadata and config

Task IDs follow naming: `{difficulty}-{number}` where difficulty is `e` (easy), `m` (medium), or `h` (hard).

### Evaluation Types

- **Programmatic**: Deterministic checks (regex, contains, number ranges)
- **LLM Judge**: Qualitative assessment via another LLM
- **Hybrid**: Weighted combination of both

### Model Runners

`eval/helpers.py` contains `OpenAIRunner` and `AnthropicRunner` classes for API calls.

## File Handling

| Type | Processing |
|------|------------|
| `.pdf` | Native Claude document support |
| `.xlsx` | Converted to JSON with formulas preserved (see below) |
| `.png/.jpg` | Native image support |
| `.csv/.txt` | Sent as text |

### Excel Converter

Since no LLM API natively supports xlsx with formula preservation, use the converter:

```bash
# Convert xlsx to JSON (preserves formulas + computed values + formatting)
uv run python eval/xlsx_converter.py path/to/file.xlsx

# Save to file
uv run python eval/xlsx_converter.py path/to/file.xlsx --output output.json
```

Output format:
```json
{
  "sheets": {
    "Sheet1": {
      "cells": {
        "L140": {"formula": "=SUM(L135:L139)", "value": 1000, "type": "formula"},
        "B1": {"value": 100, "type": "number", "format": {"font_color": "#0000FF", "number_format": "#,##0"}}
      }
    }
  },
  "named_ranges": {"Revenue": "Sheet1!$B$5:$F$5"}
}
```

Formatting captured: `font_color` (blue = inputs), `bold`, `italic`, `underline`, `background`, `number_format`, `align`.
