## Core Principles

1. **Make minimal, surgical changes when possible**
2. **Never compromise type safety**
3. **Abstractions**: consciously constrained, pragmatically parameterised,
   doggedly documented
4. **One way to do things**: if there are two ways to do something in your
   codebase, pick one and delete the other—unless there's a genuine reason for
   both

---

## The 80% Rule

Handle the common path clearly. Don't contort code to cover every edge case.

For edge cases:

- Handle simply if the fix is trivial
- Document with a comment if it's complex ("does not handle X")
- Raise an informative error if it's unrecoverable

The goal is **audit-able honesty**, not false completeness.

---

## Functions as Contracts

Write functions so they can be verified at the boundary—inputs in, outputs out.

### Type the boundaries

```python
def calculate_irr(
    cashflows: list[float],
    periods_per_year: int = 1,
) -> float:
```

If the types are right and the output is right, the implementation is right.

### Docstrings state scope, not mechanics

Use RST format. Say what the function handles and what it doesn't.

```python
def calculate_irr(cashflows: list[float], periods_per_year: int = 1) -> float:
    """
    IRR via Newton-Raphson.

    :param cashflows: Cash flows, first should be negative (investment)
    :param periods_per_year: Compounding periods, defaults to annual
    :returns: IRR as decimal (0.15 = 15%)
    :raises ValueError: If no solution converges

    Assumes: At least one positive return after initial investment.
    Does not handle: Multiple sign changes, irregular periods.
    """
```

This lets you trust without reading—you know the contract and its limits.

### One function, one job

If you can't describe what a function does in one sentence, split it.

---

## Functional Patterns

Steal the useful bits from functional programming without going full FP.

### Default to pure functions

For logic and transformations, prefer functions where the same input always
gives the same output. These are trivial to test and verify at the boundary.

```python
# Pure - predictable, testable
def calculate_score(example: Example, weights: Weights) -> float:
    ...

# Not pure - depends on external state
def calculate_score(example: Example) -> float:
    weights = load_weights_from_db()  # side effect hidden inside
    ...
```

### Data flows through pipelines

Structure work as: load → transform → transform → output. Each step takes data
in, produces data out.

```python
examples = load_examples(path)
valid = filter_valid(examples)
scored = score_examples(valid, model)
result = compute_metrics(scored)
```

Each function is testable in isolation. You can verify at each boundary.

### Immutable data where practical

Use `frozen=True` dataclasses for data flowing through your pipeline. This
prevents accidental mutation.

```python
@dataclass(frozen=True)
class Example:
    id: str
    prompt: str
    expected: str
```

### Write idiomatically

Don't fight the language or libraries. If pandas wants mutation, let it—but keep
the mutation contained. **Important: Code should look like normal Python when
writing Python (and likewise for Typescript, Svelte etc.), not a functional
programming exercise.**

---

## Side Effects

Pure functions are ideal but not always possible. When side effects are
necessary:

### Isolate them

Keep side effects (API calls, file I/O, database writes) at the edges. Core
logic should be pure and testable.

```python
# Pure - easy to verify
def build_request_payload(deal: Deal, options: ExportOptions) -> dict:
    ...

# Side effect - isolated
def send_to_api(payload: dict) -> ApiResponse:
    ...

# Orchestration - calls both
def export_deal(deal: Deal, options: ExportOptions) -> ApiResponse:
    payload = build_request_payload(deal, options)
    return send_to_api(payload)
```

### Name them honestly

Functions with side effects should have names that make this obvious: `send_`,
`save_`, `fetch_`, `write_`, `delete_`.

---

## Errors

Errors should help, not just fail.

```python
# Bad
raise ValueError("Invalid input")

# Good
raise ValueError(
    f"Expected positive EBITDA, got {ebitda:,.0f}. "
    f"Check financials for {company_name}."
)
```

Tell the user what to do next in your error message and how to debug.

---

## Modifying Existing Code

- **Understand before changing** — read surrounding code, match existing
  patterns
- **Minimal diffs** — smaller changes are easier to verify and revert
- **Don't refactor while fixing** — one purpose per change

---

## Comments

Comments explain **why**, not **what**. The code shows what happens.

```python
# Bad: restates the code
# Calculate the sum
total = sum(values)

# Good: explains the reasoning
# Using sum of absolutes because negative values indicate reversals, not losses
total = sum(abs(v) for v in values)
```

## Quick Reference

| Situation                 | Approach                                                       |
| ------------------------- | -------------------------------------------------------------- |
| Edge case                 | Handle if trivial, document if complex, error if unrecoverable |
| Side effect needed        | Isolate it, name it honestly                                   |
| Function getting complex  | Split into smaller pure functions                              |
| Not sure if code is right | Check types match, test with representative inputs             |
| Modifying existing code   | Smallest change that works                                     |
| Two ways to do something  | Pick one, delete the other (unless there's a good reason)      |
