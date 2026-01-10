---
name: create-ib-task
description:
  Use when creating prompt.md and rubric.json for a new IB-bench task based on
  an existing meta.yaml
---

# Creating IB-bench Task Files

This skill creates `prompt.md` and `rubric.json` for IB-bench evaluation tasks.

## Resources

Before using this skill, you MUST have:

1. A populated `meta.yaml` in the task directory
2. Referred to examples of high quality prompt.md and rubric.json. See
   [prompt-example-*.md] and [rubric-example-*.json]

## Step 1: Analyze the meta.yaml

Read the task's `meta.yaml` and extract all fields:

```yaml
task:
  id: e-001 # Task identifier (must match folder name, pattern: ^[emh]-\d{3}$)
  title: "Find the balance sheet error in an LBO model" # Human-readable (10-100 chars)
  type: fix-error # fix-error, summarise, extraction, creating
  category: # IB domain(s) - array with 1+ values
    - financial-analysis
  input_type: excel # Input format: excel, pdf, web, multi
  description: >
    Brief explanation. Error/problem (if applicable). Expected answer with
    specific values. What capability this tests. (min 50 chars)

prompt:
  notes: "Special instructions or context given to LLM"

input:
  input-file-original: "$human/source.xlsx" # Path, list of paths, or null
  notes: "Modifications or notable aspects of input"
```

**Path alias:** `$human` = `data-warehouse/human-generated/`

**Category values** (IB domains, can have multiple):

- `financial-analysis` - Financial modeling, valuation, metrics
- `due-diligence` - Deal analysis, target company research
- `document-review` - Reviewing filings, agreements, disclosures
- `data-extraction` - Pulling specific data points from sources

**Input type values** (file format):

- `excel` - Excel spreadsheets (.xlsx)
- `pdf` - PDF documents
- `web` - Web-based data (SEC EDGAR, IR sites)
- `multi` - Multiple input types

**Key fields to use:**

- `task.title` → Human-readable task summary for display
- `task.type` → Determines prompt structure and methodology
- `task.category` → IB domain(s) the task tests
- `task.input_type` → Determines input handling (excel/pdf/web/multi)
- `task.description` → Contains the answer and specific requirements
- `prompt.notes` → Context about what instructions LLM receives
- `input.input-file-original` → Source file path(s), or null for web tasks
- `input.notes` → Additional context for prompt creation

## Step 2: Create prompt.md

See `eval/schema/prompt.schema.md` for full specification.

Follow this structure:

```markdown
## Task

You are an investment banking analyst tasked with [specific task description].
[Clear context and deliverable in plain prose.]

## Methodology & Process

1. [First concrete step]
2. [Second step]
3. [Continue as needed...]

## Constraints and Negative Constraints

Constraints:
- [Format requirements]
- [Quality standards]

Negative Constraints:
- DO NOT [thing to avoid]
- NO conversational filler

## Output Format

Provide your response as a raw JSON object with the following keys. Do not
include any markdown formatting, backticks, or preamble.

`{
  "key_matching_rubric_criterion": "description",
  ...
}`
```

### Key Rules for prompt.md:

1. **JSON output keys MUST match rubric criterion IDs exactly**
2. **NO curly braces `{}` in Task section** - causes LLM judge parsing failures
3. **Include reasoning/methodology key** for transparency
4. **Be specific about data sources**:
   - If `input-file-original` exists → reference the input file by name
   - If `input-file-original` is null → instruct LLM to fetch from web
5. **Include negative constraints** to prevent common LLM mistakes
6. **For extraction tasks**: specify exact format for numerical answers (e.g., "in millions USD")

### Excel File Output (CRITICAL):

When the task requires the LLM to create or modify an Excel file:

1. **State explicitly in Task section**: "Your deliverable includes the completed Excel model"
2. **Repeat in Output Format** with TWO outputs structure:
   ```
   You must provide TWO outputs:
   
   **1. Modified Excel File**: Save and return the updated Excel workbook with
   all changes applied to [specific sheet].
   
   **2. JSON Summary**: [standard JSON output instructions]
   ```
3. **Specify which sheets/cells** should be modified or created
4. **Include verification values** in JSON (e.g., `"cell_A1_value": "..."`) to confirm implementation

### Excel Formatting Conventions (REQUIRED for Excel output tasks):

For ALL tasks requiring Excel output, include IB formatting standards in the prompt.

**Add this section before Output Format:**

```markdown
## Formatting Requirements

Apply standard IB Excel formatting conventions to all cells you modify:

- **Blue font**: Hardcoded numbers (values you type directly)
- **Green font**: Formulas referencing another sheet in the same workbook
- **Red font**: Formulas referencing an external workbook
```

**Add formatting criterion to rubric.json (10 points):**

