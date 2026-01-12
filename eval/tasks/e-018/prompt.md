## Task

You are an investment banking analyst tasked with fixing a broken 3-statement
model. The Balance Sheet does not tie because of a formula error in the cash flow
linkages. Your job is to identify the error, correct it, and explain the fix.

You are provided with `input.xlsx` (the model). Your deliverable includes the
corrected Excel model and a JSON summary.

## Methodology & Process

1. Identify the first period where the balance sheet check fails.
2. Trace the cash flow statement linkages, focusing on working capital changes.
3. Locate the incorrect formula and determine the correct sign/structure.
4. Fix the formula and confirm the balance sheet ties.

## Constraints and Negative Constraints

Constraints:
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.
- Modify only the `BS & CFS` sheet in `input.xlsx`.
- Correct the formula error without changing the model structure.
- Preserve existing formulas and references outside the fix.

Negative Constraints:
- DO NOT hard-code plugs to force the balance sheet to tie.
- DO NOT change assumptions or unrelated lines.
- NO conversational filler.

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the `BS & CFS` sheet.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

`{
  "error_location": "Cell or row reference where the formula is wrong",
  "current_formula": "The incorrect formula currently in the model",
  "corrected_formula": "The corrected formula you applied",
  "explanation": "Why the sign/structure was wrong and how the fix resolves it",
  "reasoning_steps": [
    "Step 1: How you found the break",
    "Step 2: How you validated the corrected linkage"
  ]
}`
