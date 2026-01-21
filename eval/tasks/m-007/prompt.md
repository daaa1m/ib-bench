## Task

You are an investment banking analyst tasked with completing a management return
analysis for a leveraged buyout. You are given an LBO model for Dave and
Buster's with a partially completed Mgmt Return Analysis sheet.

Your deliverable is to complete the management return sensitivity analysis that
shows how management proceeds vary across different exit multiples, accounting
for their sweet equity participation.

You must return the completed Excel workbook.

## Methodology & Process

1. Review the LBO sheet to extract key inputs for FY26 exit:
   - LTM Adjusted EBITDA
   - Net Debt
   - Entry equity value (Sponsor + Management investment)
   - Management sweet equity percentage

2. Build the exit analysis for multiples 15x to 19x in 0.5x increments:
   - Exit Enterprise Value = LTM EBITDA × Exit Multiple
   - Exit Equity Value = Exit EV - Net Debt

3. Implement the sweet equity hurdle logic:
   - Hurdle is 200% meaning exit equity must be at least 3x entry equity
   - If hurdle is met: Mgmt earns their sweet equity pot on the gain
   - If hurdle is not met: Mgmt receives only their rollover investment value

4. Calculate management equity value at exit for each multiple

## Constraints

- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Use FY26 as the exit year
- Exit multiple range: 15.0x to 19.0x in 0.5x increments (9 scenarios)
- Sweet equity hurdle: 200% (exit equity >= 3x entry equity)
- Use the model's circularity toggle setting
- All values in millions USD
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.

## Negative Constraints

- DO NOT modify the LBO sheet
- DO NOT change entry assumptions or capital structure
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
changes applied to the Mgmt Return Analysis sheet, following the formatting conventions above.

**2. JSON Summary**: After implementing changes, provide your response as a raw
JSON object with the following keys. Do not include any markdown formatting,
backticks, or preamble.

```json
{
  "mgmt_equity_15x": "Management equity value at exit for 15.0x multiple",
  "mgmt_equity_15_5x": "Management equity value at exit for 15.5x multiple",
  "mgmt_equity_16x": "Management equity value at exit for 16.0x multiple",
  "mgmt_equity_16_5x": "Management equity value at exit for 16.5x multiple",
  "mgmt_equity_17x": "Management equity value at exit for 17.0x multiple",
  "mgmt_equity_17_5x": "Management equity value at exit for 17.5x multiple",
  "mgmt_equity_18x": "Management equity value at exit for 18.0x multiple",
  "mgmt_equity_18_5x": "Management equity value at exit for 18.5x multiple",
  "mgmt_equity_19x": "Management equity value at exit for 19.0x multiple"
}
```
