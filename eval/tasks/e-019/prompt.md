## Task

You are an investment banking analyst reviewing AMC Entertainment’s high-yield
bond indenture. Your task is to extract the key covenant terms from the
agreement provided in `input.pdf`.

Focus on the following sections:
- Debt Incurrence (Section 4.05)
- Restricted Payments (Section 4.06)
- Asset Sales (Section 4.16)
- Change of Control (Section 4.11)
- Liens & Other Covenants (Sections 4.07–4.10)

## Methodology & Process

1. Read the specified covenant sections in the indenture.
2. Extract ratio tests, basket sizes, thresholds, and timing requirements.
3. Note any “greater of” basket mechanics and required conditions (e.g., no EoD).
4. Summarize each section in a concise, structured format.

## Constraints and Negative Constraints

Constraints:
- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Use only the information contained in `input.pdf`.
- Provide specific numeric thresholds and formulas when stated.
- Use precise covenant terminology (e.g., “Total Leverage Ratio”).

Negative Constraints:
- DO NOT speculate or fill gaps with assumptions.
- DO NOT include unrelated boilerplate provisions.
- NO conversational filler.

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "debt_incurrence": "Concise summary of the general test, key baskets, and leverage thresholds",
  "restricted_payments": "Concise summary of RP baskets, builder mechanics, and ratio tests",
  "asset_sales": "Concise summary of cash requirements, reinvestment timing, and excess proceeds mechanics",
  "change_of_control": "Concise summary of offer price, timing, and tender mechanics",
  "liens_and_other": "Concise summary of equal-and-ratable, guarantor triggers, and lien limitations",
  "reasoning_steps": [
    "Step 1: How you located the covenant sections",
    "Step 2: How you extracted ratios and basket mechanics"
  ]
}`
