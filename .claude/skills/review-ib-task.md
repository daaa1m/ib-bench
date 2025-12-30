---
name: review-ib-task
description: Use when reviewing IB-bench task quality - checks completeness, alignment, content quality, and consistency before tasks are finalized
---

# Reviewing IB-bench Task Quality

This skill systematically reviews task folders for quality issues before finalization.

## Checklist

**Execute each check and report PASS/FAIL with specific findings.**

### 1. Structural Completeness

Check that required files exist:
- [ ] `meta.yaml` exists
- [ ] `prompt.md` exists
- [ ] `rubric.json` exists
- [ ] Input files exist IF `input-file-original` is not None in meta.yaml

Check meta.yaml structure:
- [ ] Has `# Documentation` comment at top
- [ ] `task.id` matches folder name (e.g., `e-001` in `eval/tasks/e-001/`)
- [ ] `task.type` is valid (`fix-error`, `summarise`, `extraction`, `creating`)
- [ ] `task.category` is valid (`excel`, `pdf`, `web`)
- [ ] No TODO comments remain in meta.yaml

Check `task.description` quality (must include ALL of these):
- [ ] Brief explanation of what the task requires
- [ ] The error or problem (if applicable, e.g., for fix-error tasks)
- [ ] The expected answer with specific values
- [ ] What capability/skill the task aims to test

Check `prompt.notes`:
- [ ] Present and describes any special instructions or context given to LLM

Check `input.input-file-original`:
- [ ] If path(s) specified, verify file(s) exist at path(s)
- [ ] If None, confirm this is intentional (e.g., web tasks)
- [ ] Can be single string, list of strings, or None

Check `input.notes`:
- [ ] Documents any modifications made to the original file(s)
- [ ] Highlights anything notable about the input (format quirks, edge cases, etc.)

### 2. Criterion ID Alignment

**For programmatic criteria:** Criterion IDs must match prompt JSON output keys exactly (to extract and check values).

**For pure LLM-judge tasks:** Criteria can be evaluation dimensions (e.g., `accuracy`, `completeness`) that assess the quality of an output field like `summary`. This is acceptable.

**Extra prompt keys:** Prompt can have JSON keys not scored in rubric (e.g., `reasoning`, `audit_steps_followed`) - useful for diagnosing LLM thinking.

Cross-check prompt.md and rubric.json:
- [ ] Every **programmatic** criterion ID has a matching JSON key in prompt output
- [ ] For **llm_judge-only** tasks: criteria can be evaluation dimensions applied to output fields
- [ ] Rubric doesn't reference fields that don't exist in prompt output

### 3. Rubric Quality

Check rubric.json structure:
- [ ] `task_id` matches folder name
- [ ] `version` is present
- [ ] Points sum exactly to `total_points`
- [ ] Each criterion has required fields: `description`, `type`, `points`

Check programmatic criteria:
- [ ] `match_type` is valid (`substring_one_of` or `regex_pattern`)
- [ ] `accepted_values` includes reasonable format variations
- [ ] For numbers: includes with/without commas, $, units
- [ ] For cells: includes row-only and cell references

Check llm_judge criteria:
- [ ] `core_concepts` array is present and non-empty
- [ ] Points for llm_judge criteria ≤ 15% of total (usually)

Check gating:
- [ ] `gates_llm: true` only appears when rubric has llm_judge criteria
- [ ] Gating criteria are objective (not dependent on subjective assessment)

### 4. Prompt Quality

Check structure:
- [ ] Has `## Task` section with clear role and objective
- [ ] Has `## Methodology & Process` with numbered steps
- [ ] Has `## Constraints and Negative Constraints` section
- [ ] Has `## Output Format` with JSON example

Check content:
- [ ] Task description is unambiguous
- [ ] Negative constraints prevent common LLM mistakes
- [ ] "NO conversational filler" included
- [ ] JSON format uses backticks correctly

### 5. Category-Input Consistency

