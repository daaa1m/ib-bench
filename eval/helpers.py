"""
Shared utilities for the IB-bench evaluation pipeline.
"""

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass
class Task:
    """Represents a SINGLE evaluation task."""

    id: str
    task_dir: Path
    task_type: str
    category: str
    description: str
    evaluation_type: str
    prompt: str
    rubric: dict
    input_files: list[Path]


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    raw_text: str
    parsed_json: dict | None
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


def load_task(task_dir: Path, include_rubric: bool = True) -> Task:
    """Load a single task from a directory."""
    # Parse meta.yaml
    meta_path = task_dir / "meta.yaml"
    with open(meta_path) as f:
        meta = yaml.safe_load(f)

    task_meta = meta.get("task", {})
    eval_meta = meta.get("evaluation", {})

    # Read prompt
    prompt_path = task_dir / "prompt.md"
    prompt = prompt_path.read_text()

    # Read rubric (only if needed for scoring)
    rubric = {}
    if include_rubric:
        rubric_path = task_dir / "rubric.json"
        if rubric_path.exists():
            with open(rubric_path) as f:
                rubric = json.load(f)

    # Find input files (glob pattern: input*.*)
    input_files = list(task_dir.glob("input*.*"))

    return Task(
        id=task_meta.get("id"),
        task_dir=task_dir,
        task_type=task_meta.get("type"),
        category=task_meta.get("category"),
        description=task_meta.get("description", ""),
        evaluation_type=eval_meta.get("type", "programmatic"),
        prompt=prompt,
        rubric=rubric,
        input_files=input_files,
    )


def load_tasks(
    tasks_dir: Path = None,
    task_ids: list[str] = None,
    filter_pattern: str = None,
    include_rubric: bool = True,
) -> list[Task]:
    """Discover and load tasks from the tasks directory.

    Args:
        tasks_dir: Path to tasks directory. Defaults to eval/tasks/
        task_ids: Optional list of specific task IDs to load (e.g., ["e-001"])
        filter_pattern: Optional prefix filter (e.g., "e-" for easy tasks)
        include_rubric: Whether to load rubric.json (only needed for scoring)

    Returns:
        List of Task objects.
    """
    if tasks_dir is None:
        tasks_dir = Path(__file__).parent / "tasks"

    tasks = []

    for task_path in sorted(tasks_dir.iterdir()):
        if not task_path.is_dir():
            continue

        # Extract task ID from directory name (strip -done/-working suffixes)
        dir_name = task_path.name
        task_id = dir_name.replace("-done", "").replace("-working", "")

        # Filter by task_ids if provided
        if task_ids and task_id not in task_ids:
            continue

        # Filter by pattern if provided
        if filter_pattern and not task_id.startswith(filter_pattern):
            continue

        try:
            task = load_task(task_path, include_rubric=include_rubric)
            tasks.append(task)
        except (FileNotFoundError, ValueError) as e:
            print(f"Warning: Skipping {task_path.name}: {e}")

    return tasks


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from response text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON in code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


class AnthropicRunner:
    """Run tasks against Anthropic Claude models with code execution for Excel files."""

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def run(self, task: Task, input_file: Path = None) -> LLMResponse:
        """Execute a task against Claude with file upload via Files API."""
        if input_file:
            return self._run_with_file(task, input_file)
        else:
            return self._run_text_only(task)

    def _run_text_only(self, task: Task) -> LLMResponse:
        """Run task with text prompt only (no Excel file)."""
        start = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": task.prompt}],
        )
        latency_ms = (time.time() - start) * 1000

        raw_text = response.content[0].text
        parsed_json = _extract_json(raw_text)

        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
        )

    def _run_with_file(self, task: Task, input_file: Path) -> LLMResponse:
        """Run with file upload - uploads file via Files API and uses code execution."""
        # Upload the file
        print(f"  Uploading {input_file.name} to Files API...")
        with open(input_file, "rb") as f:
            file_obj = self.client.beta.files.upload(file=f)

        # Build message with file reference
        content = [
            {"type": "container_upload", "file_id": file_obj.id},
            {"type": "text", "text": task.prompt},
        ]

        # Call with code execution tool
        start = time.time()
        response = self.client.beta.messages.create(
            model=self.model,
            betas=["code-execution-2025-08-25", "files-api-2025-04-14"],
            max_tokens=16384,
            messages=[{"role": "user", "content": content}],
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
        )
        latency_ms = (time.time() - start) * 1000

        # Extract text from response (may have multiple content blocks)
        raw_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw_text += block.text + "\n"

        parsed_json = _extract_json(raw_text)

        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
        )


