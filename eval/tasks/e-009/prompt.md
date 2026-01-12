## Task

You are an investment banking analyst tasked with extracting all key assumptions
from an LBO (Leveraged Buyout) model. Your goal is to identify and extract the
driver cells containing hard-coded assumptions, distinguishing them from
calculated or linked cells.

The attached Excel file contains a complete LBO model. Extract all key
transaction and operating assumptions that drive the model outputs.

## Methodology & Process

1. **Navigate the Model Structure:** Identify the main sections of the LBO model
   (Transaction Assumptions, Sources & Uses, Operating Model, Debt Schedule,
   Returns Analysis)
2. **Identify Assumption Cells:** Look for cells containing hard-coded values
   (blue font or input cells) vs. formulas. Focus on cells that are inputs to
   the model, not calculated outputs
3. **Extract Transaction Assumptions:** Find entry valuation metrics (purchase
   price, entry multiple), exit assumptions (exit multiple, hold period), and
   transaction costs
4. **Extract Financing Assumptions:** Identify debt tranches, amounts, interest
   rates, amortization schedules, and any equity contribution
5. **Extract Operating Assumptions:** Find revenue growth rates, margin
   assumptions, working capital assumptions, and capex assumptions
6. **Verify Cell References:** Confirm each value is a true assumption (input)
   by checking that it is not a formula referencing other cells

## Constraints and Negative Constraints

Constraints:

- Report all monetary values in the same unit as the model (typically millions)
- Include cell references where assumptions are located
- Distinguish between assumption inputs and calculated values
- Report interest rates and growth rates as percentages

Negative Constraints:

- DO NOT include calculated outputs (IRR, MOIC, etc.) as assumptions
- DO NOT include values that are formulas or links to other cells
- DO NOT confuse historical data with forward-looking assumptions
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```json
{
  "entry_multiple": "Entry EV/EBITDA multiple on forward basis, i.e., EV / FY22 EBITDA (numeric value only)",
  "exit_multiple": "Exit EV/EBITDA multiple (numeric value only)",
  "hold_period_years": "Investment holding period in years (integer)",
  "senior_debt_rate": "Senior debt interest rate as percentage (e.g., '8.0%')",
  "revenue_growth_rate": "Revenue growth rate assumption as percentage (e.g., '5.0%')",
  "assumptions_summary": "Brief summary of methodology used to identify assumptions vs calculated cells"
}
```
