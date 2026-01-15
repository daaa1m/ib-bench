## Task

You are an investment banking analyst evaluating whether to invest alongside an activist in Phillips 66. You are given an activist presentation in `input.pdf`. You must use the presentation plus FY24 10-K and FY25 Q1/Q2/Q3 10-Q filings to build a three-statement financial model, incorporate the activist value-creation drivers, run a returns analysis, and deliver a clear invest / pass recommendation.

Your deliverable includes the completed Excel model and a JSON summary.

## Methodology & Process

1. Review `input.pdf` to identify the activist’s specific value-creation drivers and targets.
2. Pull FY24 10-K and FY25 Q1/Q2/Q3 10-Q financials for Phillips 66 and reconcile key historical line items.
3. Build a three-statement model (Income Statement, Balance Sheet, Cash Flow) with assumptions that bridge history to projections.
4. Model the activist drivers explicitly (portfolio simplification, refining performance, cost actions, capital return) and reflect their expected impacts in projections.
5. Run a returns analysis (base, upside, downside) and translate it into an IC-ready recommendation.

## Constraints and Negative Constraints

Constraints:
- Use only `input.pdf` and Phillips 66 public filings (FY24 10-K, FY25 Q1/Q2/Q3 10-Qs).
- Clearly state units and timeframes (e.g., USD millions, FY24A, FY25E).
- Create a new Excel workbook with these sheets: `Summary`, `Income Statement`, `Balance Sheet`, `Cash Flow`, `Assumptions`, `Returns`.
- Ensure the three statements tie and the model is internally consistent.
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.

Negative Constraints:
- DO NOT use any sources beyond the deck and filings.
- DO NOT fabricate figures or targets not supported by sources.
- DO NOT omit a clear recommendation.
- NO conversational filler.

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. New Excel File**: Save and return a new Excel workbook containing the model and analysis, following the formatting conventions above.

**2. JSON Summary**: Provide your response as a raw JSON object with the following keys. Do not include any markdown formatting, backticks, or preamble.

```json
{
  "data_sources": "Specific filings and deck slides used, with page/section references",
  "model_structure": "How the three statements are structured and how the model ties",
  "historicals_summary": "Key FY24A and FY25 YTD historicals used to anchor projections",
  "value_creation_drivers": [
    {
      "driver": "Name of driver",
      "mechanism": "How it affects financials",
      "assumptions": "Key quantitative assumptions",
      "evidence": "Deck or filing citation"
    }
  ],
  "projection_highlights": "Main FY25E–FY27E projection takeaways (revenue, EBITDA, FCF, leverage)",
  "returns_analysis": {
    "entry_valuation": "Entry multiple or valuation framework",
    "base_case": "IRR/MOIC or return metrics",
    "upside_case": "IRR/MOIC or return metrics",
    "downside_case": "IRR/MOIC or return metrics",
    "key_sensitivities": ["Sensitivity 1", "Sensitivity 2"]
  },
  "investment_recommendation": {
    "recommendation": "Invest/Pass/Conditional",
    "rationale": "Concise IC-ready rationale tied to model outputs",
    "conditions_to_invest": ["Condition 1", "Condition 2"]
  },
  "risks_and_sensitivities": [
    {
      "risk": "Key risk",
      "impact": "How it impacts thesis",
      "signpost": "What you would monitor"
    }
  ],
  "reasoning_steps": [
    "Step 1: How you reconciled historicals",
    "Step 2: How you translated activist drivers into projections",
    "Step 3: How you translated projections into returns and recommendation"
  ]
}
```
