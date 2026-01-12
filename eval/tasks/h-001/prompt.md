## Task

You are an investment banking analyst tasked with updating an outdated WildBrain
financial model. The model is three years out of date and uses legacy revenue
segmentation. You must update the model to the new segmentation and refresh the
latest three years of data while keeping the model consistent and balanced.

You are provided with `input.xlsx`. Update all sheets except `Reference` and
return the updated workbook plus a JSON summary.

## Methodology & Process

1. Obtain the consolidated financial statements for FY25, FY24 and FY23.
2. Update the `Quarterly` sheet with the refreshed three-year data.
3. Update `RevBuild Calcs`, `FS Calcs`, and `Debt Calcs` so the new segmentation
   flows through the model correctly.
4. Roll the updates through `P&L` and `BS & CFS`, ensuring the statements tie.
5. Update `Output` and `Summary` to reflect the refreshed model results.
6. Make reasonable assumptions for the model whenever necessary.

## Constraints and Negative Constraints

Constraints:

- Use headless LibreOffice to recalculate the workbook; do not rely on
  calculations outside the spreadsheet.
- Update all sheets except `Reference` (do not edit `Reference`).
- Preserve the existing structure, headers, and formulas unless the update
  requires a formula change for new segmentation.
- Ensure the model balances and check lines reconcile after updates.

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

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to every sheet except `Reference`.

**2. JSON Summary**: Provide your response as a raw JSON object with the
following keys. Do not include any markdown formatting, backticks, or preamble.

```json
{
  "quarterly_updates": "Summary of the three-year quarterly data updates",
  "revbuild_segmentation_updates": "How the new segmentation was applied in RevBuild Calcs",
  "financial_statements_updates": "How P&L and BS & CFS were updated to reflect the new segmentation",
  "output_summary_updates": "Key Output and Summary sheet changes",
  "model_integrity_checks": "How you verified the model ties and reconciles",
  "reasoning_steps": [
    "Step 1: How you mapped the new segmentation",
    "Step 2: How you validated the updated model"
  ]
}
```
