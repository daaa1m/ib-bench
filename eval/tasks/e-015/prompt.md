## Task

You are an investment banking analyst asked to propose potential U.S. biotech
M&A targets as of January 1, 2026. Build two tiers of targets:

- **Tier 1**: 5 targets with 30-50% probability
- **Tier 2**: 5 targets with 15-30% probability

Use public sources to estimate market caps and provide a concise strategic
rationale for each target.

## Methodology & Process

1. Identify U.S.-listed biotech companies with strategic relevance to large
   acquirers.
2. Use current market data (as of Jan 1, 2026) to estimate market caps.
3. Assign each target to Tier 1 or Tier 2 based on plausibility and strategic
   fit.
4. Provide concise rationale tied to pipeline, modality, or platform fit.

## Constraints and Negative Constraints

Constraints:
- Provide exactly 5 Tier 1 and 5 Tier 2 targets.
- Each target must include company name, ticker, market cap, probability range,
  and strategic rationale.
- Focus on U.S. biotech companies only.
- Use sources to support market cap estimates.

Negative Constraints:
- DO NOT include non-biotech or non-U.S. companies.
- DO NOT repeat the same company across tiers.
- DO NOT include speculative rumors without rationale.
- NO conversational filler.

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "tier_1_targets": [
    {
      "name": "Company name",
      "ticker": "Ticker",
      "market_cap_usd_b": "Market cap in USD billions",
      "probability": "30-50%",
      "strategic_rationale": "Concise rationale",
      "source": "URL"
    }
  ],
  "tier_2_targets": [
    {
      "name": "Company name",
      "ticker": "Ticker",
      "market_cap_usd_b": "Market cap in USD billions",
      "probability": "15-30%",
      "strategic_rationale": "Concise rationale",
      "source": "URL"
    }
  ],
  "selection_methodology": "How you chose and tiered the targets",
  "source_urls": ["URL1", "URL2"],
  "reasoning_steps": ["Step 1: How you screened the universe", "Step 2: How you assigned tiers"]
}`
