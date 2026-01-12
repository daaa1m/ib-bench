## Task

You are an investment banking analyst tasked with researching precedent M&A
transactions for a client pitch. Your assignment is to identify 5 comparable
transactions in the enterprise software sector from the past 3 years and extract
EV/EBITDA multiples for each deal.

## Methodology & Process

1. **Search for Precedent Transactions:** Use web search to identify M&A
   transactions in the enterprise software sector announced between January 2022
   and December 2024
2. **Filter for Relevance:** Focus on acquisitions where the target is an
   enterprise software company (SaaS, infrastructure software, or enterprise
   applications)
3. **Verify Deal Details:** For each transaction, confirm the acquirer, target,
   announcement date, and deal value from reputable sources (press releases,
   financial news, deal databases)
4. **Extract EV/EBITDA Multiples:** Find the reported or calculated EV/EBITDA
   multiple for each deal. If not directly stated, note if it was derived from
   disclosed financials
5. **Cite Sources:** Document the source URL or publication for each data point

## Constraints and Negative Constraints

Constraints:

- Include only completed or announced deals, not rumors or speculation
- Report EV/EBITDA multiples as decimal numbers (e.g., "15.2x" or "15.2")
- Use reputable sources: company press releases, SEC filings, major financial
  news outlets, or established deal databases
- Include deal value context where available (helps validate multiple accuracy)

Negative Constraints:

- DO NOT include private equity buyouts unless EV/EBITDA multiple is publicly
  disclosed
- DO NOT include deals where the target is primarily a hardware company
- DO NOT fabricate or estimate multiples without source documentation
- DO NOT include deals under $500 million enterprise value (too small for comps)
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```json
{
  "transactions": "Array of 5 transaction objects, each containing: acquirer (string), target (string), announcement_date (YYYY-MM format), ev_ebitda_multiple (number or string with 'x'), enterprise_value_millions (number, optional)",
  "sources": "Array of source URLs or publication references used to verify the deals and multiples",
  "methodology": "Brief explanation of how deals were selected and multiples verified"
}
```
