## Task

You are an investment banking analyst supporting an M&A coverage team. Your MD has asked you to review the attached Compass-Anywhere merger agreement (from the 8-K) and prepare a summary of the key economic and structural terms for an internal briefing.

You are provided with `input.pdf` containing the merger agreement. Use this document only.

The summary should focus on deal economics and material protections, not boilerplate legal language.

## Methodology & Process

1. Read the merger agreement in full before summarizing
2. Identify the transaction structure (merger type, parties, consideration)
3. Extract the purchase price and per-share consideration details
4. Locate conditions to closing (regulatory approvals, shareholder votes, material adverse change)
5. Find termination provisions including fees, triggers, and amounts
6. Identify any MAC/MAE provisions and their key carve-outs
7. Note any go-shop or no-shop provisions if present
8. Synthesise into a structured deal summary

## Constraints and Negative Constraints

Constraints:

- Do not ask clarifying questions; assume all required information is provided or can be obtained via web search.
- Focus on economic terms that would matter to bankers advising on similar transactions
- Use only `input.pdf` as your source
- Include specific figures (prices, percentages, dollar amounts) when stated
- Use precise M&A terminology (e.g., "reverse termination fee" not "breakup fee the buyer pays")
- Note the date of the agreement if available

Negative Constraints:

- DO NOT summarize boilerplate provisions (representations, warranties, covenants) unless economically material
- DO NOT include general legal disclaimers or standard definitions
- DO NOT speculate on terms not explicitly stated in the agreement
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not include any markdown formatting, backticks, or preamble.

`{
  "deal_structure": "Transaction type, parties, and form of consideration",
  "purchase_price": "Per-share price and implied total equity value if stated",
  "conditions_to_closing": "Key closing conditions including regulatory and shareholder requirements",
  "termination_provisions": "Termination rights, fees, and their triggers",
  "mac_provisions": "MAC/MAE definition scope and key carve-outs",
  "other_material_terms": "Any other economically significant provisions (go-shop, financing conditions, etc.)",
  "reasoning": "Your analysis approach and how you identified the key terms",
  "reasoning_steps": ["Step 1: How you located the key economic terms", "Step 2: How you validated fee and condition details"]
}`
