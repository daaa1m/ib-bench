## Task

You are a private equity associate at a leading PE firm. Your team is evaluating
a potential acquisition of "Project Iceberg," a healthcare information and
analytics company. Based on the background materials provided, prepare a 1-page
investment memo for the Investment Committee.

You are provided with `input.pdf` containing the case study background materials.

## Company Overview

Project Iceberg is a healthcare data and analytics provider serving
pharmaceutical companies, biotech firms, and healthcare providers. The business
has two main segments:
- **Information & Analytics (I&A)**: Data products and analytics platforms
- **Consulting & Services (C&S)**: Advisory and implementation services

## Required Deliverables

### 1. Investment Thesis (Bull Case)

Articulate why this is an attractive investment:
- Key value drivers and competitive advantages
- Growth opportunities and margin expansion potential
- Quality of earnings and cash flow characteristics

### 2. Key Investment Risks

Identify the 3-5 most significant risks:
- Business/operational risks
- Market/competitive risks
- Financial/structural risks
- Rank risks by severity and likelihood

### 3. Valuation Perspective

Provide your view on:
- Appropriate entry multiple range (EV/EBITDA)
- Comparison to precedent transactions and trading comps
- Key valuation considerations for this asset

### 4. Management Projections Assessment

Critically evaluate the projections:
- Are revenue growth assumptions reasonable?
- Are margin expansion targets achievable?
- What are the key sensitivities?

### 5. Diligence Priorities

List the top 5 areas for business diligence:
- What questions need to be answered before proceeding?
- What data would you request from management?

### 6. Investment Recommendation

Provide a clear recommendation:
- Proceed / Pass / Conditional (with conditions)
- Key factors driving your recommendation

## Methodology & Process

1. Read the background materials thoroughly
2. Extract key financial metrics and trends
3. Identify business model strengths and weaknesses
4. Assess management's projections critically
5. Develop your investment thesis
6. Prioritize risks and diligence items
7. Synthesize into concise, actionable memo

## Constraints

- Memo must be structured and concise (equivalent to 1 page)
- All views must be supported by data from the materials
- Recommendations must be actionable for Investment Committee
- Must address all required sections

## Negative Constraints

- DO NOT make up financial data not in the materials
- DO NOT provide generic PE commentary unconnected to this deal
- DO NOT ignore obvious risks or red flags
- DO NOT provide wishy-washy recommendations without clear view
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "investment_thesis": "3-4 sentence summary of why this is attractive",
  "key_risks": [
    {"risk": "Risk description", "severity": "High/Medium/Low", "mitigation": "How to address"},
    {"risk": "Risk description", "severity": "High/Medium/Low", "mitigation": "How to address"},
    {"risk": "Risk description", "severity": "High/Medium/Low", "mitigation": "How to address"}
  ],
  "entry_multiple_view": "Your view on appropriate entry EV/EBITDA with rationale",
  "projection_assessment": "Your critical view of management's projections",
  "top_diligence_items": ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"],
  "recommendation": "Proceed/Pass/Conditional",
  "recommendation_rationale": "2-3 sentences supporting your recommendation"
}`
