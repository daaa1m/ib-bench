# IB-Bench Architecture Guide

A comprehensive guide to understanding the IB-bench codebase.

---

## Core Philosophy

**Separate expensive from cheap:**

- **Generation** (`run.py`): Slow, expensive LLM calls. Run once, cache forever.
- **Scoring** (`score.py`): Fast, cheap. Iterate on rubrics without re-running
  LLMs.
- **Analysis** (`analyze.py`): Deep dive into per-model performance and failure
  patterns.
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
  title: "Short task title" # 10-100 chars
  type: fix-error # fix-error|summarise|extraction|creating
  category: # Array of categories
    - financial-analysis # financial-analysis|due-diligence|document-review|data-extraction
  input_type: excel # excel|pdf|web|multi
  description: "..." # What the task tests (min 50 chars)

prompt:
  notes: "Special context for prompt generation"

input:
  input-file-original: "$human/source.xlsx" # Path, [paths], or null
  notes: "Modifications made to source file"
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

| Runner              | Provider      | File Handling          | Tools                                        |
| ------------------- | ------------- | ---------------------- | -------------------------------------------- |
| `AnthropicRunner`   | Anthropic     | Files API              | Code execution                               |
| `OpenAIRunner`      | OpenAI        | Responses API          | file_search, code_interpreter, web_search    |
| `GeminiRunner`      | Google        | Files API              | Code execution                               |
| `AzureAgentRunner`  | Azure (v1)    | Agent Files API        | code_interpreter, file_search                |
| `AzureAgentRunnerV2`| Azure (v2)    | Containers + Vector Stores | code_interpreter, file_search, web_search |

### Azure Runners

Azure AI Foundry supports multiple model providers through a unified API:
- **OpenAI models**: GPT-4o, GPT-5, o1, o3, o4
- **Third-party models**: Mistral, DeepSeek, Llama, Grok

**AzureAgentRunner (v1)**: Uses the Agent Service SDK with `client.agents` API.

**AzureAgentRunnerV2 (v2)**: Uses the Responses API with containers. Recommended.
- For **OpenAI models**: Uses native `web_search_preview` tool
- For **other models**: Uses Brave Search via function calling (requires `BRAVE_API_KEY`)

**File Type Routing:**

| Extension   | Anthropic | OpenAI           | Gemini    | Azure v2              |
| ----------- | --------- | ---------------- | --------- | --------------------- |
| `.pdf`      | Files API | file_search      | Files API | file_search (vector)  |
| `.xlsx`     | Code exec | code_interpreter | Code exec | code_interpreter      |
| `.png/.jpg` | Vision    | Vision (base64)  | Files API | code_interpreter      |

---

## Results Directory Structure

```
eval/
├── responses/
│   └── {model}/
│       └── {YYYYMMDD_HHMMSS}/
│           ├── config.json       # Run metadata
│           ├── e-001.json        # Raw + parsed response
│           └── e-002.json
│
└── scores/
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
  "parsed_response": { "error_location": "Row 140" },
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
