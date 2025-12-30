# Leaderboard Future Enhancements

## Task Category Breakdown

Add scoring by task category (excel, pdf, web) in addition to difficulty:

```json
"scores_by_category": {
  "excel": {"score": 85.0, "completed": 15, "total": 15},
  "pdf": {"score": 72.0, "completed": 12, "total": 12},
  "web": {"score": 65.0, "completed": 9, "total": 9}
}
```

This would show capability profiles: "Model X excels at Excel but struggles with PDFs"

## Cost/Latency Metrics

Track operational metrics per run:

```json
"metrics": {
  "total_tokens": 125000,
  "avg_response_time_ms": 4500,
  "estimated_cost_usd": 2.50
}
```

Useful for cost-performance tradeoff analysis.

## Multiple Runs Per Model

Options to consider:
- Best run (highest overall score)
- Latest run (current default)
- Average across N runs
- Confidence intervals from multiple runs

Needs decision on what's most meaningful for benchmark credibility.
