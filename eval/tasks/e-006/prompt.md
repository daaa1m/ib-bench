## Task

You are an investment banking analyst tasked with enhancing an LBO model to
properly handle interest expense circularity.

The provided model currently calculates interest expense using only the
beginning-of-period debt balance. This is a simplification that ignores the
circular relationship between interest expense, net income, cash flow, and debt
paydown. Your task is to:

1. **Modify the interest expense calculation** to use the average of beginning
   and ending period debt balances
2. **Add a circularity switch** that allows users to toggle circularity on/off
   to prevent Excel from entering an infinite calculation loop

## Background: Interest Expense Circularity

In integrated financial models, interest expense creates a circular reference:
- Interest expense affects Net Income
- Net Income affects Cash Flow Available for Debt Repayment
- Debt Repayment affects Ending Debt Balance
- Ending Debt Balance affects Interest Expense (circular)

The standard solution is to:
1. Calculate interest on the average of beginning and ending debt
2. Include a toggle switch (typically 1 = circular on, 0 = circular off)
3. Use an IF statement: `=IF(CircSwitch, AverageDebtCalc, BeginningDebtCalc)`

## Methodology & Process

1. **Locate the Interest Expense row** in the model
2. **Identify the Debt Schedule** and note the beginning/ending debt balance
   rows
3. **Create a Circularity Switch cell** in an assumptions or controls area,
   labeled clearly (e.g., "Circ Switch" with value 1 or 0)
4. **Modify the Interest Expense formula** to:
   - When switch = 1: Interest = Rate × (Beginning Debt + Ending Debt) / 2
   - When switch = 0: Interest = Rate × Beginning Debt (original behavior)
5. **Enable iterative calculations** - note this in your response
6. **Verify the model still balances** after changes

## Constraints and Negative Constraints

Constraints:
- The circularity switch must be clearly labeled and easy to find
- Interest calculation must use AVERAGE or (Begin + End) / 2 formula structure
- Preserve all existing model functionality

Negative Constraints:
- DO NOT hard-code any values
- DO NOT delete or overwrite other model components
- DO NOT change the debt amortization schedule logic
- NO conversational filler

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the modified Excel workbook with
circularity implemented, circularity switch turned ON, and IB formatting conventions applied.

**2. JSON Summary**: After implementing changes, report the Total Cash Interest
values from row 164 (with circularity ON). Provide as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

`{
  "K164": "Total Cash Interest value in cell K164 (rounded to nearest integer)",
  "L164": "Total Cash Interest value in cell L164 (rounded to nearest integer)",
  "M164": "Total Cash Interest value in cell M164 (rounded to nearest integer)",
  "N164": "Total Cash Interest value in cell N164 (rounded to nearest integer)",
  "O164": "Total Cash Interest value in cell O164 (rounded to nearest integer)",
  "implementation_notes": "Brief explanation of changes made"
}`
