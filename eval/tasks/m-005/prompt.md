## Task

You are an investment banking analyst building a quarterly cost analysis model
for Tesla. You are given an Excel template (`input.xlsx`) with revenue data
pre-filled and a structure for COGS analysis.

Your task is to:

1. Research and input Tesla's quarterly Cost of Goods Sold by segment
2. Calculate Q4 seasonal indices for each cost category
3. Estimate Q4 2025 costs using the seasonal indices
4. Calculate gross profit excluding automotive credit revenue

## Methodology & Process

1. **Review the template structure** in rows 2-6 which outline the specific
   deliverables

2. **Research Tesla quarterly financials** from public sources (10-Q/10-K
   filings, earnings releases) to find COGS breakdown by segment for 2023, 2024,
   and Q1-Q3 2025

3. **Input COGS data** in rows 18-21 for each segment:
   - Automotive (row 18)
   - Automotive excluding leasing (row 19)
   - Energy generation and storage (row 20)
   - Service and other (row 21)

4. **Calculate totals** in row 22 (sum of segments) and yearly totals

5. **Calculate Q4 seasonal indices** (rows 25-28):
   - Formula: Q4 value / (Yearly total / 4)
   - Calculate for 2023 (column F), 2024 (column K)
   - Average the two years for the projection index (column P)

6. **Input auto credit revenue** in row 30 for all quarters (this is regulatory
   credit revenue that should be excluded from gross margin analysis)
   - For Q4 2025 (P32), assume auto credit revenue of 450

7. **Calculate gross profit ex auto credits** in row 32:

8. **Calculate margin percentage** in row 33

## Constraints

- Use Tesla's actual reported quarterly figures from public filings
- All monetary values in millions USD
- Q4 2025 estimate (column P) should use the average seasonal index
- The circularity toggle in P9 controls whether Q4E calculations are active
- Use headless LibreOffice to recalculate the workbook; do not rely on calculations outside the spreadsheet.

## Negative Constraints

- DO NOT fabricate financial data - use actual Tesla reported figures
- DO NOT modify the template structure or add/delete rows
- DO NOT change the revenue figures already provided
- NO conversational filler

## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook

## Output Format

You must provide TWO outputs:

**1. Completed Excel Model**: Save and return the completed Excel workbook with
all COGS data, seasonal indices, and gross profit calculations, following the
formatting conventions above.

**2. JSON Summary**: After completing the model, provide your response as a raw
JSON object with the following keys. Do not include any markdown formatting,
backticks, or preamble.

```json
{
  "p22_total_cogs_q4e": "Value in cell P22 (Q4 2025 estimated total COGS)",
  "f28_service_q4_index_2023": "Value in cell F28 (Service Q4 seasonal index for 2023)",
  "g30_auto_credit_2023": "Value in cell G30 (2023 total auto credit revenue)",
  "p32_gross_profit_q4e": "Value in cell P32 (Q4 2025 gross profit ex auto credits)",
  "c32_gross_profit_q1_2023": "Value in cell C32 (Q1 2023 gross profit ex auto credits)",
  "data_sources": "Brief description of sources used for Tesla financial data"
}
```
