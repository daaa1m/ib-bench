## Task

You are an investment banking analyst tasked with populating a management
guidance history template for ADT Inc. (NYSE: ADT). You are provided with
`input.xlsx` containing a partially completed "Guidance" sheet where the
structure (dates, events, and guidance periods) is already filled in, but the
actual guidance values are missing.

Your task is to research ADT's historical earnings releases and investor
presentations to extract the management guidance figures and populate the
template in the sheet titled "Guidance" and in the cells highlighted in green.

## Template Structure

The "Guidance" sheet has the following layout:

- **Row 3 (Date)**: The date when guidance was announced (earnings release date)
- **Row 4 (Event)**: The quarterly earnings event (e.g., "3Q 2025", "1Q 2024")
- **Row 6 (Guidance period)**: The fiscal year the guidance applies to (e.g.,
  "FY 2025")

You must fill in the Low and High values for these metrics:

| Metric                   | Low Row | High Row | Columns | Notes                                               |
| ------------------------ | ------- | -------- | ------- | --------------------------------------------------- |
| Total Revenue            | 9       | 10       | C to AH | All periods, values in millions USD                 |
| Adj. EBITDA              | 14      | 15       | C to AH | All periods, values in millions USD                 |
| Adj. EPS                 | 20      | 21       | C to N  | Started in FY 2023 guidance, values in dollars      |
| FCF before special items | 25      | 26       | C to H  | Started in FY 2024 guidance, values in millions USD |

## Methodology & Process

1. **Identify Source Documents**: For each date in Row 3, locate the
   corresponding ADT earnings release or investor presentation from that date.
   Sources include SEC 8-K filings, ADT investor relations website, and
   financial news archives.

2. **Extract Guidance Figures**: From each source document, extract the
   management's full-year guidance for each metric. Pay attention to:
   - The guidance is for the fiscal year shown in Row 6 (Guidance period), NOT
     the quarter when the guidance was announced
   - Some metrics were introduced later (EPS from FY 2022, FCF from FY 2024)
   - Leave cells blank where guidance was not provided for that metric

3. **Verify Consistency**: Check that guidance updates make logical sense:
   - Initial guidance is typically given at the start of the fiscal year (4Q
     prior year results)
   - Guidance may be raised, maintained, or lowered as the year progresses
   - Guidance ranges typically narrow as the year progresses

4. **Document Your Reasoning**: Explain reasoning steps and data sources.

## Constraints

- Only modify the "Guidance" sheet
- Enter only numeric values (no currency symbols, no "million" text)
- Revenue and EBITDA values should be in millions USD (e.g., 5000
  not 5000000000)
- EPS values should be in dollars (e.g., 0.85)
- Leave cells blank if guidance was not provided for that metric/period
- Only fill in cells highlighted in green

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)

## Negative Constraints

- DO NOT modify the "rubric" sheet
- DO NOT change the existing dates, events, or guidance period values
- DO NOT fabricate guidance values - only use figures from actual ADT
  disclosures
- DO NOT include formulas in the Low/High rows - enter hardcoded values only
- NO conversational filler

## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
guidance values populated in the "Guidance" sheet.

**2. JSON Summary**: Provide a summary of your work as a raw JSON object with
the following keys. Do not include any markdown formatting, backticks, or
preamble.

`{   "reasoning_steps": [     "Step 1: Description of how you approached finding the data",     "Step 2: How you verified the guidance periods matched",     "Step 3: Any notable observations about the data"   ],   "metrics_coverage": {     "revenue_periods_filled": "Number of periods with revenue guidance entered",     "ebitda_periods_filled": "Number of periods with EBITDA guidance entered",     "eps_periods_filled": "Number of periods with EPS guidance entered",     "fcf_periods_filled": "Number of periods with FCF guidance entered"   },   "data_sources": ["List of primary sources used for the guidance data"] }`
