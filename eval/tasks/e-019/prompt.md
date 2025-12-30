## Task

You are an investment banking analyst reviewing a credit agreement for a
leveraged finance transaction. Your task is to extract and organize the
financial covenants from the attached credit agreement.

The credit agreement contains financial covenant provisions that impose
restrictions on the borrower. You must identify and extract these covenants,
including their definitions, threshold levels, and testing requirements.

## Methodology & Process

Follow these steps to systematically extract the covenant information:

1. **Locate Covenant Section:** Navigate to the financial covenants section of
   the credit agreement. This is typically found in the "Affirmative Covenants"
   or "Financial Covenants" article.

2. **Identify Each Covenant:** For each financial covenant, extract:
   - The covenant name (e.g., Maximum Leverage Ratio, Minimum Interest Coverage)
   - The specific ratio or metric definition
   - The numeric threshold or limit
   - Testing frequency (quarterly, annually, etc.)

3. **Parse Ratio Definitions:** Carefully read how each ratio is defined:
   - Numerator components
   - Denominator components
   - Any adjustments or exclusions

4. **Extract Compliance Levels:** Note the specific threshold levels required
   for compliance, including any step-downs or changes over time.

5. **Document Testing Requirements:** Identify how and when covenants are
   measured (fiscal quarter-end, trailing twelve months, etc.).

## Constraints and Negative Constraints

Constraints:
- Extract exact threshold values as stated in the agreement
- Preserve the precise language used for ratio definitions
- Include all material financial covenants

Negative Constraints:
- DO NOT paraphrase or simplify covenant definitions
- DO NOT include non-financial covenants (reporting, insurance, etc.)
- DO NOT infer thresholds not explicitly stated
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "covenant_summary": "A structured table or list of all financial covenants with their names, definitions, thresholds, and testing frequency",
  "leverage_covenant": "The leverage ratio covenant details including definition and threshold(s)",
  "coverage_covenant": "The interest coverage or fixed charge coverage covenant details including definition and threshold(s)",
  "testing_frequency": "How and when covenants are tested (e.g., quarterly on trailing twelve months basis)",
  "extraction_methodology": "Brief description of how you located and parsed the covenant information"
}`
