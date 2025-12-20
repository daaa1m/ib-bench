# TODO / Future Improvements

## Pinned for Later

### Rubric Versioning
Track which version of a rubric was used to produce each score. Consider adding a hash or version field to score outputs so changes to rubrics are traceable.

### Missing status.py
The architecture doc references `status.py` for checking task/run progress, but it doesn't exist yet.

### Parallel Task Execution
Running 50 tasks sequentially at 1-5 min each is slow. Add concurrency support with rate limiting for faster runs.

## Open Questions

### Excel File Output
How should the LLM return modified/created Excel files?

Options:
1. **Python code output** - LLM returns openpyxl code, harness executes it
2. **Cell-by-cell JSON** - LLM returns `{"A1": "=SUM(B1:B10)", "A2": 100, ...}`, harness applies changes
3. **computer_use** - Use Anthropic's computer use API to control a sandboxed desktop (complex)
4. **Code execution sandbox** - Similar to how claude.ai creates files (may need custom implementation)

### Excel File Input via API

| Provider | Files API | xlsx Support | Notes |
|----------|-----------|--------------|-------|
| Anthropic | Yes (`files-api-2025-04-14`) | **No** | xlsx explicitly unsupported, must convert to text |
| OpenAI | Yes | **No** | Must convert to CSV |
| Gemini | Yes (File Search) | **Yes** | Native support up to 100MB |

**Gemini is the only provider with native xlsx API support.**

For Anthropic/OpenAI, need xlsx-to-structured-format converter. Options:
1. **Structured JSON** - Parse xlsx preserving formulas, cell refs, sheet structure
2. **Markdown with formulas** - Custom format showing both values and formulas
3. ~~CSV~~ - Not suitable (loses formulas and multi-sheet structure)
