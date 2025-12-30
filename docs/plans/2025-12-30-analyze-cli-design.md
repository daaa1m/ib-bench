# Score Analyzer CLI Design

## Overview

A CLI tool to analyze individual run results with full diagnostic dump.

## Command Interface

```bash
uv run python eval/analyze.py MODEL/RUN_ID
uv run python eval/analyze.py MODEL/RUN_ID --compare MODEL2/RUN_ID2
```

## Output Sections

1. **Metadata** - model, provider, date, task counts
2. **Score Summary** - overall, tier breakdown, credit counts
3. **Health Warnings** - broken rubrics, missing judges, 0% scores
4. **Full Credit** - tasks with 100 pts (what worked)
5. **Half Credit** - tasks with 50-99 pts (what's missing)
6. **Partial Fail** - tasks with 1-49 pts (close but not half)
7. **Full Fail** - tasks with 0 pts (what went wrong)
8. **Patterns** - failure patterns by criteria type and task category
9. **Comparison** (if --compare) - deltas between runs

## Credit Tiers

| Points | Tier | Credit |
|--------|------|--------|
| 100 | Full Credit | 1.0 |
| 50-99 | Half Credit | 0.5 |
| 1-49 | Partial Fail | 0.0 |
| 0 | Full Fail | 0.0 |
