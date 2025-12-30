## Task

You are an investment banking analyst tasked with extracting the debt maturity
schedule from the attached 10-K filing. Your goal is to identify and compile
the complete schedule of principal debt amounts due by year as disclosed in the
debt footnotes.

## Methodology & Process

Follow these steps to extract the debt maturity schedule:

1. **Locate the Debt Footnote:** Navigate to the Notes to Consolidated Financial
   Statements section and find the footnote discussing long-term debt or
   borrowings.

2. **Identify the Maturity Schedule:** Within the debt footnote, locate the
   table or disclosure showing future maturities of long-term debt by fiscal
   year.

3. **Extract All Years:** Record the principal amount due for each year listed
   in the maturity schedule, including any "thereafter" bucket if present.

4. **Verify Completeness:** Cross-check that the sum of all maturity amounts
   reconciles to the total long-term debt balance disclosed.

5. **Note the Currency and Units:** Identify whether amounts are in thousands,
   millions, or actual dollars, and the currency (typically USD).

## Constraints and Negative Constraints

Constraints:
- Extract amounts exactly as presented in the source document
- Include all maturity years shown in the schedule
- Preserve the exact numerical values from the disclosure
- Identify the fiscal year-end date to contextualize the maturity years

Negative Constraints:
- DO NOT estimate or interpolate missing data
- DO NOT adjust amounts for any reason
- DO NOT include operating lease obligations unless explicitly part of debt maturities
- DO NOT conflate debt maturities with interest payments
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "maturity_schedule": {
    "year_1": "Amount for first maturity year (include year label, e.g., '2024: $X million')",
    "year_2": "Amount for second maturity year",
    "year_3": "Amount for third maturity year",
    "year_4": "Amount for fourth maturity year",
    "year_5": "Amount for fifth maturity year",
    "thereafter": "Amount due after year 5, if disclosed"
  },
  "total_debt": "Total long-term debt amount from schedule",
  "units": "Units of measurement (e.g., 'millions USD', 'thousands USD')",
  "source_location": "Specific footnote number and page reference where data was found",
  "methodology": "Brief description of how you located and verified the maturity schedule"
}`
