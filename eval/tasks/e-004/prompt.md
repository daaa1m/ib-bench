## Task

You are an investment banking analyst tasked with extracting and reconciling
AMD's Q3 2025 operating income metrics from GAAP to non-GAAP.

You must obtain AMD's Q3 2025 earnings report or financial statements from
either the SEC EDGAR database or AMD's Investor Relations website. From this
filing, extract and reconcile the following:

1. GAAP operating income
2. Non-GAAP operating income
3. All reconciling line items that bridge GAAP to non-GAAP operating income

## Methodology & Process

1. **Locate the Filing:** Use web search or navigate directly to SEC EDGAR
   (www.sec.gov/edgar) or AMD's Investor Relations website to find the Q3 2025
   earnings release or 10-Q filing
2. **Identify Reconciliation Section:** Locate the GAAP to non-GAAP
   reconciliation table, typically found in the earnings release or MD&A section
3. **Extract GAAP Operating Income:** Identify the GAAP operating income figure
   for Q3 2025
4. **Extract Non-GAAP Operating Income:** Identify the non-GAAP operating income
   figure for Q3 2025
5. **Extract Reconciling Items:** Identify each adjustment line item
6. **Verify the Reconciliation:** Ensure GAAP operating income + sum of
   adjustments = Non-GAAP operating income
7. **Verify Units:** Confirm whether amounts are stated in millions or billions
   and ensure your answer reflects this accurately

## Constraints and Negative Constraints

Constraints:

- Use the official SEC filing or AMD's IR website as your data source
- Report all values in millions USD (e.g., "1,234" for USD 1,234 million)
- Extract all reconciling line items that bridge GAAP to non-GAAP operating
  income
- Ensure the reconciliation mathematically ties

Negative Constraints:

- DO NOT confuse operating income with net income or other metrics
- DO NOT use data from different quarters or fiscal years
- DO NOT omit any reconciling line items
- DO NOT include items that reconcile other metrics (gross profit, net income,
  etc.)
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "gaap_operating_income": "GAAP operating income in millions USD",
  "non_gaap_operating_income": "Non-GAAP operating income in millions USD",
  "adjustments": [
    {"name": "First adjustment line item", "amount": "Amount in millions USD"},
    {"name": "Second adjustment line item", "amount": "Amount in millions USD"},
    "... include all reconciling line items"
  ]
}`
