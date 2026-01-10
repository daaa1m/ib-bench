---
name: explain-code
description: Find "@agent-explain" markers and add explanatory comments. Optionally specify a file path.
---

# Explain Code Markers

This skill finds `@agent-explain` markers in the codebase and adds explanatory comments.

## Workflow

1. **Find all markers**: Search for `@agent-explain` comments
2. **For each marker**: Read surrounding context (20-30 lines above/below)
3. **Add comment below**: Explain WHY the code exists, with brief WHAT

## Comment Style

Comments should:
- **Focus on WHY** - What problem does this solve? What would break without it?
- **Brief WHAT** - One line on what the code does
- **Answer specific questions** - If marker includes a question, address it directly
- **Stay concise** - 1-3 lines max
- **NOT delete** the `@agent-explain` marker (user reviews before cleanup)

## Handling Specific Questions

If the marker includes a question, answer it directly:

```python
# @agent-explain why cast to bytes?
content = cast(bytes, file_content)
```

Becomes:

```python
# @agent-explain why cast to bytes?
# file_content can be bytes or a file-like object depending on API version.
# Cast tells type checker we've handled both cases above.
content = cast(bytes, file_content)
```

## Example

Before:
```python
# @agent-explain
if container_id:
    container_files = self.client.beta.files.list(container_id=container_id)
```

After:
```python
# @agent-explain
# Code execution runs in an ephemeral container. Files created there vanish
# on cleanup - we must retrieve them before that happens.
if container_id:
    container_files = self.client.beta.files.list(container_id=container_id)
```

## Usage

- `/explain-code` - search entire codebase
- `/explain-code path/to/file.py` - search only specified file

## Execution Steps

1. If file specified: `grep -n "@agent-explain" <file>`
   Otherwise: `grep -rn "@agent-explain" .`
2. For each match:
   - Read the file context around the marker
   - Understand what the code block does and WHY it exists
   - Add 1-3 line comment immediately below the marker
3. Report what was commented

## Do NOT

- Delete the `@agent-explain` marker
- Write obvious comments ("loop through items")
- Explain language syntax
- Add docstrings (just inline comments)
