# WORKPLAN.md

Remaining code improvements for IB-bench infrastructure.

---

## Completed

- [x] Hybrid evaluation with gated LLM scoring
- [x] New rubric format with `type` per criterion and `gates_llm` flag
- [x] Evaluation type derived from rubric (not meta.yaml)
- [x] Point-based scoring system
- [x] Updated e-001, e-002, e-003 rubrics to new format
- [x] CLAUDE.md documentation updates
- [x] New meta.yaml format with `input-file-original`, `input-file-used`, `notes`
- [x] `--model` argument now required (no defaults)
- [x] Created `create-ib-task` skill for task creation (`.claude/skills/create-ib-task.md`)
- [x] Removed `evaluation_type` from Task dataclass (derived from rubric)

---

## Priority 1: OpenAI Files API + Assistants

**File:** `eval/helpers.py`, class `OpenAIRunner`

**Current:** Only xlsx→JSON conversion. No native file support.

**Target:** Match `AnthropicRunner` pattern using OpenAI Files API + Assistants API.

**Implementation:**

```python
class OpenAIRunner:
    def __init__(self, model: str):
        if not model:
            raise ValueError("model is required for OpenAIRunner")
        self.client = openai.OpenAI()
        self.model = model
        self.assistant_id = None

    def _get_or_create_assistant(self) -> str:
        """Create assistant with file_search and code_interpreter."""
        if self.assistant_id:
            return self.assistant_id

        assistant = self.client.beta.assistants.create(
            name="IB-bench Evaluator",
            model=self.model,
            tools=[
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ]
        )
        self.assistant_id = assistant.id
        return self.assistant_id

    def _upload_file(self, path: Path) -> str:
        """Upload file to OpenAI Files API."""
        with open(path, "rb") as f:
            file = self.client.files.create(file=f, purpose="assistants")
        return file.id

    def run(self, task: Task, input_file: Path = None) -> LLMResponse:
        """Run task using Assistants API with file attachments."""
        assistant_id = self._get_or_create_assistant()

        # Upload input files
        file_ids = [self._upload_file(f) for f in task.input_files] if task.input_files else []

        # Create thread with attachments
        thread = self.client.beta.threads.create(
            messages=[{
                "role": "user",
                "content": task.prompt,
                "attachments": [
                    {"file_id": fid, "tools": [{"type": "file_search"}, {"type": "code_interpreter"}]}
                    for fid in file_ids
                ]
            }]
        )

        # Run and poll for completion
        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        # Get response
        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        response_text = messages.data[0].content[0].text.value

        # Cleanup uploaded files
        for fid in file_ids:
            self.client.files.delete(fid)

        return LLMResponse(
            raw_text=response_text,
            parsed_json=_extract_json(response_text),
            model=self.model,
            input_tokens=run.usage.prompt_tokens,
            output_tokens=run.usage.completion_tokens,
            latency_ms=0,  # TODO: track actual latency
        )
```

**File type handling:**
| Type | OpenAI Tool |
|------|-------------|
| `.pdf` | file_search |
| `.xlsx` | code_interpreter |
| `.png/.jpg` | code_interpreter (vision) |

---

## Priority 2: Implement status.py

**Create:** `eval/status.py`

**Commands:**
```bash
uv run python eval/status.py              # Task readiness
uv run python eval/status.py --runs       # Recent runs
```

**Implementation:**

```python
def get_task_status(tasks_dir: Path) -> list[dict]:
    """Check each task directory for required files."""
    statuses = []
    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir():
            continue

        has_prompt = (task_dir / "prompt.md").exists()
        has_rubric = (task_dir / "rubric.json").exists()
        input_files = list(task_dir.glob("input*.*"))

        status = "complete" if has_prompt and has_rubric and input_files else "incomplete"
        missing = []
        if not has_prompt: missing.append("prompt.md")
        if not has_rubric: missing.append("rubric.json")
        if not input_files: missing.append("input files")

        statuses.append({
            "task_id": task_dir.name,
            "status": status,
            "missing": missing,
            "input_count": len(input_files),
        })
    return statuses

def get_run_status(results_dir: Path) -> list[dict]:
    """List recent runs with pass/fail counts."""
    runs = []
    responses_dir = results_dir / "responses"
    scores_dir = results_dir / "scores"

    for run_dir in sorted(responses_dir.iterdir(), reverse=True)[:10]:
        run_id = run_dir.name
        response_count = len(list(run_dir.glob("*.json"))) - 1  # exclude config.json

        # Check if scored
        score_dir = scores_dir / run_id
        summary_file = score_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)
            passed = summary.get("passed", 0)
            total = summary.get("total", 0)
            scored = True
        else:
            passed = total = 0
            scored = False

        runs.append({
            "run_id": run_id,
            "responses": response_count,
            "passed": passed,
            "total": total,
            "scored": scored,
        })
    return runs
```

---

## Priority 3: Parallel Task Execution

**File:** `eval/run.py`

**Add:** `--parallel N` flag (default: 1 for sequential)

**Implementation approach:**
- Use `asyncio` with semaphore for rate limiting
- Respect API rate limits: Anthropic ~50 RPM, OpenAI varies
- Graceful per-task failure handling
- Progress bar for concurrent tasks

```python
async def run_task_async(task, runner, semaphore):
    async with semaphore:
        # Run task (may need to wrap sync runner in executor)
        return await asyncio.to_thread(runner.run, task, task.input_files[0] if task.input_files else None)

async def run_tasks_parallel(tasks, runner, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks_coros = [run_task_async(t, runner, semaphore) for t in tasks]
    return await asyncio.gather(*tasks_coros, return_exceptions=True)
```

---

## Priority 4: Quality Improvements

### 4.1 Rubric Versioning

Add rubric hash to score output for audit trail:

```python
import hashlib

def get_rubric_hash(rubric: dict) -> str:
    return hashlib.sha256(json.dumps(rubric, sort_keys=True).encode()).hexdigest()[:8]
```

Include in score output:
```json
{
  "rubric_hash": "a1b2c3d4",
  "scored_at": "2025-12-21T12:00:00Z"
}
```

### 4.2 Better Error Messages

- Clear errors when task files missing
- Show expected vs actual keys in scoring mismatches
- Validate rubric format on load

---

## Implementation Order

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | OpenAI Files API + Assistants | Medium | High - model parity |
| 2 | Implement `status.py` | Small | High - workflow |
| 3 | Add parallel execution | Medium | High - time savings |
| 4 | Rubric versioning | Small | Low - audit trail |

---

## Files to Create

| File | Purpose |
|------|---------|
| `eval/status.py` | Task and run status overview |

## Files to Modify

| File | Changes |
|------|---------|
| `eval/helpers.py` | OpenAI Files API + Assistants runner |
| `eval/run.py` | Add --parallel flag |
