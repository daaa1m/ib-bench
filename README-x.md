# LLM Evaluation Pipeline

A lightweight, practical evaluation framework for testing LLM capabilities on complex tasks involving documents, spreadsheets, and multi-step reasoning.

### Core Principle: Separate Expensive from Cheap

```
┌─────────────────────────────────────────────────────────────────┐
│  GENERATION (run.py)          │  SCORING (score.py)            │
│                               │                                 │
│  - Slow (1-5 min per task)    │  - Fast (seconds per task)     │
│  - Expensive ($0.50-2+/task)  │  - Cheap (10x less)            │
│  - Run once                   │  - Run many times              │
│  - Needs model API            │  - Iterate on rubrics freely   │
└─────────────────────────────────────────────────────────────────┘
```

You can:

1. Write all your task prompts
2. Start a generation run
3. Write rubrics while waiting (or after)
4. Score and re-score as you refine criteria

## Project Structure

```
eval/
├── tasks/                      # One folder per task
│   ├── e-001/                  # Easy task 001
│   │   ├── prompt.md           # The task prompt (required)
│   │   ├── input.pdf           # Input files (optional)
│   │   ├── rubric.json         # Evaluation criteria (for scoring)
│   │   └── meta.yaml           # Metadata and config (optional)
│   ├── e-002/
│   ├── m-001/                  # Medium task 001
│   └── h-001/                  # Hard task 001
├── results/                    # One folder per run
│   └── 20250115_143022_sonnet/
│       ├── config.json         # Run configuration
│       ├── responses/          # Model outputs (expensive, cached)
│       │   ├── e-001.json
│       │   └── e-002.json
│       ├── scores/             # Evaluation scores (cheap, regenerate freely)
│       │   ├── e-001.json
│       │   └── e-002.json
│       └── summary.json        # Aggregated results
├── run.py                      # Generate responses
├── score.py                    # Score responses
├── status.py                   # Check progress
└── helpers.py                  # Shared utilities
```

## Task Anatomy

### Minimal Task (just needs prompt)

```
tasks/e-001/
└── prompt.md
```

### Full Task

```
tasks/e-001/
├── prompt.md           # Required: instructions for the model
├── input.pdf           # Optional: files to include in prompt
├── input.xlsx          # Optional: multiple inputs supported
├── rubric.json         # Required for scoring: evaluation criteria
└── meta.yaml           # Optional: metadata and config overrides
```

### `prompt.md`

The task instructions. Can reference attached files:

```markdown
Review the attached financial report and:

1. Identify the top 3 risks mentioned
2. Summarize the revenue trend
3. Flag any inconsistencies in the data

Be specific and cite page numbers where relevant.
```

### `rubric.json`

Defines how to evaluate the response. Three evaluation types:

**Programmatic (deterministic checks):**

```json
{
  "checks": [
    {
      "id": "mentions_revenue",
      "type": "contains",
      "target": "revenue",
      "weight": 0.3
    },
    {
      "id": "has_page_citations",
      "type": "regex",
      "pattern": "page \\d+",
      "weight": 0.3
    },
    {
      "id": "reasonable_length",
      "type": "number_in_range",
      "min": 100,
      "max": 500,
      "weight": 0.4
    }
  ]
}
```

**LLM Judge (qualitative assessment):**

```json
{
  "criteria": [
    {
      "id": "accuracy",
      "weight": 0.4,
      "description": "Are the identified risks actually present in the document?"
    },
    {
      "id": "completeness",
      "weight": 0.3,
      "description": "Are the top 3 most significant risks captured?"
    },
    {
      "id": "clarity",
      "weight": 0.3,
      "description": "Is the response well-structured and easy to follow?"
    }
  ]
}
```

**Hybrid (both):**

```json
{
  "programmatic": {
    "checks": [
      {
        "id": "has_citations",
        "type": "regex",
        "pattern": "page \\d+",
        "weight": 1.0
      }
    ]
  },
  "llm_judge": {
    "criteria": [
      { "id": "accuracy", "weight": 0.5, "description": "..." },
      { "id": "insight", "weight": 0.5, "description": "..." }
    ]
  }
}
```

### `meta.yaml`

```yaml
# Documentation (for humans)
id: e-001
title: Financial Report Risk Analysis
description: Extract and summarize key risks from an annual report
difficulty: easy
category: document_analysis
tags: [pdf, finance, summarization]

# ────────────────────────────────────────────
# Config (for pipeline)
# ────────────────────────────────────────────
evaluation:
  type: hybrid # "programmatic", "llm_judge", or "hybrid"
  include_inputs: true # Include original files in judge context
  programmatic:
    weight: 0.3
  llm_judge:
    weight: 0.7
    model: claude-sonnet-4-20250514 # Optional: override judge model
```

## File Handling

The pipeline automatically handles different input file types:

| File Type       | How It's Processed                          |
| --------------- | ------------------------------------------- |
| `.pdf`          | Sent natively via Claude's document support |
| `.png`, `.jpg`  | Sent natively as images                     |
| `.xlsx`, `.xls` | Converted to markdown tables                |
| `.csv`          | Sent as text                                |
| `.txt`          | Sent as text                                |

Files are detected by glob pattern `input*.<ext>` in the task folder:

- `input.pdf` ✓
- `input_data.xlsx` ✓
- `input_appendix.pdf` ✓
- `output.xlsx` ✗ (ignored)
- `expected.pdf` ✗ (ignored)

## Usage

### 1. Create Tasks

```bash
mkdir -p tasks/e-001
echo "Summarize the attached document." > tasks/e-001/prompt.md
cp my_document.pdf tasks/e-001/input.pdf
```