Verify inputs match category:
- [ ] If `input-file-original` is not None:
  - `excel` category → has `input*.xlsx` file(s)
  - `pdf` category → has `input*.pdf` file(s)
- [ ] If `input-file-original` is None → no input files required
- [ ] `web` category typically has `input-file-original: None`

### 6. Expected Answer Traceability

For programmatic criteria:
- [ ] Each accepted value can be traced to meta.yaml description
- [ ] No values appear "invented" without source
- [ ] For extraction tasks: values are verifiable from input files

### 7. Coherence Check

Verify all components tie together and make sense:
- [ ] meta.yaml description aligns with what prompt.md asks the LLM to do
- [ ] Input file(s) contain the data needed to complete the task described
- [ ] Rubric criteria evaluate what the prompt actually asks for
- [ ] Expected answers in meta.yaml match rubric accepted_values
- [ ] Task difficulty (e/m/h prefix) is appropriate for the task complexity
- [ ] No contradictions between files (e.g., prompt asks for X but rubric scores Y)

## Output Format

Report findings as:

```markdown
## Task Review: {task-id}

### Summary
- **Status**: PASS / NEEDS WORK / FAIL
- **Issues Found**: {count}

### Detailed Findings

#### Structural Completeness
- [PASS/FAIL] {check}: {finding}

#### Criterion ID Alignment
- [PASS/FAIL] {check}: {finding}

#### Rubric Quality
- [PASS/FAIL] {check}: {finding}

#### Prompt Quality
- [PASS/FAIL] {check}: {finding}

#### Category-Input Consistency
- [PASS/FAIL] {check}: {finding}

#### Expected Answer Traceability
- [PASS/FAIL] {check}: {finding}

#### Coherence Check
- [PASS/FAIL] {check}: {finding}

### Recommended Fixes
1. {fix description}
2. {fix description}
```

## Common Issues

| Issue | Example | Fix |
|-------|---------|-----|
| Mismatched programmatic criterion | Prompt has `answer`, rubric has `final_answer` | Rename to match |
| LLM-judge dimensions (not an issue) | Rubric has `accuracy`, `completeness` for `summary` field | Acceptable for pure llm_judge tasks |
| Points don't sum | 42+43+14=99, total_points=100 | Adjust point allocation |
| Missing format variations | Only `"16477"`, missing `"16,477"` | Add comma/currency/unit variants |
| TODO in meta.yaml | `#TODO add full path` | Complete the TODO |
| gates_llm without llm_judge | gates_llm=true but no llm_judge criteria | Remove gates_llm |
| Input files missing | input-file-original is set but files don't exist | Add input files or set to None |
| Incoherent task | Prompt asks for summary but rubric only scores numbers | Align prompt and rubric |
| Meta/rubric mismatch | meta.yaml says answer is X, rubric accepts Y | Sync expected answers |
| Missing description elements | Description only says "Extract data" | Add error, expected answer, capability tested |

## Quick Validation Script

For fast structural checks, run in task directory:

```bash
# Check files exist
ls meta.yaml prompt.md rubric.json 2>/dev/null || echo "Missing required files"

# Check points sum (requires jq)
jq '.criteria | to_entries | map(.value.points) | add' rubric.json

# Check for TODOs
grep -i "TODO" meta.yaml && echo "TODOs found in meta.yaml"

# List criterion IDs
jq '.criteria | keys' rubric.json
```

## Meta.yaml Reference

```yaml
# Documentation
task:
  id: e-001                    # Must match folder name
  type: fix-error              # fix-error | summarise | extraction | creating
  category: excel              # excel | pdf | web
  description:                 # Multi-line string with ALL of:
    "Brief explanation. Error/problem. Expected answer with values.
    What capability this tests."

prompt:
  notes: "Special instructions given to LLM"

input:
  input-file-original: "$human/file.xlsx"  # Path, list of paths, or None
  notes: "Modifications or notable aspects of input"
```

**Path alias:** `$human` = `data-factory/human-generated/`
