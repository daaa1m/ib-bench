## Task

You are an investment banking analyst tasked with building a debt schedule for
Carnival Corp covering 3Q22 through 2025. You are provided with `input.xlsx`,
which includes a pre-built template on the `Debt` sheet with the period headers
already populated. Your job is to populate the schedule with the correct debt
amounts and maturities using Carnival Corp 10-Q and 10-K filings.

Your deliverable includes the completed Excel model and a JSON summary.

## Methodology & Process

1. Identify the relevant Carnival Corp 10-Q and 10-K filings covering 3Q22
   through 2025 and locate the debt tables (by maturity and by instrument).
2. Map each debt instrument into the template rows and confirm the correct
   period column (3Q22 through 2025 in columns G through X).
3. Populate the template with hardcoded values for each period, keeping all
   existing formulas intact.
4. Check that totals reconcile within the template and that the Total Debt row
   is consistent with the filings for each period.

## Constraints and Negative Constraints

Constraints:
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.
- Modify only the `Debt` sheet in `input.xlsx`.
- Fill in the periods from 3Q22 through 2025 (columns G through X).
- Use USD millions and enter numbers only (no currency symbols or text).
- Preserve the template structure, headers, and formulas.
- Use only Carnival Corp 10-Q and 10-K filings as sources.

Negative Constraints:
- DO NOT add or delete rows/columns.
- DO NOT overwrite existing formulas.
- DO NOT use external sources other than the filings.
- NO conversational filler.

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the `Debt` sheet.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

`{
  "total_debt_3q22": "Value in Debt!G95",
  "total_debt_2023": "Value in Debt!N95",
  "total_debt_2025": "Value in Debt!X95",
  "short_term_borrowings_3q22": "Value in Debt!G96",
  "short_term_borrowings_2023": "Value in Debt!N96",
  "short_term_borrowings_2025": "Value in Debt!X96",
  "short_term_debt_3q22": "Value in Debt!G97",
  "short_term_debt_2023": "Value in Debt!N97",
  "short_term_debt_2025": "Value in Debt!X97",
  "formatting": "Optional: leave blank (scored from Excel file formatting)",
  "reasoning_steps": [
    "Step 1: How you located the debt tables",
    "Step 2: How you mapped instruments to the schedule",
    "Step 3: How you validated the totals"
  ]
}`
