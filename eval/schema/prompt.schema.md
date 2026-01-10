# Prompt Schema for IB-bench Tasks

This document defines the structure and requirements for `prompt.md` files.

## Required Sections

### 1. Task

Sets the context and objective.

**Requirements:**
- Open with role statement: "You are an investment banking analyst..."
- State the specific deliverable clearly
- Reference input files by name if applicable
- **NO curly braces `{}`** - causes LLM judge parsing failures during evaluation

**Example:**
```markdown
## Task

You are an investment banking analyst tasked with auditing a simple, integrated
LBO model for 'Dave & Buster's' that is currently broken. Specifically, the
Balance Sheet does not tie (Total Assets ≠ Total Liabilities + Equity) in
row 123.
```

### 2. Methodology & Process

Numbered steps the model should follow.

**Requirements:**
- 3-7 concrete steps
- Each step should be actionable
- Order steps logically (read → analyze → compute → verify)

### 3. Constraints and Negative Constraints

Guardrails for acceptable responses.

**Constraints (positive):**
- Format requirements (units, precision)
- Scope boundaries
- Quality standards

**Negative Constraints:**
- Always include: "NO conversational filler"
- Prevent common LLM mistakes
- Scope exclusions (what NOT to touch)

### 4. Output Format

Specifies the exact deliverable format.

**For JSON-only tasks:**
```markdown
## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "key_name": "description of what goes here",
  ...
}`
```

**For tasks requiring file output (Excel, etc.):**
```markdown
## Output Format

You must provide TWO outputs:

**1. Modified Excel File**: Save and return the updated Excel workbook with all
changes applied to [specific sheet/location].

**2. JSON Summary**: After implementing changes, provide your response as a raw
JSON object with the following keys. Do not include any markdown formatting,
backticks, or preamble.

`{
  "key_name": "description",
  ...
}`
```

## Key Rules

1. **JSON keys MUST match rubric criterion IDs exactly**
2. **No curly braces `{}` in Task section** - causes LLM judge parsing failures
3. **Be explicit about file outputs** - if LLM must return an Excel file, state it clearly with specific instructions
4. **Include reasoning key** for transparency in evaluation
5. **Specify units and precision** for numerical outputs (e.g., "in millions USD", "two decimal places")

## File Output Requirements

When the task requires the LLM to produce/modify an Excel file:

1. **State it prominently** in the Task section
2. **Repeat in Output Format** with explicit "Save and return" language
3. **Specify which sheets/cells** should be modified
4. **Include verification values** in JSON output to confirm correct implementation

Example language:
- "Save and return the updated Excel workbook"
- "You must return the modified Excel file with your changes"
- "Your deliverable includes the completed Excel model"
