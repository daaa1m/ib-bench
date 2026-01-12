## Task

You are an investment banking analyst tasked with completing a simple
3-statement model in `input.xlsx`. The Income Statement is already built; your
job is to complete the Balance Sheet and Cash Flow statements without changing
the structure of the model.

Your deliverable includes the completed Excel model and a JSON summary.

## Methodology & Process

1. Review the Income Statement and Assumptions to understand the model drivers.
2. Build or complete Balance Sheet line items using standard linkages and
   working capital relationships.
3. Build or complete the Cash Flow statement so it ties to the Balance Sheet.
4. Validate that ending cash from the Cash Flow ties to Balance Sheet cash.

## Constraints and Negative Constraints

Constraints:
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.
- Modify only the `Balance Sheet` and `Cash Flow` sheets.
- Preserve the template structure, headers, and existing formulas.
- Use USD millions and enter numbers only (no currency symbols).

Negative Constraints:
- DO NOT add or delete rows/columns.
- DO NOT change the Income Statement or Assumptions sheets.
- DO NOT hard-code values that should be formula-driven outside of the target
  sheets.
- NO conversational filler.

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the `Balance Sheet` and `Cash Flow` sheets.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

`{
  "cash_equivalents_fy2025": "Value in Balance Sheet!D7",
  "total_liabilities_fy2025": "Value in Balance Sheet!D35",
  "total_equity_fy2025": "Value in Balance Sheet!D41",
  "net_cash_from_ops_fy2026e": "Value in Cash Flow!E18",
  "net_cash_from_investing_fy2026e": "Value in Cash Flow!E22",
  "ending_cash_fy2026e": "Value in Cash Flow!E27",
  "formatting": "Optional: leave blank (scored from Excel file formatting)",
  "reasoning_steps": [
    "Step 1: How you completed the Balance Sheet",
    "Step 2: How you tied the Cash Flow",
    "Step 3: How you validated the model"
  ]
}`
