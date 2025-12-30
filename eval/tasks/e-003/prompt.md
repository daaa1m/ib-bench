## Task

You are an investment banking analyst tasked with extracting specific financial
data from Amazon's fiscal year 2024 10-K filing.

You must obtain Amazon's (AMZN) fiscal year 2024 10-K filing from either the SEC
EDGAR database or Amazon's Investor Relations website. From this filing, extract
the total purchase obligations due within the next 24 months from December
31, 2024.

## Methodology & Process

1. **Locate the Filing:** Use web search or navigate directly to SEC EDGAR
   (www.sec.gov/edgar) or Amazon's IR website to find the FY2024 10-K filing
2. **Identify Relevant Section:** Locate the "Purchase Obligations," or similar
   disclosure section
3. **Extract Purchase Obligations:** Find the table showing purchase obligations
   broken down by time period
4. **Calculate 24-Month Total:** Identify and sum the amounts for obligations
   due in the next 24 months from December 31, 2024
5. **Verify Units:** Confirm whether amounts are stated in millions or billions
   and ensure your answer reflects this accurately

## Constraints and Negative Constraints

Constraints:

- Use the official SEC filing or Amazon's IR website as your data source
- Report the value in millions USD (e.g., "12,599" for USD 12,599 million)
- Extract only purchase obligations, not other types of contractual commitments

Negative Constraints:

- DO NOT confuse purchase obligations with other contractual obligations (debt,
  leases, etc.)
- DO NOT use data from quarterly filings (10-Q) or prior year 10-Ks
- DO NOT include obligations beyond 24 months in your calculation
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```
{
  "purchase_obligations_24m": "The total purchase obligations due within 24 months in millions USD (numeric format)",
  "source_reference": "Cite the exact section, page, or table from the 10-K where you found this data"
}
```
