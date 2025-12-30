## Task

You are an investment banking analyst tasked with auditing a simple, integrated
LBO model for 'Dave & Buster’s' that is currently broken. Specifically, the
Balance Sheet does not tie (Total Assets ≠ Total Liabilities + Equity) in
row 123.

A preliminary review suggests the discrepancy originates from an error in the
Balance Sheet or the Cash Flow Statement. Your goal is to identify the specific
row causing the imbalance and provide a structural fix. There is exactly one
source of error causing this model to be unbalanced.

## Methodology & Process

To diagnose the error, apply the following systematic accounting checks:

1. **Circularity Control:** Treat the model as having embedded circularity.
   Mentally isolate the iterative loops to identify if the error is a static
   linkage or a logic flow issue.
2. **Variance Analysis:** - Identify the "Break Year": Audit the model from left
   to right. Focus your diagnostic energy entirely on the first year where the
   check row is non-zero.
   - Evaluate the Error Behavior: Determine if the variance is a constant value
     (suggesting an Opening Balance or hard-code error) or a variable/growing
     value (suggesting a flaw in the Cash Flow Statement flow or a Schedule
     linkage).
3. **The "Half-Number" Sign Check:** If the variance is a specific dollar
   amount, scan for half of that amount in the model. A sign-convention flip
   (adding an outflow instead of subtracting) results in a variance double the
   original value.
4. **Linkage Integrity:**
   - Perform an audit on summation ranges for Total Assets and Total Liabilities
     & Equity to ensure all line items are captured.
   - Confirm the "Golden Rule": Ensure every period-to-period change (Delta) in
     non-cash assets and liabilities on the Balance Sheet is reflected exactly
     once on the Cash Flow Statement.
   - Verify the Cash Link: Ensure the Ending Cash from the CFS is the exact cell
     linked to the Balance Sheet.

### Constraints & Negative Constraints

- DO NOT use manual "plugs" or hard-codes to force the model to balance.
- DO NOT make changes to the Transaction Dashboard, Operating Assumptions, or
  Returns Analysis sections.
- NO conversational filler.

### Output Format

Provide your findings in a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{   "error_location": "The specific Cell or Row ID",   "current_formula": "The exact formula found in the sheet",   "corrected_formula": "The corrected Excel formula",   "logical_explanation": "A concise explanation of the accounting error",   "audit_steps_followed": ["Step 1", "Step 2", "List of diagnostic steps used from the instructions"] }`
