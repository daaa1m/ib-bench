## Task

You are an investment banking analyst tasked with auditing the EuropeCo LBO
model before it goes to the Investment Committee. The model has been flagged as
containing errors after a preliminary review showed returns appear incorrect.

Your task is to find and fix all errors in the model - it is likely that there
are 2-3 errors. The MOIC currently shows approximately 1.0x which is clearly
wrong given the model assumptions.

You must return the corrected Excel workbook.

## Methodology & Process

1. Start with the Returns section to understand the magnitude of errors
2. Trace backwards through the model to find root causes
3. Check the Cash Flow Statement for completeness
4. Verify the Debt Schedule calculations
5. Ensure that the Returns look reasonable and realistic

Apply these systematic checks:

- Verify debt balances roll forward correctly
- Check that all cash flow items are captured
- Ensure net debt calculation is correct for exit equity
- Verify MOIC formula references correct values

## Constraints

- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Provide specific cell references for each error location
- Fix the model so it calculates correctly
- All values in millions EUR
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.

## Negative Constraints

- DO NOT flag stylistic issues as errors
- DO NOT flag rounding differences as errors
- DO NOT fix errors by hard-coding values
- DO NOT modify model structure
- NO conversational filler

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the corrected Excel workbook with
all errors fixed and IB formatting conventions applied.

**2. JSON Summary**: After fixing the model, provide your response as a raw JSON
object with the following keys. Do not include any markdown formatting,
backticks, or preamble.

```json
{
  "reasoning_steps": "Brief explanation of how you identified the errors",
  "error_1_location": "Cell or range where first error was found",
  "error_1_fix": "Description of what was wrong and how you fixed it",
  "error_2_location": "Cell or range where second error was found",
  "error_2_fix": "Description of what was wrong and how you fixed it",
  "error_3_location": "Cell or range where third error was found",
  "error_3_fix": "Description of what was wrong and how you fixed it",
  "l166_moic": "Value in cell L166 (MOIC) after fixes",
  "l156_eop_cash": "Value in cell L156 (EoP cash) after fixes",
  "l164_exit_equity": "Value in cell L164 (Exit equity) after fixes"
}
```
