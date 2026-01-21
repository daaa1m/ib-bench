## Task

You are an investment banking analyst tasked with building a transaction
comparables sheet for E&P oil & gas M&A in H2 2025. You are provided with
`input.xlsx`, which contains the `M&A Deals` sheet template. Populate 10
qualifying transactions announced between July 1 and December 31, 2025.

Each transaction must meet these criteria:
- E&P oil & gas industry
- Deal value >= USD 100m
- Corporate acquisitions or asset sales

Your deliverable includes the completed Excel model and a JSON summary.

## Methodology & Process

1. Identify qualifying H2 2025 E&P transactions using public sources.
2. For each transaction, extract the date, target or asset name, acquirer,
   seller (if applicable), deal value in USD millions, and payment type.
3. Populate the template rows in `M&A Deals` with 10 transactions.
4. Validate that each transaction meets the industry, date, and size filters.

## Constraints and Negative Constraints

Constraints:
- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.
- Modify only the `M&A Deals` sheet in `input.xlsx`.
- Fill exactly 10 rows (rows 2-11).
- Use USD millions and numeric values for deal value.
- For asset sales, include the seller; for corporate deals, seller may be blank.
- Use only public sources for deal details.

Negative Constraints:
- DO NOT include transactions outside H2 2025.
- DO NOT include deals under USD 100m.
- DO NOT include non-E&P industries.
- NO conversational filler.

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the `M&A Deals` sheet.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

`{
  "deal_list": [
    {
      "date": "MM/DD/YYYY",
      "target_or_asset": "Target or asset name",
      "acquirer": "Acquirer name",
      "seller": "Seller name or blank",
      "deal_value_usd_mm": "Deal value in USD millions",
      "payment_type": "Cash/Stock/Hybrid",
      "source": "URL"
    }
  ],
  "source_urls": ["URL1", "URL2"],
  "reasoning_steps": [
    "Step 1: How you screened for qualifying deals",
    "Step 2: How you verified deal values and payment types",
    "Step 3: How you validated industry and timing"
  ]
}`
