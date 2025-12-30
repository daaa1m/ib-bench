## Task

You are an investment banking analyst tasked with auditing a cash flow model
that contains an error in the Net Working Capital (NWC) calculation. The model
currently produces incorrect Free Cash Flow figures due to an NWC formula error
involving wrong signs, missing components, or incorrect period referencing.

Your goal is to identify the specific cell(s) containing the NWC error and
provide a corrected formula that properly reflects working capital mechanics.

## Methodology & Process

To diagnose the NWC error, apply the following systematic checks:

1. **Identify the NWC Calculation Section:** Locate where Change in NWC flows
   into the Cash Flow Statement or FCF calculation.

2. **Verify Sign Convention:** Remember the fundamental rule:
   - Increase in Current Assets (e.g., AR, Inventory) = Cash Outflow (negative)
   - Decrease in Current Assets = Cash Inflow (positive)
   - Increase in Current Liabilities (e.g., AP) = Cash Inflow (positive)
   - Decrease in Current Liabilities = Cash Outflow (negative)

3. **Check Period Referencing:** Ensure the formula calculates the change
   correctly (Current Period - Prior Period) and is applied consistently.

4. **Component Verification:** Confirm all relevant NWC components are included:
   - Accounts Receivable
   - Inventory
   - Prepaid Expenses (if applicable)
   - Accounts Payable
   - Accrued Liabilities (if applicable)

5. **Trace the Impact:** Verify how the NWC change flows through to FCF and
   confirm the correction resolves any downstream calculation errors.

## Constraints & Negative Constraints

Constraints:
- Focus exclusively on the NWC calculation error
- Provide the exact cell reference(s) where the error occurs
- Your corrected formula must use proper Excel syntax

Negative Constraints:
- DO NOT modify any cells outside the NWC calculation
- DO NOT change the structure or layout of the model
- DO NOT use hard-coded values to fix the formula
- NO conversational filler

## Output Format

Provide your findings as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{ "error_location": "The specific Cell or Row ID containing the NWC error", "current_formula": "The exact formula currently in the cell", "corrected_formula": "The corrected Excel formula with proper NWC mechanics", "explanation": "A concise explanation of what was wrong and why the fix is correct" }`
