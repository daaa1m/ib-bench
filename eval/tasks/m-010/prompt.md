## Task

You are an investment banking analyst tasked to update an ongoing 3 statement
model. You are given an existing equity model in `input-1.xlsx` that has not yet
been updated with actuals for 3Q25. You are also given `input-2.pdf`, the
company’s 3Q25 10-Q.

Your task is to update the model so that the 3Q25 estimate column is replaced
with 3Q25 actuals using the 10-Q.

Make the updates in these locations only:

- **Segments** sheet: update the **3Q25 column (column BT)**
- **IS** sheet: update the **3Q25 column (column BO)**
- **BS & CFS** sheet: update the **3Q25 column (column BB)**

After updating, the model must be internally consistent (e.g., revenue totals
tie across tabs, and the balance sheet balances).

## Methodology & Process

1. Read the 3Q25 10-Q and identify the exact 3Q25 reported figures needed for
   the Segments tab, Income Statement tab, and Balance Sheet / Cash Flow tab.
2. In `input-1.xlsx`, locate the 3Q25 estimate columns (BT / BO / BB) and
   confirm you are editing the correct period.
3. Update the 3Q25 columns with actuals from the 10-Q, following the structure
   of the existing model (do not redesign the model).
4. Preserve formulas where appropriate and only replace values that are supposed
   to be actual inputs for 3Q25.
5. Verify internal consistency:
   - Total revenue ties between Segments and IS
   - Balance sheet ties (Total Assets equals Total Liabilities and Equity)
6. Do a final scan for obvious errors (blank required cells, incorrect signs,
   broken references).

## Constraints

- Modify only these three columns:
  - `Segments` column `BT`
  - `IS` column `BO`
  - `BS & CFS` column `BB`
- Use only the attached 3Q25 10-Q (`input-2.pdf`) as the source of actuals
- Keep units consistent with the model (values are in USD millions unless the
  model indicates otherwise)
- Ensure the balance sheet balances for 3Q25 after the update

## Negative Constraints

- DO NOT add or delete rows/columns
- DO NOT change the model’s layout or existing historical periods
- DO NOT hard-code values that should be formula-driven outside the 3Q25 column
- DO NOT fabricate numbers; use only values supported by the 10-Q
- NO conversational filler

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the 3Q25 columns in the sheets listed above.

**2. JSON Summary**: After updating the model, provide your response as a raw
JSON object with the following keys. Do not include any markdown formatting,
backticks, or preamble.

`{   "reasoning_steps": [     "Step 1: How you found the relevant numbers in the 10-Q",     "Step 2: How you mapped them into the model",     "Step 3: How you verified the model ties"   ],   "segments_total_revenue_bt150": "Value in Segments!BT150 after update",   "segments_mis_revenue_bt31": "Value in Segments!BT31 after update",   "segments_ma_revenue_bt95": "Value in Segments!BT95 after update",   "is_net_income_bo62": "Value in IS!BO62 after update",   "is_interest_expense_net_bo54": "Value in IS!BO54 after update",   "bs_cash_bb10": "Value in BS & CFS!BB10 after update",   "bs_total_assets_bb21": "Value in BS & CFS!BB21 after update",   "bs_total_debt_bb31": "Value in BS & CFS!BB31 after update",   "bs_total_liabilities_bb36": "Value in BS & CFS!BB36 after update",   "bs_total_equity_bb38": "Value in BS & CFS!BB38 after update",   "bs_balance_sheet_ties": "true if BS & CFS!BB39 equals BS & CFS!BB21, else false",   "formatting_segments": "Optional: leave blank (scored from Excel file formatting)",   "formatting_is": "Optional: leave blank (scored from Excel file formatting)",   "formatting_bs_cfs": "Optional: leave blank (scored from Excel file formatting)" }`
