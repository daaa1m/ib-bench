## Task

You are an investment banking analyst tasked with auditing a quarterly financial
model that contains date/period alignment errors. The fiscal quarters in the
model do not match correctly, causing data misalignment issues that will lead to
incorrect analysis.

Your goal is to identify the specific location(s) where period labels or formula
references are misaligned and provide the corrected values.

## Methodology & Process

To diagnose the period alignment error, apply the following systematic checks:

1. **Period Label Audit:** Review all quarter labels (Q1, Q2, Q3, Q4) and fiscal
   year indicators. Verify that labels follow a consistent sequential pattern
   and align with the data they represent.

2. **Cross-Reference Validation:** Verify that quarterly data sums to annual
   totals. If Q1+Q2+Q3+Q4 does not equal the annual figure, this indicates a
   potential misalignment.

3. **Formula Reference Check:** Examine formulas that reference specific periods.
   Ensure cell references point to the correct quarter columns and that relative
   vs. absolute references are used appropriately.

4. **Timeline Consistency:** Verify that date headers progress chronologically
   and that no quarters are duplicated or skipped.

5. **Year Boundary Check:** Pay special attention to fiscal year transitions
   where Q4 of one year meets Q1 of the next. This is a common location for
   alignment errors.

## Constraints & Negative Constraints

Constraints:
- Identify the exact cell(s) or row(s) containing the misalignment
- Provide both the current incorrect value/formula and the corrected version
- Explain the nature of the period alignment error

Negative Constraints:
- DO NOT restructure the entire model
- DO NOT add new columns or rows
- DO NOT modify data values that are not part of the alignment fix
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "error_location": "The specific cell reference(s) or row(s) where the misalignment occurs",
  "current_value": "The current incorrect period label or formula",
  "corrected_value": "The corrected period label or formula",
  "quarterly_sum_check": "Verification that quarterly data sums to annual totals (PASS/FAIL with details)",
  "explanation": "A concise explanation of the period alignment error and why the fix resolves it"
}`
