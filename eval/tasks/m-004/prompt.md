## Task

You are an investment banking analyst supporting an M&A origination effort. A
strategic client is looking to acquire companies in the European food
ingredients and specialty chemicals sector. Your task is to generate a
preliminary target list of 10 private companies that could be potential
acquisition candidates.

## Target Criteria

The client is interested in companies that meet the following profile:

- **Geography**: Headquarters in Europe (UK, Germany, France, Netherlands,
  Italy, Spain, Nordics, or Benelux preferred)
- **Sector**: Food ingredients, flavors & fragrances, specialty food chemicals,
  or functional food additives
- **Size**: Estimated revenue between €50M and €500M
- **Ownership**: Private companies (PE-backed or family-owned) - no public
  companies
- **Business Model**: B2B suppliers to food & beverage manufacturers

## Required Information Per Target

For each company, provide:

1. **Company Name**: Legal entity name
2. **Headquarters**: City and country
3. **Estimated Revenue**: Revenue range or estimate (cite source if available)
4. **Key Products/Segments**: Primary product categories or business segments
5. **Ownership**: PE sponsor name if PE-backed, or "Family/Founder-owned" if
   independent
6. **Brief Rationale**: 1-2 sentences on why this is a relevant target

## Methodology & Process

1. Use web search to identify relevant companies through:
   - Industry association member lists
   - Trade publication coverage
   - PE portfolio company announcements
   - M&A transaction databases (if accessible)
   - Company websites and LinkedIn
2. Verify each company meets the target criteria
3. Cross-reference multiple sources to validate information
4. Prioritize companies with recent news or activity indicating potential
   transaction readiness

## Constraints

- Include exactly 10 companies
- All companies must be private (not publicly traded)
- All companies must have European headquarters
- Revenue estimates should be defensible (cite source or basis)

## Negative Constraints

- DO NOT include public companies
- DO NOT include companies headquartered outside Europe
- DO NOT include companies clearly outside the food ingredients sector
- DO NOT fabricate company names or details
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{   "methodology": "Brief description of search approach and sources used",   "targets": [     {       "company_name": "Company legal name",       "headquarters": "City, Country",       "estimated_revenue": "€XXM-€XXXM or specific estimate",       "key_products": "Primary product categories",       "ownership": "PE sponsor name or Family/Founder-owned",       "rationale": "Why this is a relevant target"     }   ],   "data_limitations": "Note any limitations in data availability or confidence level" }`