```json
{
  "formatting": {
    "description": "IB formatting conventions: blue for hardcoded numbers, green for cross-sheet refs, red for external workbook refs",
    "type": "programmatic",
    "match_type": "excel_formatting",
    "sheet": "Model",
    "points": 10
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `cells` | No | List of cell refs/ranges to check (default: all cells) |
| `sheet` | No | Sheet name to check (default: active sheet) |

**Scoring logic:**
- Blue: hardcoded numbers (int/float values, not formulas)
- Green: formulas with `Sheet!Cell` syntax (same workbook, different sheet)
- Red: formulas with `[Workbook]Sheet!Cell` syntax (external workbook)

**Point allocation:** Add 10 points for formatting, bumping total_points to 110.

### Input type-specific guidance:

| input_type | Input handling                                                                |
| ---------- | ----------------------------------------------------------------------------- |
| `excel`    | Reference the attached xlsx file, mention specific sheets/cells if known      |
| `pdf`      | Reference the attached PDF, mention sections if known                         |
| `web`      | Instruct to use web search or navigate to specific URLs (SEC EDGAR, IR sites) |
| `multi`    | Reference all attached files by name, explain how they relate                 |

## Step 3: Create rubric.json

See `eval/schema/rubric.schema.json` for full specification.

```json
{
  "task_id": "e-001",
  "version": "1.0",
  "total_points": 100,
  "criteria": {
    "criterion_id": {
      "description": "What this criterion evaluates (min 10 chars)",
      "type": "programmatic",
      "match_type": "substring_one_of",
      "accepted_values": ["value1", "value2"],
      "points": 40,
      "gates_llm": true
    }
  }
}
```

### Rubric Design Rules:

1. **Criterion IDs = JSON output keys** from prompt.md
2. **Programmatic checks first** for objective answers (use `gates_llm: true`)
3. **LLM judge for qualitative** assessment (reasoning, explanation quality)
4. **Points allocation**: Weight by importance to task goal. No fixed formula.

### Match Types for `type: "programmatic"`:

**1. `substring_one_of`** - Value contains any accepted string (case-insensitive)

```json
{
  "match_type": "substring_one_of",
  "accepted_values": ["16,477", "16477", "$16,477"],
  "forbidden_elements": ["million", "billion"],
  "search_full_response": false
}
```

**2. `regex_pattern`** - Value matches regex with optional constraints

```json
{
  "match_type": "regex_pattern",
  "valid_patterns": ["^\\d+\\.\\d{2}$"],
  "required_elements": ["USD"],
  "forbidden_elements": ["approximately"]
}
```

**3. `excel_cell_value`** - Check specific cell in output Excel file

```json
{
  "match_type": "excel_cell_value",
  "cell": "E27",
  "expected": 1250.5,
  "tolerance": 0.01,
  "sheet": "Waterfall"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `cell` | Yes | Cell reference (e.g., "A3", "AA100") |
| `expected` | Yes | Expected numeric value |
| `tolerance` | No | Allowed difference (default: 0 = exact) |
| `sheet` | No | Sheet name (default: active sheet) |

### Match Type for `type: "llm_judge"`:

```json
{
  "type": "llm_judge",
  "core_concepts": ["preferred return", "catch-up", "carried interest"],
  "points": 15
}
```

### Optional Fields (all match types):

| Field | Description |
|-------|-------------|
| `gates_llm` | If true and fails, skip LLM judge criteria (saves cost) |
| `search_full_response` | Search raw response instead of parsed JSON field |
| `forbidden_elements` | Strings that must NOT appear |

### Using gates_llm with Excel tasks:

For Excel output tasks, put `gates_llm: true` on the **most important cell check**, not a
dummy A1 check. If the key output is wrong, skip LLM evaluation.

**Bad pattern** (brittle):
```json
"excel_output": {
  "cell": "A1",
  "expected": 0,
  "tolerance": 999999999,
  "gates_llm": true
}
```

**Good pattern** (use actual value check as gate):
```json
"key_result": {
  "cell": "E27",
  "expected": 5864,
  "tolerance": 1,
  "gates_llm": true
}
```

### Extracting accepted values from meta.yaml:

The `task.description` often contains the expected answer. Parse it to build
`accepted_values`:

- "The answer is USD16,477m" → `["16,477", "16477", "$16,477", "16,477m"]`
- "formula in row 140" → `["Row 140", "140", "L140", "M140"]`

## Step 4: Verify Alignment

Checklist:

- [ ] Every JSON output key in prompt.md has a matching criterion in rubric.json
- [ ] Programmatic criteria have clear, unambiguous accepted values
- [ ] Points sum to total_points (usually 100)
- [ ] gates_llm is true for objective criteria that should block LLM evaluation
      on failure
- [ ] input_type matches input handling (web tasks have no input files)
- [ ] category array contains valid IB domains for what the task tests
- [ ] For Excel output tasks: use `excel_cell_value` match type to verify key cells

## Examples by Task Type

### fix-error

- Prompt: Describe the error symptoms, provide diagnostic methodology
- Rubric: Programmatic checks for error location + fix, LLM judge for explanation

### summarise

- Prompt: Specify focus areas and structure requirements
- Rubric: Primarily LLM judge criteria for qualitative assessment

### extraction

- Prompt: Specify exact data points needed and format requirements
- Rubric: Programmatic checks for extracted values, LLM judge for methodology

### creating

- Prompt: If Excel output required, explicitly state "Save and return the Excel workbook"
- Rubric: Use `excel_cell_value` match type to verify key output cells
