## Task

You are an investment banking analyst tasked with populating a shareholder
summary for Apple (AAPL). You are provided with `input.xlsx`, which includes a
`Holders` sheet template. Use 13F data or other credible public sources to fill
in the top 15 largest shareholders.

Your deliverable includes the completed Excel model and a JSON summary.

## Methodology & Process

1. Identify the most recent 13F filings or credible ownership datasets for AAPL.
2. Rank holders by shares held and select the top 15.
3. Populate the template with name, shares held, market value, % of portfolio,
   and % ownership.
4. Cross-check totals using the Rubric sheet (do not edit it).

## Constraints and Negative Constraints

Constraints:
- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.
- Modify only the `Holders` sheet in `input.xlsx`.
- Fill exactly 15 rows (rows 2-16).
- Use numeric values only (no currency symbols).
- Keep units consistent with the template.

Negative Constraints:
- DO NOT edit the `Rubric` sheet.
- DO NOT change the template structure or headers.
- DO NOT fabricate data; use verifiable sources.
- NO conversational filler.

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the `Holders` sheet.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

`{
  "top_5_holders": [
    {
      "name": "Holder name",
      "shares_held": "Number of shares",
      "market_value_usd": "Market value in USD",
      "pct_of_portfolio": "Percent of portfolio",
      "pct_ownership": "Percent ownership"
    }
  ],
  "data_sources": ["URL1", "URL2"],
  "reasoning_steps": [
    "Step 1: How you sourced the ownership data",
    "Step 2: How you ranked the holders",
    "Step 3: How you validated totals"
  ]
}`
