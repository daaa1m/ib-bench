## Task

You are an investment banking analyst responsible for updating a DCF valuation
model. Your task is to update the Marine DCF sheet with FY2024 values and
recalculate the DCF valuation.

You are given an Excel model (`input.xlsx`) containing a Kirby Corporation
valuation. Focus exclusively on the **Marine DCF** sheet for editing.

## Methodology & Process

1. **Identify the LQA (Last Quarter Annualized) values** in the Model Shell
   sheet that represent the most annualised performance data

2. **Update FY2024 column** with the LQA values to reflect annualised FY2024
   performance

3. **Recalculate the DCF** with 2025 as the first projection year (the DCF
   should now value future cash flows starting from 2025)

4. **Verify the model** recalculates correctly with no formula errors

## Constraints

- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Edit ONLY the Marine DCF sheet
- Preserve all existing assumptions (discount rate, terminal growth, etc.)
- Preserve the model structure
- Use LQA values as the basis for FY2024 actuals
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.

## Negative Constraints

- DO NOT change any valuation assumptions
- DO NOT modify other sheets in the workbook
- DO NOT add or delete rows or columns
- DO NOT hard-code values that should be formula-driven
- NO conversational filler

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the Marine DCF sheet, following the formatting conventions above.

**2. JSON Summary**: After implementing changes, provide your response as a raw
JSON object with the following keys. Do not include any markdown formatting,
backticks, or preamble.

```json
{
  "reasoning_steps": "Brief explanation of how you identified and applied the LQA values",
  "k8_value": "Value in cell K8 after update",
  "l2_value": "Value in cell L2 after update",
  "k17_value": "Value in cell K17 after update",
  "k20_value": "Value in cell K20 after update",
  "e27_value": "Value in cell E27 (DCF result)"
}
```
