# IB-Bench Architecture Guide

A comprehensive guide to understanding the IB-bench codebase.

---

## Core Philosophy

**Separate expensive from cheap:**
- **Generation** (`run.py`): Slow, expensive LLM calls. Run once, cache forever.
- **Scoring** (`score.py`): Fast, cheap. Iterate on rubrics without re-running LLMs.
- **Aggregation** (`leaderboard.py`): Summarize scores across models.

This lets you refine evaluation criteria without burning API credits.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      TASK DEFINITIONS                       │
│           eval/tasks/{task-id}/                             │
│   meta.yaml │ prompt.md │ rubric.json │ input.*             │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           v                               v
┌─────────────────────┐        ┌─────────────────────┐
│     run.py          │        │  configs/*.yaml    │
│   GENERATION        │◄───────│  provider, model   │
│   (Expensive)       │        │  tasks, parallel   │
│                     │        └─────────────────────┘
│  1. Load tasks      │
│  2. Init runner     │
│  3. Call LLM        │
│  4. Save response   │
└─────────┬───────────┘
          │
          │ cached responses
          v
┌─────────────────────────────────────────────────────────────┐
│         responses/{model}/{run_id}/*.json                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          v                                 v
┌─────────────────────┐         ┌─────────────────────┐
│     score.py        │         │   leaderboard.py    │
│     SCORING         │         │    AGGREGATION      │
│     (Cheap)         │         │                     │
│                     │         │  Weighted scores    │
│  Programmatic eval  │         │  across models      │
│  LLM judge (gated)  │         │  JSON export        │
└─────────┬───────────┘         └─────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────┐
│           scores/{model}/{run_id}/*.json                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Reading Guide

Read in this order to build understanding incrementally:

### Level 1: Core Concepts (Start Here)

| Order | File | Why | Time |
|-------|------|-----|------|
| 1 | `CLAUDE.md` | Project overview, commands, conventions | 5 min |
| 2 | `eval/tasks/e-001/` | Example task structure (all 4 files) | 5 min |
| 3 | `eval/configs/quick-test.yaml` | Config file (copy from `eval/configs.example/`) | 2 min |

### Level 2: Main Pipeline

| Order | File | Why | Focus On |
|-------|------|-----|----------|
| 4 | `eval/helpers.py:1-100` | Task & LLMResponse dataclasses | Data structures |
| 5 | `eval/helpers.py:100-200` | `load_task()`, `load_tasks()` | Task discovery |
| 6 | `eval/run.py` | Generation flow | `run_task()`, `main()` |
| 7 | `eval/score.py:1-150` | Scoring logic | Criterion evaluation |
| 8 | `eval/score.py:150-300` | `score_task()` | Gate logic, LLM judge |

### Level 3: Provider Details

| Order | File | Why | Focus On |
|-------|------|-----|----------|
| 9 | `eval/helpers.py:300-450` | `AnthropicRunner` | Files API, code exec |
| 10 | `eval/helpers.py:450-550` | `OpenAIRunner` | Responses API |
| 11 | `eval/helpers.py:550-650` | `GeminiRunner` | Files API |
| 12 | `eval/helpers.py:650-700` | `LLMJudge` | Claude-as-judge |

### Level 4: Aggregation & Output

| Order | File | Why |
|-------|------|-----|
| 13 | `eval/leaderboard.py` | How scores become rankings |
| 14 | `eval/responses/`, `eval/scores/` | Output directory structure |

---

## Component Deep Dives

### eval/helpers.py (691 lines)

The workhorse. Contains everything shared between run and score.

**Key Sections:**

```
Lines 1-50     : Dataclasses (Task, LLMResponse)
Lines 50-100   : Task loading (load_task, load_tasks)
Lines 100-150  : Utilities (extract_json, get_rubric_hash)
Lines 150-200  : Rate limiting decorator
Lines 200-350  : AnthropicRunner
Lines 350-450  : OpenAIRunner
Lines 450-550  : GeminiRunner
Lines 550-650  : LLMJudge
Lines 650-700  : Factory functions (get_runner)
```

**Critical Functions:**

| Function | Purpose |
|----------|---------|
| `load_tasks()` | Discover tasks by ID or pattern |
| `_extract_json()` | Parse JSON from LLM response (3 strategies) |
| `get_runner()` | Factory for provider-specific runner |
| `retry_on_rate_limit()` | Decorator for 429 handling |

### eval/run.py (292 lines)

Orchestrates task execution against LLMs.

**Key Sections:**

```
Lines 1-50     : Imports, arg parsing
Lines 50-100   : Config loading (load_config, merge_config_with_args)
Lines 100-150  : run_task() - synchronous execution
Lines 150-200  : run_task_async() - async wrapper
Lines 200-250  : run_tasks_parallel() - concurrent execution
Lines 250-292  : main() - entry point
```

**Execution Flow:**

1. Parse config file + CLI args (CLI wins on conflicts)
2. Find tasks via `load_tasks()` with filter/IDs
3. Create timestamped run directory
4. Execute tasks (sequential or parallel)
5. Save responses with metadata
6. Update config.json with completion status

### eval/score.py (491 lines)

Evaluates LLM responses against rubric criteria.

**Key Sections:**

```
Lines 1-50     : Dataclasses (CriterionResult, TaskScore)
Lines 50-100   : Programmatic evaluators (substring, regex)
Lines 100-200  : LLM judge integration
Lines 200-350  : score_task() - main orchestration
Lines 350-450  : CLI and main()
Lines 450-491  : Summary generation
```

**Evaluation Types:**

| Type | Criteria | Cost | When Used |
|------|----------|------|-----------|
| Programmatic | All `type: "programmatic"` | Free | Always |
| LLM Judge | All `type: "llm_judge"` | $$$ | Subjective tasks |
| Hybrid | Mixed types | $ | Gate expensive with cheap |

**Gate Logic:**

```json
{
  "error_found": {
    "type": "programmatic",
    "gates_llm": true    // If this fails, skip LLM criteria
  },
  "explanation": {
    "type": "llm_judge"  // Only runs if error_found passes
  }
}
```

### eval/leaderboard.py (370 lines)

Aggregates scores into rankings.

**Scoring Formula:**

```
Task Credit:
  0.0  if score < 50%
  0.5  if 50% ≤ score < 100%
  1.0  if score == 100%

Tier Score = (sum of credits / total tasks) × 100

Overall = Easy×0.20 + Medium×0.35 + Hard×0.45
```

---

## Task Anatomy

Each task lives in `eval/tasks/{task-id}/`:

```
eval/tasks/e-001/
├── meta.yaml      # Metadata: id, type, category, expected answer
├── prompt.md      # Instructions to LLM
├── rubric.json    # Evaluation criteria (auto-generated)
└── input.xlsx     # Source file(s) - optional, pattern: input*.*
```

### meta.yaml

```yaml
task:
  id: e-001
  type: fix-error          # fix-error|summarise|extraction|creating
  category: excel          # excel|pdf|web
  description: "..."       # What the task tests

prompt:
  notes: "Special context"

input:
  input-file-original: "$human/source.xlsx"  # Path or [paths] or None
  notes: "Modifications made"
```

### rubric.json

```json
{
  "task_id": "e-001",
  "version": "1.0",
  "total_points": 100,
  "criteria": {
    "error_location": {
      "description": "Must find the error row",
      "type": "programmatic",
      "match_type": "substring_one_of",
      "accepted_values": ["Row 140", "L140", "row 140"],
      "points": 55,
      "gates_llm": true
    },
    "corrected_formula": {
      "type": "programmatic",
      "match_type": "regex_pattern",
      "valid_patterns": ["SUM\\(.*138.*139.*\\)"],
      "required_elements": ["138"],
      "forbidden_elements": ["#REF!"],
      "points": 45
    }
  }
}
```

---

## Model Runners

All runners share the same interface:

```python
class Runner:
    def run(self, task: Task, input_files: list[Path]) -> LLMResponse
```

| Runner | Provider | File Handling | Tools |
|--------|----------|---------------|-------|
| `AnthropicRunner` | Anthropic | Files API | Code execution |
| `OpenAIRunner` | OpenAI | Responses API | file_search, code_interpreter |
| `GeminiRunner` | Google | Files API | Code execution |

**File Type Routing:**

| Extension | Anthropic | OpenAI | Gemini |
|-----------|-----------|--------|--------|
| `.pdf` | Files API | file_search | Files API |
| `.xlsx` | Code exec | code_interpreter | Code exec |
| `.png/.jpg` | Vision | code_interpreter | Files API |

---

## Results Directory Structure

```
eval/
├── responses/                    # Expensive - PRESERVE
│   └── {model}/
│       └── {YYYYMMDD_HHMMSS}/
│           ├── config.json       # Run metadata
│           ├── e-001.json        # Raw + parsed response
│           └── e-002.json
│
└── scores/                       # Cheap - regenerable
    └── {model}/
        └── {YYYYMMDD_HHMMSS}/
            ├── e-001.json        # Criterion results
            ├── e-002.json
            └── summary.json      # Aggregated stats
```

**Response JSON:**

```json
{
  "task_id": "e-001",
  "model": "claude-opus-4-5-20251101",
  "timestamp": "2025-12-30T11:44:18.955574",
  "input_files": ["input.xlsx"],
  "raw_response": "...",
  "parsed_response": {"error_location": "Row 140"},
  "usage": {
    "input_tokens": 188187,
    "output_tokens": 7184,
    "latency_ms": 157073.33
  }
}
```

**Score JSON:**

```json
{
  "task_id": "e-001",
  "rubric_hash": "4ee50e89",
  "scored_at": "2025-12-30T20:04:35.865141",
  "passed": true,
  "total_points": 100,
  "points_earned": 100,
  "score_percent": 100.0,
  "llm_gated": false,
  "criteria": [...]
}
```

---

## Cheat Sheet

### Running Tasks

Copy `eval/configs.example/` to `eval/configs/` before running.

```bash
# Single task
uv run python eval/run.py --tasks e-001 --model claude-sonnet-4-20250514

# Multiple specific tasks
uv run python eval/run.py --tasks e-001 e-002 e-003 --model gpt-4o

# All easy tasks
uv run python eval/run.py --filter e- --model gemini-2.5-flash

# With config file
uv run python eval/run.py --config configs/quick-test.yaml

# Override config
uv run python eval/run.py --config configs/full-easy.yaml --model gpt-4o

# Parallel execution (5 concurrent)
uv run python eval/run.py --filter e- --model claude-opus-4-5 --parallel 5

# Resume interrupted run
uv run python eval/run.py --resume claude-opus-4-5/20251230_114140
```

### Scoring

```bash
# Score a run
uv run python eval/score.py MODEL/RUN_ID
uv run python eval/score.py claude-opus-4-5-20251101/20251230_114140

# Score specific tasks only
uv run python eval/score.py claude-opus-4-5/20251230_114140 --tasks e-001 e-002

# Force rescore (ignore cached)
uv run python eval/score.py claude-opus-4-5/20251230_114140 --rescore
```

### Leaderboard

```bash
# Display leaderboard
uv run python eval/leaderboard.py

# Export JSON
uv run python eval/leaderboard.py --export results/

# Custom weights
uv run python eval/leaderboard.py --weights 25,35,40
```

### Task Management

```bash
# List all tasks
ls eval/tasks/

# Count tasks by difficulty
ls eval/tasks/ | grep "^e-" | wc -l   # Easy
ls eval/tasks/ | grep "^m-" | wc -l   # Medium
ls eval/tasks/ | grep "^h-" | wc -l   # Hard
```

### Common Patterns

```bash
# Full workflow: run all easy, score, view leaderboard
uv run python eval/run.py --filter e- --model claude-opus-4-5 --parallel 5
uv run python eval/score.py claude-opus-4-5/LATEST_RUN_ID
uv run python eval/leaderboard.py

# Compare two models
uv run python eval/run.py --filter e- --provider anthropic --model claude-opus-4-5
uv run python eval/run.py --filter e- --provider openai --model gpt-4o
uv run python eval/leaderboard.py
```

### Quick Reference

| What | Command |
|------|---------|
| Run tests | `uv run pytest eval/test_eval.py -v` |
| Add dependency | `uv add package-name` |
| Check env | `cat .env` |
| View task | `cat eval/tasks/e-001/prompt.md` |
| View rubric | `cat eval/tasks/e-001/rubric.json` |
| Check response | `cat eval/responses/MODEL/RUN_ID/e-001.json` |
| Check score | `cat eval/scores/MODEL/RUN_ID/e-001.json` |

### Rubric Match Types

| Type | Usage | Example |
|------|-------|---------|
| `substring_one_of` | Any value in list appears in response | `["Row 140", "L140"]` |
| `regex_pattern` | Pattern matches response | `"SUM\\(.*138.*\\)"` |

### Criterion ID Rules

- **Programmatic**: ID must match response JSON key
  - Response: `{"error_location": "Row 140"}`
  - Criterion: `"error_location"`

- **LLM Judge**: Can be dimension names
  - Response field: `summary`
  - Criteria: `summary_quality`, `summary_clarity`

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

### Config File Template

```yaml
# eval/configs/my-config.yaml
provider: anthropic          # anthropic|openai|gemini
model: claude-sonnet-4-20250514
tasks:                       # OR use filter
  - e-001
  - e-002
# filter: e-                 # Alternative: run all matching prefix
parallel: 1                  # Concurrent tasks (default: 1)
```

---

## Debugging Tips

**Task not loading?**
- Check directory name matches pattern: `{e|m|h}-{###}`
- Ensure `meta.yaml` and `prompt.md` exist

**JSON not parsing?**
- LLM must output valid JSON (check `parsed_response` in response file)
- Three extraction strategies: direct parse → code block → regex

**Gate blocking LLM eval?**
- Check `llm_gated: true` in score output
- Review which criterion has `gates_llm: true` in rubric

**Rubric not matching?**
- Add more variants to `accepted_values`
- Use `regex_pattern` for flexible matching
- Case sensitivity: substring matching is case-sensitive

**Rate limited?**
- Reduce `--parallel` count
- Built-in retry with exponential backoff handles 429s

---

## Key Design Decisions

1. **Responses cached forever** - Never re-run expensive LLM calls
2. **Rubric hash tracking** - Know which rubric version scored each response
3. **Gate logic** - Save $ by skipping LLM judge when programmatic fails
4. **Provider abstraction** - Same interface for all LLM providers
5. **Discrete task credit** - 0/0.5/1 prevents gaming with partial answers
6. **Weighted tiers** - Hard tasks worth more (45% vs 20% for easy)