### 2. Run Generation

```bash
# Run all tasks
python run.py

# Run specific tasks
python run.py --tasks e-001 e-002 m-001

# Run by difficulty
python run.py --filter e-      # Easy only
python run.py --filter h-      # Hard only

# Use different model
python run.py --model claude-opus-4-20250514

# Continue interrupted run
python run.py --continue-run 20250115_143022_sonnet
```

Output:

```
Loaded 50 tasks
New run: 20250115_143022_sonnet

[1/50] e-001
    Done in 45s, ~$0.42
    ETA: 35m remaining

[2/50] e-002
    Done in 1.2m, ~$0.78
    ETA: 33m remaining
...
```

### 3. Write Rubrics (can do while generation runs)

```bash
# Check which tasks need rubrics
python status.py

# Output:
# TASKS
#   e-001: ready
#   e-002: ready
#   e-003: no rubric
#   e-004: no rubric
```

### 4. Score Responses

```bash
# Score all tasks that have rubrics
python score.py 20250115_143022_sonnet

# Score specific tasks
python score.py 20250115_143022_sonnet --tasks e-001 e-002

# Re-score after updating rubrics
python score.py 20250115_143022_sonnet --rescore
```

Output:

```
Scoring 50 responses

[e-001] Scoring (llm_judge)...
[e-001] Score: 82%

[e-002] Scoring (hybrid)...
[e-002] Score: 75%

[e-003] No rubric yet, skipping
...

══════════════════════════════════════════
Overall: 78.2% (n=48)
  easy: 85.1% (n=20)
  medium: 76.3% (n=18)
  hard: 69.4% (n=10)
```

### 5. View Results

```bash
# Quick status
python status.py

# Detailed results in JSON
cat results/20250115_143022_sonnet/summary.json

# Individual task results
cat results/20250115_143022_sonnet/responses/e-001.json
cat results/20250115_143022_sonnet/scores/e-001.json
```

## Evaluation Types

### Programmatic

Best for: Exact answers, format checking, keyword presence

```json
{
  "checks": [
    {
      "id": "check_id",
      "type": "contains",
      "target": "expected text",
      "weight": 1.0
    },
    {
      "id": "check_id",
      "type": "regex",
      "pattern": "\\d{4}-\\d{2}-\\d{2}",
      "weight": 1.0
    },
    {
      "id": "check_id",
      "type": "number_in_range",
      "min": 100,
      "max": 200,
      "weight": 1.0
    }
  ]
}
```

Check types:

- `contains`: Case-insensitive substring match
- `regex`: Regular expression match
- `number_in_range`: Any number in output falls within range

### LLM Judge

Best for: Open-ended responses, reasoning quality, subjective criteria

```json
{
  "criteria": [
    { "id": "criterion_id", "weight": 0.5, "description": "What to evaluate" }
  ]
}
```

The judge receives:

- Original task prompt
- Original input files (if `include_inputs: true`)
- Model's response
- Evaluation criteria

### Hybrid

Best for: Tasks needing both exact checks and qualitative assessment

Combines both, with configurable weights:

```yaml
evaluation:
  type: hybrid
  programmatic:
    weight: 0.4
  llm_judge:
    weight: 0.6
```

## Resilience Features

### Automatic Resume

If a run crashes, just re-run the same command:

```bash
python run.py --continue-run 20250115_143022_sonnet
# Picks up where it left off
```

### Retry with Backoff

API errors automatically retry with exponential backoff (up to 5 attempts).

### Progress Tracking

- ETA displayed during runs
- Cost estimates per task and total
- Token usage tracked

### Separate Storage

Responses and scores stored separately:

- Responses: Expensive, preserved
- Scores: Cheap, freely regenerated

## Cost Management

Approximate costs (Claude Sonnet):

- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

For chunky tasks with documents:

- ~$0.50-2.00 per task generation
- ~$0.05-0.20 per task scoring (LLM judge)
- Full 50-task run: $50-150

Tips:

- Use `--filter` to test on subset first
- Check `status.py` before re-running
- Iterate on rubrics freely (scoring is cheap)

## Extending

### Adding New Check Types

Edit `score.py`:

```python
def run_check(check: dict, output: str) -> bool:
    if check["type"] == "my_new_check":
        # Your logic here
        return True
    # ... existing checks
```

### Adding New File Types

Edit `helpers.py`:

```python
def prepare_file_for_prompt(file_path: Path) -> dict:
    if suffix == ".my_format":
        # Your extraction logic
        return {"type": "text", "text": extracted_content}
    # ... existing handlers
```

### Custom Scoring Logic

For task-specific scoring, add a `score.py` in the task folder:

```
tasks/e-001/
├── prompt.md
├── rubric.json
└── score.py          # Custom scoring logic
```

```python
# tasks/e-001/score.py
def score(output: str, rubric: dict) -> dict:
    # Custom logic
    return {"overall": 0.85, "details": {...}}
```

## FAQ

**Q: Can I run without rubrics?**
Yes. Generation doesn't need rubrics. Add them later and run scoring when ready.

**Q: Can I use GPT-4 instead of Claude?**
The pipeline is Claude-focused but you can swap `helpers.py` to use OpenAI's API. File handling will need adjustment since OpenAI handles documents differently.

**Q: How do I compare two runs?**

```bash
# Manual for now
diff results/run1/summary.json results/run2/summary.json
```

**Q: Can I use this for agentic/tool-use tasks?**
Yes, but you'll need to implement tool execution in `helpers.py`. The structure supports multi-turn conversations.

## License

MIT
