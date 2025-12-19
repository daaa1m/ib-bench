## Task

You are an investment banking analyst preparing a Public Information Book (PIB) for a senior banker. Your task is to compile and synthesise key public information on {company_name} (ticker: {ticker}) and produce a 1-page executive summary. #TODO

You will need to:

1. Retrieve the last 3 years of 10-K annual reports from SEC EDGAR
2. Retrieve all 10-Q quarterly reports from the last 3 years from SEC EDGAR
3. Obtain the most recent investor presentation from the company's Investor Relations website
4. Review the equity research reports provided below
5. Synthesise all sources into a 1-page summary

## Methodology & Process

1. **Retrieve SEC Filings**
   - Access SEC EDGAR (https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=40)
   - Download the 3 most recent 10-K filings
   - Download all 10-Q filings from the corresponding 3-year period

2. **Retrieve Investor Presentation**
   - Navigate to {company_name}'s investor relations website
   - Locate and download the most recent investor presentation or investor day materials

3. **Review Provided Equity Research**
   - Analyse the equity research reports provided below for analyst perspectives, price targets, and key themes

4. **Extract Key Information**
   - Business overview and segment breakdown
   - Financial performance trends (revenue, EBITDA, margins, EPS)
   - Key growth drivers and strategic initiatives
   - Capital structure and leverage metrics
   - Management guidance and outlook
   - Analyst consensus views and valuation perspectives

5. **Synthesise into 1-Page Summary**
   - Consolidate findings into a concise executive summary
   - Highlight the most critical information for deal context
   - Note any discrepancies between company guidance and analyst views

## Constraints and Negative Constraints

Constraints:

- Use only publicly available information from the specified sources
- Cite the source document for key figures (e.g., "FY2024 10-K", "Q3 2024 10-Q", "Morgan Stanley report dated XX/XX/XXXX")
- Prioritise the most recent data while showing relevant trends
- Use professional language appropriate for a client-facing PIB
- Include specific figures with appropriate precision (revenue in $mm or $bn as appropriate)

Negative Constraints:

- DO NOT include information from sources other than SEC filings, the investor presentation, and provided equity research
- DO NOT fabricate or estimate figures not explicitly stated in the source documents
- DO NOT include material non-public information
- DO NOT provide your own valuation or price target
- DO NOT exceed 1 page in the final summary output

## Output Format

Provide the 1-page summary in the following structure:

**Company Overview** (2-3 sentences)
Brief description of the business, key segments, and market position.

**Financial Summary**
Table or concise paragraph covering:

- Revenue (last 3 fiscal years + LTM)
- EBITDA and EBITDA margin
- Net income / EPS
- Key segment performance

**Strategic Highlights**
Recent strategic initiatives, M&A activity, capital allocation priorities, and management focus areas drawn from investor presentation and 10-K commentary.

**Analyst Perspectives**
Summary of sell-side views including consensus rating, price target range, and key debate topics from the provided equity research.

**Key Considerations**
2-3 bullet points highlighting the most important factors for a senior banker to understand about this company in a deal context.

---

## Provided Equity Research Reports

{equity_research_reports}
