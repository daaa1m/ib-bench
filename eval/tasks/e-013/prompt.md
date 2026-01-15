## Task

You are an investment banking analyst preparing management diligence questions
for Dollar General. Your task is to draft 10 high-quality diligence questions
based on current public information about the company and its operating context.

Use web sources (earnings releases, investor presentations, transcripts, and
credible industry commentary) to ground the questions in specific issues.

## Methodology & Process

1. Review recent Dollar General filings, earnings releases, and transcripts to
   identify performance drivers and pain points.
2. Scan recent news and industry commentary for competitive dynamics, pricing
   pressure, and consumer behavior trends.
3. Translate findings into 10 prioritized management questions that probe
   root causes, leading indicators, and executable levers.
4. Ensure the questions collectively cover the required topic areas.

## Constraints and Negative Constraints

Constraints:
- Provide exactly 10 questions, ranked 1-10 by priority.
- Each question must be 1-2 sentences and include a brief rationale.
- Cover all required topic areas (margins/shrink, SG&A drivers, inventory/SKU,
  store productivity, pricing/markdowns/competition, digital delivery, and
  low-income consumer/SNAP exposure).
- Include at least one source URL for the underlying context.

Negative Constraints:
- DO NOT include generic textbook questions.
- DO NOT use sources unrelated to Dollar General or U.S. discount retail.
- NO conversational filler.

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "questions": [
    {
      "rank": 1,
      "topic": "Margin drivers / shrink / damages / media network",
      "question": "Question text",
      "why_it_matters": "Brief rationale",
      "source": "URL"
    }
  ],
  "topic_coverage": "Brief confirmation that all required topics are covered",
  "source_support": ["URL1", "URL2"],
  "methodology_notes": "Brief description of how you selected and prioritized the questions",
  "reasoning_steps": ["Step 1: How you gathered the source context", "Step 2: How you prioritized questions"]
}`
