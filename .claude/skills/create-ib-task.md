---
name: create-ib-task
description: Use when creating prompt.md and rubric.json for a new IB-bench task based on an existing meta.yaml
---

# Creating IB-bench Task Files

This skill creates `prompt.md` and `rubric.json` for IB-bench evaluation tasks.

## Prerequisites

Before using this skill, you MUST have:
1. A populated `meta.yaml` in the task directory
2. Read existing examples: `eval/tasks/e-001/`, `eval/tasks/e-002/`, `eval/tasks/e-003/`

## Step 1: Analyze the meta.yaml

Read the task's `meta.yaml` and extract all fields:

```yaml
# Documentation
task:
  id: e-001                    # Task identifier (must match folder name)
  type: fix-error              # fix-error, summarise, extraction, creating
  category: excel              # excel, pdf, web
  description:
    "Brief explanation. Error/problem (if applicable). Expected answer with
    specific values. What capability this tests."

prompt:
  notes: "Special instructions or context given to LLM"

input:
  input-file-original: "$human/source.xlsx"  # Path, list of paths, or None
  notes: "Modifications or notable aspects of input"
```

**Path alias:** `$human` = `data-factory/human-generated/`

**Key fields to use:**
- `task.type` → Determines prompt structure and methodology
- `task.category` → Determines input handling (excel/pdf/web)
- `task.description` → Contains the answer and specific requirements
- `prompt.notes` → Context about what instructions LLM receives
- `input.input-file-original` → Source file path(s), or None for web tasks
- `input.notes` → Additional context for prompt creation

## Step 2: Create prompt.md

Follow this structure:

```markdown
## Task

You are an investment banking analyst [specific role based on task type].

[Clear description of what needs to be done, including any specific data sources or files]

## Methodology & Process

[Numbered steps the model should follow to complete the task]

1. [First step]
2. [Second step]
...

## Constraints and Negative Constraints

Constraints:
- [What must be done]
- [Quality requirements]

Negative Constraints:
- DO NOT [thing to avoid]
- DO NOT [another thing to avoid]
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

```json
{
  "key_matching_rubric_criterion": "description",
  ...
}
```
```

### Key Rules for prompt.md:

1. **JSON output keys MUST match rubric criterion IDs exactly**
2. **Include reasoning/methodology key** for transparency
3. **Be specific about data sources**:
   - If `input-file-original` exists → reference the input file
   - If `input-file-original` is None → instruct LLM to fetch from web
4. **Include negative constraints** to prevent common LLM mistakes
5. **For extraction tasks**: specify exact format for numerical answers (e.g., "in millions USD")

### Category-specific guidance:

| category | Input handling |
|----------|----------------|
| `excel` | Reference the attached xlsx file, mention specific sheets/cells if known |
| `pdf` | Reference the attached PDF, mention sections if known |
| `web` | Instruct to use web search or navigate to specific URLs (SEC EDGAR, IR sites) |

## Step 3: Create rubric.json

Follow this schema:

```json
{
  "task_id": "{task-id}",
  "version": "1.0",
  "total_points": 100,
  "criteria": {
    "criterion_id_matching_prompt_output_key": {
      "description": "What this criterion evaluates",
      "type": "programmatic",
      "match_type": "substring_one_of",
      "accepted_values": ["value1", "value2"],
      "points": 40,
      "gates_llm": true
    },
    "another_criterion": {
      "description": "Qualitative assessment",
      "type": "llm_judge",
      "core_concepts": ["concept1", "concept2"],
      "points": 15
    }
  }
}
```

### Rubric Design Rules:

1. **Criterion IDs = JSON output keys** from prompt.md
2. **Programmatic checks first** for objective answers (use `gates_llm: true`)
3. **LLM judge for qualitative** assessment (15% of total points max)
4. **Points allocation**:
   - Core answer/finding: 40-50 points
   - Supporting details: 30-40 points
   - Methodology/reasoning: 10-15 points (usually llm_judge)

### Match Types:

For `type: "programmatic"`:
- `substring_one_of`: Value contains any of the accepted strings (case-insensitive)
- `regex_pattern`: Value matches regex pattern with optional required/forbidden elements

For `type: "llm_judge"`:
- Include `core_concepts` array with key terms the judge should look for

### Extracting accepted values from meta.yaml:

The `task.description` often contains the expected answer. Parse it to build `accepted_values`:
- "The answer is USD16,477m" → `["16,477", "16477", "$16,477", "16,477m"]`
- "formula in row 140" → `["Row 140", "140", "L140", "M140"]`

## Step 4: Verify Alignment

Checklist:
- [ ] Every JSON output key in prompt.md has a matching criterion in rubric.json
- [ ] Programmatic criteria have clear, unambiguous accepted values
- [ ] Points sum to total_points (usually 100)
- [ ] gates_llm is true for objective criteria that should block LLM evaluation on failure
- [ ] Category matches input handling (web tasks have no input files)

## Examples by Task Type

### fix-error (excel)
- Prompt: Ask to find and fix specific error, provide methodology
- Rubric: Programmatic checks for location + formula, LLM judge for explanation

### summarise (pdf)
- Prompt: Ask to summarize with specific focus areas
- Rubric: All LLM judge criteria for qualitative assessment

### extraction (web)
- Prompt: Specify data source (SEC EDGAR, IR site), exact value to extract
- Rubric: Programmatic check for extracted value, source validation, LLM for methodology
