## Task

You are an investment banking analyst preparing a short internal investment
memo.

Your team is evaluating whether to invest alongside an activist investor in
PepsiCo. You must base your work ONLY on the activist presentation available at
this URL:
"https://elliottletters.com/wp-content/uploads/Elliotts-Perspectives-on-PepsiCo-Presentation.pdf"

Your deliverable is an IC-ready summary of the company’s current situation, the
activist’s thesis and proposed initiatives, the value creation opportunity, and
the key risks. You must also recommend whether the team should invest alongside
the activist and, if yes, at what valuation / entry multiple given the market
price has moved up since the stake was revealed.

## Methodology & Process

1. Read the activist presentation end-to-end and identify the primary claims,
   supporting evidence, and proposed value creation initiatives.
2. Summarize the company’s current situation as described in the deck
   (performance, drivers of underperformance, and where the problems are
   concentrated).
3. Distill the activist’s plan into a small set of actionable initiatives and
   explain the mechanism for value creation (what changes, why it matters, and
   how it impacts fundamentals and/or multiple).
4. Provide valuation framing using only what the deck provides (e.g., current
   multiple vs peers / historical range, implied upside targets). Translate this
   into a clear recommended entry valuation / multiple that reflects a margin of
   safety given the post-reveal price move.
5. Identify the key risks and execution challenges (including reasons the plan
   could fail or take longer than expected), again using only deck-supported
   points.
6. Conclude with a clear recommendation (invest / pass / conditional) and the
   conditions required to proceed.

## Constraints

- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Use ONLY the activist presentation at the URL above as your source.
- Do not cite or rely on external data, news, or filings.
- Keep the write-up structured and senior-readable (IC-ready), not a
  slide-by-slide recap.
- When stating numbers, keep units consistent with the deck and be explicit
  about whether metrics are LTM / NTM.

## Negative Constraints

- DO NOT use any source other than the activist presentation.
- DO NOT fabricate facts or numbers not supported by the presentation.
- DO NOT give a vague recommendation; you must pick a stance and support it.
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```json
{
  "executive_summary": [
    "Bullet 1",
    "Bullet 2",
    "Bullet 3"
  ],
  "state_of_company": "Concise description of where the business is today and what is driving underperformance per the deck",
  "activist_thesis": "What the activist believes is wrong and why; include the core claims and supporting evidence",
  "value_creation_plan": [
    {
      "initiative": "Name of initiative",
      "what_changes": "What would change operationally/strategically",
      "why_it_creates_value": "Mechanism for value creation",
      "evidence_from_deck": "Specific support from the presentation, including slide/page reference(s)"
    }
  ],
  "valuation_recommendation": {
    "recommendation": "Invest/Pass/Conditional",
    "entry_valuation_framework": "How you translate the deck’s valuation discussion into an entry framework",
    "recommended_entry_multiple": "A specific entry multiple or valuation range you would be willing to pay, stated in the same terms as the deck (e.g., NTM P/E)",
    "upside_case": "What upside you expect if key initiatives work (tie to deck framing)",
    "downside_case": "What could go wrong and what downside that implies (qualitative is fine if deck lacks numbers)",
    "conditions_to_invest": ["Condition 1", "Condition 2", "Condition 3"]
  },
  "risk_assessment": [
    {
      "risk": "Key risk",
      "why_it_matters": "How it impacts thesis / timeline",
      "mitigant_or_signpost": "What you would watch for or what would reduce the risk"
    }
  ],
  "presentation_quality": {
    "structure": "How the memo is organized and why it is easy to follow",
    "evidence_quality": "How well you anchored claims to the deck",
    "missing_info_or_open_questions": ["Question 1", "Question 2"]
  }
}
```

