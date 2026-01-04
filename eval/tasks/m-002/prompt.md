## Task

You are an investment banking analyst responsible for maintaining financial
models. Your task is to update the Kirby Corporation (NYSE: KEX) DCF model with
the latest quarterly and annual financial data from the provided SEC filing.

You are given:

1. An Excel model (`input.xlsx`) containing the existing DCF valuation
2. A PDF with the latest SEC filing data to use for updates

The model has two key sheets:

- **Model Shell**: Operating model with historical and projected financials
- **Marine DCF**: DCF valuation for the Marine Transportation segment

## Methodology & Process

1. **Review the SEC filing** to identify the latest reported figures for:
   - Revenue (Inland and Coastal)
   - EBIT and EBITDA
   - D&A (Depreciation & Amortization)
   - Any updated guidance or projections

2. **Update the Model Shell** with new historical data:
   - Input actual figures for the most recent completed periods
   - Preserve all existing formulas and model structure
   - Do not modify projection assumptions unless filing provides new guidance

3. **Update the Marine DCF** sheet:
   - Ensure updated actuals flow through to the DCF
   - Verify cash flow calculations reflect new data
   - Check that TEV calculation in E27 updates correctly

4. **Validate the model**:
   - Confirm balance sheet check (row 84 of Model Shell) shows "OK"
   - Verify no #REF or other formula errors exist
   - Ensure all formulas remain intact

## Constraints

- Update ONLY cells that need new data values
- Preserve all existing formulas and model structure
- Maintain consistent formatting with existing cells
- Use values exactly as reported in the SEC filing

## Negative Constraints

- DO NOT change the structure or layout of any sheet
- DO NOT modify formulas - only update hard-coded input values
- DO NOT add or delete rows or columns
- DO NOT change projection assumptions unless explicitly stated in filing
- NO conversational filler or unnecessary commentary

## Output Format

Return your analysis as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```json
{
  "reasoning_steps": "Step-by-step explanation of how you identified and updated each value",
  "changes_made": [
    {
      "cell": "Sheet!Cell",
      "old_value": "X",
      "new_value": "Y",
      "source": "Filing reference"
    }
  ],
  "model_balanced": true,
  "cell_value_E27": "Updated TEV value from Marine DCF E27"
}
```

Also return the updated Excel file with all changes applied.
