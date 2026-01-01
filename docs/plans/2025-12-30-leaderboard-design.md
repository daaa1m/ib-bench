# Leaderboard Design

## Overview

A leaderboard system to visualize IB-bench results and export them for public display.

## Scoring System

### Difficulty Tiers

Each task belongs to a difficulty tier:
- **Easy (e-)**: Foundation IB tasks
- **Medium (m-)**: Core analyst workload
- **Hard (h-)**: Advanced IB capabilities

### Per-Task Credit

Each task earns discrete credit based on points:
- **0 credit**: < 50 points (fail)
- **0.5 credit**: 50-99 points (half credit)
- **1.0 credit**: 100 points (full credit)

### Tier Scores

Each tier is scored 0-100 based on credits earned:

```
tier_score = (total_credits / tasks_completed) * 100
```

### Overall Score

Weighted average of tier scores (max 100):

```
overall = easy_score × 0.20 + medium_score × 0.35 + hard_score × 0.45
```

Default weights: Easy=20%, Medium=35%, Hard=45%

Weights are configurable via `leaderboard_config.yaml`.

## Output Formats

### CLI Output

Table format for development:

```
IB-bench Leaderboard
====================

Rank  Model                          Overall  Easy   Medium  Hard
----  -----------------------------  -------  -----  ------  -----
1     claude-opus-4-5-20251101         73.2   95.0    68.0   52.0
2     gpt-4o                           65.8   88.0    62.0   48.0
3     gemini-2.0-flash                 58.4   82.0    55.0   42.0

Weights: Easy=20% Medium=35% Hard=45%
```

### JSON Export

Canonical format for frontend integration:

```json
{
  "leaderboard_version": "1.0",
  "generated_at": "2025-12-30T14:30:00Z",
  "benchmark_version": "1.0",
  "weights": {
    "easy": 0.20,
    "medium": 0.35,
    "hard": 0.45
  },
  "task_counts": {
    "easy": 20,
    "medium": 10,
    "hard": 6
  },
  "entries": [
    {
      "rank": 1,
      "model": "claude-opus-4-5-20251101",
      "provider": "anthropic",
      "overall_score": 73.2,
      "scores_by_difficulty": {
        "easy": {"score": 95.0, "completed": 20, "total": 20},
        "medium": {"score": 68.0, "completed": 10, "total": 10},
        "hard": {"score": 52.0, "completed": 6, "total": 6}
      },
      "run_id": "20251230_114140",
      "run_date": "2025-12-30"
    }
  ]
}
```

## Implementation

### New File: `eval/leaderboard.py`

```
uv run python eval/leaderboard.py                    # CLI output
uv run python eval/leaderboard.py --export results/  # JSON export
uv run python eval/leaderboard.py --weights 25,35,40 # Custom weights
```

### Config File: `eval/leaderboard_config.yaml`

```yaml
weights:
  easy: 0.20
  medium: 0.35
  hard: 0.45

benchmark_version: "1.0"
```

### Data Flow

1. Scan `eval/scores/*/summary.json` for all runs
2. Group by model (latest run per model by default)
3. Calculate tier scores from task results
4. Compute weighted overall score
5. Sort by overall score, assign ranks
6. Output CLI table and/or JSON

## Edge Cases

- **Incomplete runs**: Only score attempted tiers; mark coverage in output
- **No tasks in tier**: Tier contributes 0 to weighted score (not skipped)
- **Multiple runs same model**: Use latest run (configurable later)
