## Task

You are an investment banking analyst preparing a research summary for senior
bankers. You have been provided with two equity research reports on Alphabet
(GOOGL) following Q3 2025 earnings - one from Goldman Sachs and one from
JPMorgan - along with each bank's financial model.

Your deliverable has two parts:

1. Extract key metrics from both research reports (ratings, price targets, key
   estimates)
2. Write a summary note synthesizing both analysts' views and identifying the
   key drivers from the models

## Methodology & Process

1. **Review Both Research Reports**: Read the Goldman Sachs and JPMorgan reports
   to understand each analyst's investment thesis
2. **Extract Key Metrics**: Identify ratings, price targets, and key financial
   estimates from each bank
3. **Analyze the Models**: Review both Excel models to identify key revenue and
   margin drivers, noting any differences in assumptions
4. **Synthesize Views**: Compare and contrast the two research perspectives,
   noting areas of agreement and any differences
5. **Identify Key Drivers**: Based on both models and research, identify the 3-5
   most important drivers of Alphabet's valuation

## Constraints and Negative Constraints

Constraints:

- Include specific figures (price targets, growth rates, multiples) when citing
  analyst views
- Reference both Goldman Sachs and JPMorgan perspectives
- Key drivers should be tied to specific model line items or segment metrics
- Summary should be 400-600 words, suitable for senior banker briefing

Negative Constraints:

- DO NOT simply repeat one analyst's view - must synthesize both
- DO NOT include boilerplate disclosures from the research reports
- DO NOT confuse metrics between the two banks
- DO NOT ignore the Excel model when discussing drivers
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```json
{
  "gs_rating": "Goldman Sachs rating (Buy/Neutral/Sell)",
  "gs_price_target": "Goldman Sachs 12-month price target in dollars",
  "jpm_rating": "JPMorgan rating (Overweight/Neutral/Underweight)",
  "jpm_price_target": "JPMorgan price target in dollars",
  "q3_search_growth": "Q3 2025 Google Search revenue YoY growth percentage",
  "q3_cloud_growth": "Q3 2025 Google Cloud revenue YoY growth percentage",
  "fy25_capex_guidance": "FY2025 capex guidance range in billions",
  "key_drivers": ["Driver 1", "Driver 2", "Driver 3", "..."],
  "summary": "400-600 word synthesis of both research views and key model drivers"
}
```
