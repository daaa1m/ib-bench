## Task

You are a private equity analyst completing a modelling test. Your task is to
build a functional LBO model from scratch to evaluate a potential investment in
Reverse Logistics Group (RLG).

You are provided with `input.xlsx` containing RLG's historical financial data.

## Company Background

RLG is a reverse logistics provider operating across multiple geographies:
- **Europe AMS** (Asset Management Services)
- **Europe ECS** (End-of-life Consumer Services)
- **Americas**
- **Asia**

The analysis is set in July 2020. Use 2020 estimated financials as your base year.

## Required Deliverables

Build a complete LBO model including all of the following:

### 1. Operating Forecast
5-year annual financial forecast (2021-2025) with:
- Revenue projections by segment using these growth assumptions:
  - Europe AMS: ~7% CAGR
  - Europe ECS: ~5% CAGR
  - Americas and Asia: Expected to significantly outpace European growth
- Cost of Sales (variable): Transportation, labels, 3rd party contracting - model
  based on volume and price per kg
- Operating Expenses (fixed/semi-fixed): Personnel costs, and other costs (rent,
  IT, marketing, legal, etc.)

### 2. Valuation & EV-to-Equity Bridge
- Proposed entry valuation with clear EV/EBITDA multiple assumption
- Complete bridge from Enterprise Value to Equity Value
- Clear breakdown of all adjustments (debt, cash, other items)

### 3. Sources & Uses
- Transaction structure table showing all sources of funding
- Appropriate levels of third-party debt financing
- Equity contribution from sponsor
- Transaction fees and expenses
- Sources must equal Uses

### 4. Returns Calculation
- Multiple on Invested Capital (MOIC)
- Internal Rate of Return (IRR)
- Assume exit in Year 5 (end of 2025)
- Show exit equity value calculation

### 5. Return Sensitivities
Two different sensitivity tables showing impact on IRR, such as:
- Entry multiple vs Exit multiple
- Revenue growth vs EBITDA margin
- Leverage vs Exit multiple

### 6. Investment Evaluation
Brief bullet-point answers addressing:
1. What price would you pay and why?
2. What proceeds do you expect shareholders to receive at exit?
3. How did you construct your operating assumptions?
4. What financing structure would you propose given market conditions?
5. What exit multiple is appropriate and why?

## Constraints

- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Use only the provided Excel file as your data source
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.
- Base year is 2020, first projection year is 2021
- Assume exit at end of Year 5 (2025)
- Model must be functional with working formulas
- All outputs should be formula-driven, not hard-coded

## Negative Constraints

- DO NOT use external data sources beyond the input file
- DO NOT hard-code values that should be formula-driven
- DO NOT leave incomplete sections
- NO conversational filler

## Formatting Requirements

Apply standard IB Excel formatting conventions throughout the model:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Completed Excel Model**: Save and return the completed LBO model workbook
with all required components (forecast, valuation, S&U, returns, sensitivities),
following the formatting conventions above.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

```json
{
  "entry_ev_multiple": "Your proposed entry EV/EBITDA multiple",
  "entry_equity_value": "Total equity investment required (in millions)",
  "exit_ev_multiple": "Assumed exit EV/EBITDA multiple",
  "irr": "Calculated IRR percentage",
  "moic": "Calculated MOIC",
  "revenue_2025": "Projected 2025 revenue (in millions)",
  "ebitda_2025": "Projected 2025 EBITDA (in millions)",
  "investment_thesis": "2-3 sentence summary of why this is/isn't an attractive investment"
}
```
