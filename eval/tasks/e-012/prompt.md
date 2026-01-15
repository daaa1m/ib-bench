## Task

You are an investment banking analyst reviewing an S-1 filing for a potential
IPO advisory engagement of Coinbase Inc. Your task is to analyze the Risk
Factors section and produce a concise summary of the top 5 most material risks,
prioritized by potential business impact.

You are provided with `input.pdf`, the Coinbase S-1 filing. Use this document
only.

## Methodology & Process

1. **Risk Identification:** Read the entire Risk Factors section and catalog all
   disclosed risks.

2. **Materiality Assessment:** Evaluate each risk based on:
   - Probability of occurrence
   - Magnitude of financial impact if realized
   - Uniqueness to this company vs. generic industry boilerplate
   - Near-term vs. long-term threat horizon

3. **Prioritization:** Rank risks by materiality, NOT by their order of
   appearance in the document. Generic boilerplate risks (e.g., "we may face
   competition") should rank lower than company-specific or quantified risks.

4. **Impact Analysis:** For each top risk, assess the implications for:
   - Revenue and growth trajectory
   - Margin and profitability
   - Capital requirements and liquidity
   - Competitive positioning

## Constraints & Negative Constraints

Constraints:

- Focus on the Risk Factors section specifically
- Use only `input.pdf` as your source
- Provide exactly 5 risks, no more and no fewer
- Each risk summary must be 1-2 sentences maximum
- Analyst implications must be actionable and specific

Negative Constraints:

- DO NOT simply list risks in document order
- DO NOT include generic boilerplate language
- DO NOT provide lengthy block quotes from the filing
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{   "top_5_risks": [     {       "rank": 1,       "risk_title": "Brief title for the risk",       "risk_summary": "1-2 sentence summary of the risk",       "analyst_implication": "Specific implication for deal analysis"     },     ...   ],   "prioritization_rationale": "Brief explanation of why these 5 risks were selected and how they were ranked",   "methodology_notes": "Brief description of how you identified and prioritized the risks",   "reasoning_steps": ["Step 1: How you filtered to material risks", "Step 2: How you ranked them"] }`
