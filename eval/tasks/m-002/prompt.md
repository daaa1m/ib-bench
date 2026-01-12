## Task

You are an investment banking analyst responsible for maintaining financial
models. Your task is to update the Kirby Corporation (NYSE: KEX) financial model
with 2Q24 quarterly data.

You are given an Excel model (`input.xlsx`) containing the existing DCF
valuation with one sheet: **Model Shell** which has operating model with
historical and projected financials.

You must source the 2Q24 data yourself from Kirby Corp's SEC filings (10-Q) and
company reports for the Marine Transportation segment.

## Methodology & Process

1. **Source the 2Q24 data** from SEC EDGAR or Kirby Corp investor relations:
   - Find the 2Q24 10-Q filing for Kirby Corporation
   - Identify Marine Transportation segment figures for 2Q24 from other official
     data sources

2. **Update the Model Shell** with 2Q24 data:
   - Update the 2Q24 column (column AQ) with actual figures
   - Update the LQA (Last Quarter Annualised) column to reflect 2Q24
   - Preserve all existing formulas and model structure

3. **Validate the model**:
   - Confirm Total Assets (row 60) equals Total Liabilities & Equity (row 83)
   - Verify no #REF or other formula errors exist
   - Ensure all formulas remain intact

## Constraints

- Update ONLY cells that need new data values in column AQ and G
- Preserve all existing formulas and model structure
- Use values exactly as reported in SEC filings

## Negative Constraints

- DO NOT change the structure or layout of the sheet
- DO NOT modify formulas only update hard-coded input values or empty space
- DO NOT add or delete rows or columns
- DO NOT use manual "plugs" or hard-codes to force the model to balance
- NO conversational filler

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to the Marine DCF sheet.

2. **JSON Summary**: Provide your response as a raw JSON object with the
   following keys. Do not include any markdown formatting, backticks, or
   preamble.

```json
{
  "reasoning_steps": "Step-by-step explanation of how you sourced and updated the data",
  "lqa_label": "The value you set in cell G2",
  "aq31_value": "The value in cell AQ31 after update",
  "aq60_value": "Total Assets value in AQ60",
  "aq83_value": "Total L&SE value in AQ83",
  "aq93_value": "The value in cell AQ93 after update",
  "aq112_value": "The value in cell AQ112 after update",
  "model_balanced": true
}
```
