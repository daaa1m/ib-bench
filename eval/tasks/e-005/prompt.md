## Task

You are an investment banking analyst tasked with analyzing Amazon's Q3 2025
earnings and preparing a summary for senior bankers.

You are provided with three documents:
- Amazon's Q3 2025 10-Q filing
- Amazon's Q3 2025 earnings press release
- Amazon's Q3 2025 earnings conference call slides

Your deliverable has two parts:
1. Extract key financial metrics for Q3 2025 and Q4 2025 guidance
2. Write a one-page earnings summary highlighting important topics

## Methodology & Process

1. **Review All Documents**: Read the 10-Q, press release, and slides to
   understand the full earnings picture
2. **Extract Key Metrics**: Identify revenue, operating income, diluted EPS,
   and forward guidance figures
3. **Identify Key Themes**: Note segment performance, growth drivers, margin
   trends, strategic initiatives, and management commentary
4. **Write Summary**: Synthesize findings into a coherent narrative that a
   senior banker could use to quickly understand the quarter

## Constraints and Negative Constraints

Constraints:
- Report revenue and operating income in millions USD
- Report diluted EPS as a dollar amount with two decimal places
- Report guidance in billions USD
- Summary should be approximately one page (300-500 words)
- Summary should be structured with clear sections or paragraphs
- Include specific figures to support key points

Negative Constraints:
- DO NOT use TTM (trailing twelve months) figures
- DO NOT confuse Q3 2025 with Q3 2024 or other periods
- DO NOT include generic filler or boilerplate language
- DO NOT omit significant business developments or risks mentioned
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```json
{
  "q3_revenue": "Q3 2025 total net sales in millions USD",
  "q3_operating_income": "Q3 2025 operating income in millions USD",
  "q3_diluted_eps": "Q3 2025 diluted earnings per share",
  "q4_revenue_guidance": "Q4 2025 revenue guidance range in billions USD (e.g., '206.0 - 213.0')",
  "q4_operating_income_guidance": "Q4 2025 operating income guidance range in billions USD",
  "summary": "One-page earnings summary for senior bankers"
}
```
