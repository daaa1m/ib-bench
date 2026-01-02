## Task

You are an investment banking analyst tasked with auditing an integrated LBO
model that contains multiple errors. The Balance Sheet does not tie, indicating
structural problems in the model.

Your goal is to identify ALL errors in the model and provide fixes for each.
There is more than one error causing the model to break.

## Methodology & Process

To diagnose the errors, apply the following systematic audit approach:

1. **Identify the Break:** Start with the Balance Sheet check row. Determine
   which year(s) show a discrepancy between Total Assets and Total Liabilities +
   Equity.

2. **Trace Cash Flow Statement:** For each period with a break, verify that all
   Balance Sheet movements are properly reflected in the Cash Flow Statement.
   Check Operating, Investing, and Financing sections.

3. **Audit Supporting Schedules:** Review calculations in supporting sheets
   (e.g., "FS Calcs") that feed into the main financial statements. Look for
   hard-coded values or broken references.

4. **Cross-Reference Linkages:** Ensure all line items sum correctly and
   reference the appropriate source cells. Check for missing or incorrect cell
   references in summation formulas.

5. **Validate Final Output:** After identifying all errors, verify that fixing
   them results in the model balancing correctly.

## Constraints & Negative Constraints

Constraints:

- Identify ALL errors, not just the first one found
- Provide specific cell or row references for each error
- Explain what is wrong and how to fix it

Negative Constraints:

- DO NOT use manual plugs or hard-codes to force the model to balance
- DO NOT stop after finding the first error
- DO NOT modify transaction assumptions or returns analysis
- NO conversational filler

## Output Format

Provide your findings as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{ "errors_found": [ { "location": "Cell or Row reference (e.g., 'K32 in FS Calcs' or 'Row 64 in BS & CFS')", "issue": "Description of what is wrong", "fix": "The correction needed" } ], "final_long_term_debt_2024E": "The 2024E Long Term Debt value (K29 in BS & CFS sheet) after all fixes are applied", "audit_methodology": "Brief description of the audit steps you followed" }`