class OpenAIRunner:
    """Run tasks against OpenAI models (converts Excel to JSON since no code execution)."""

    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def run(self, task: Task, input_file: Path = None) -> LLMResponse:
        """Execute a task against OpenAI (converts xlsx to JSON, PDFs not supported)."""
        from xlsx_converter import xlsx_to_json

        # Build message content
        content_parts = []

        # Handle input file
        if input_file:
            if input_file.suffix in [".xlsx", ".xls"]:
                print(f"  Converting {input_file.name} to JSON for OpenAI...")
                xlsx_data = xlsx_to_json(str(input_file))
                xlsx_text = json.dumps(xlsx_data, indent=2)
                content_parts.append(
                    f"## Excel File Data\n\n```json\n{xlsx_text}\n```\n\n"
                )
            else:
                print(f"  Warning: {input_file.suffix} files not supported for OpenAI")

        # Add the prompt
        content_parts.append(task.prompt)

        full_content = "".join(content_parts)

        # Make API call
        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": full_content}],
        )
        latency_ms = (time.time() - start) * 1000

        # Extract response
        raw_text = response.choices[0].message.content
        parsed_json = _extract_json(raw_text)

        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            latency_ms=latency_ms,
        )


def get_runner(provider: str, model: str = None):
    """Factory function to get the appropriate runner."""
    if provider == "anthropic":
        return AnthropicRunner(model=model) if model else AnthropicRunner()
    elif provider == "openai":
        return OpenAIRunner(model=model) if model else OpenAIRunner()
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_run_directory(model: str, base_dir: Path = None) -> Path:
    """Create a timestamped run directory under results/responses/."""
    if base_dir is None:
        base_dir = Path(__file__).parent / "results" / "responses"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize model name for filesystem
    model_safe = model.replace("/", "-").replace(":", "-")
    run_dir = base_dir / f"{timestamp}_{model_safe}"

    run_dir.mkdir(parents=True, exist_ok=True)

    return run_dir


class LLMJudge:
    """LLM-as-judge scorer using Claude with Files API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def score(self, rubric: dict, source_file: Path, response_text: str) -> dict:
        """Score a response against rubric criteria.

        Args:
            rubric: Rubric dict with criteria list
            source_file: Path to source document (PDF, xlsx, etc.)
            response_text: The response text to evaluate

        Returns:
            {
                "scores": {
                    "criterion_id": {"score": 0.0-1.0, "reasoning": "..."},
                    ...
                },
                "weighted_total": 0.85
            }
        """
        # Format criteria for the prompt
        criteria = rubric.get("criteria", [])
        criteria_text = "\n".join(
            [
                f"- **{c['id']}** (weight: {c['weight']}): {c['description']}"
                for c in criteria
            ]
        )

        # Upload source file via Files API
        print(f"  Uploading {source_file.name} to Files API for judging...")
        with open(source_file, "rb") as f:
            file_obj = self.client.beta.files.upload(file=f)

        # Build judge prompt
        judge_prompt = f"""You are an expert evaluator for investment banking work products.

## Task
Evaluate the following response against the provided criteria. You have access to the original source document.

## Response to Evaluate
{response_text}

## Evaluation Criteria
{criteria_text}

## Instructions
1. First, read and understand the source document
2. Then evaluate the response against each criterion
3. Score each criterion on a 0-1 scale (0 = completely fails, 1 = perfect)
4. Provide brief reasoning for each score

Return your evaluation as JSON in this exact format:
```json
{{
  "scores": {{
    "criterion_id": {{
      "score": 0.0,
      "reasoning": "brief explanation"
    }}
  }}
}}
```

Include all criteria: {", ".join(c["id"] for c in criteria)}"""

        # Build message with file reference
        content = [
            {"type": "container_upload", "file_id": file_obj.id},
            {"type": "text", "text": judge_prompt},
        ]

        # Call with code execution tool for PDF analysis
        start = time.time()
        response = self.client.beta.messages.create(
            model=self.model,
            betas=["code-execution-2025-08-25", "files-api-2025-04-14"],
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
        )
        latency_ms = (time.time() - start) * 1000
        print(f"  Judge completed in {latency_ms:.0f}ms")

        # Extract text from response
        raw_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw_text += block.text + "\n"

        # Parse JSON from response
        parsed = _extract_json(raw_text)
        if not parsed:
            print(f"  Warning: Could not parse judge response as JSON")
            return {"scores": {}, "weighted_total": 0.0, "raw_response": raw_text}

        # Calculate weighted total
        scores = parsed.get("scores", {})
        weighted_total = 0.0
        total_weight = 0.0

        for criterion in criteria:
            cid = criterion["id"]
            weight = criterion.get("weight", 0)
            if cid in scores:
                score_val = scores[cid].get("score", 0)
                weighted_total += score_val * weight
                total_weight += weight

        if total_weight > 0:
            weighted_total = (
                weighted_total / total_weight * total_weight
            )  # Already weighted

        parsed["weighted_total"] = weighted_total
        return parsed
