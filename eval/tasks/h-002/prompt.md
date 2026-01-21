## Task

You are an investment banking analyst asked to build an LBO model and investment
assessment for Albertsons using the provided template. You are given
`input.xlsx` with two sheets: `Operating Model` and `Business Assessment`. The
file is only a structural template and the data inside is not related to
Albertsons. It contains example numbers and narrative content for a different
company—replace all of it with Albertsons-specific data and analysis. Use the
layout as a blueprint and produce a new Excel file populated entirely with
Albertsons data.

Populate the last three fiscal years of historicals, build projections and
returns in the Operating Model, and complete the Business Assessment with a
clear recommendation and rationale.

Your deliverable includes the completed Excel model and a JSON summary.

## Methodology & Process

1. Gather the last three fiscal years of Albertsons financials from public
   filings and investor materials.
2. Use the template layout to create a new workbook and populate historical
   inputs in the `Operating Model` sheet, including entry assumptions and KPI
   drivers.
3. Build revenue and cost drivers, projections, and the debt schedule.
4. Apply entry assumptions, compute returns (IRR/MOIC), and check model ties.
5. Replace the example content in `Business Assessment` with Albertsons-specific
   market position, risks, and a go/no-go recommendation.

## Constraints and Negative Constraints

Constraints:

- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Use headless LibreOffice to recalculate the workbook; do not rely on
  calculations outside the spreadsheet.
- Treat `input.xlsx` as a template only; do not reuse its numbers as data.
- Create a new workbook based on the template and populate all values with
  Albertsons data, replacing all sample text.
- Update only the `Operating Model` and `Business Assessment` sheets.
- Preserve the template structure, headers, and formulas unless the new inputs
  require formula updates.
- Ensure the model ties and the output is sense-checked.

Negative Constraints:

- DO NOT hard-code plugs to force the model to balance.
- DO NOT change the layout or sheet order.
- NO conversational filler.

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify and
follow the existing model formatting style:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. New Excel File**: Save and return a new Excel workbook based on the
`input.xlsx` template with Albertsons data populated in the `Operating Model`
and `Business Assessment` sheets.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

```json
{
  "historical_updates": "Summary of the three-year historicals you populated and key sources used",
  "assumptions_summary": "Key entry, leverage, and projection assumptions",
  "returns_summary": "IRR/MOIC and exit assumptions from the model",
  "business_assessment": "Market position, strengths, weaknesses, risks, and competitive landscape",
  "recommendation": "Go/No-Go recommendation with rationale and next steps",
  "model_integrity_checks": "How you verified the model ties and reconciles",
  "formatting": "How you ensured IB formatting conventions were applied",
  "reasoning_steps": [
    "Step 1: How you mapped and validated historicals",
    "Step 2: How you built projections and returns"
  ]
}
```
