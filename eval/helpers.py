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


@dataclass
class Task:
    """Represents a single evaluation task."""
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


def load_task(task_dir: Path) -> Task:
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

    # Read rubric (optional)
    rubric_path = task_dir / "rubric.json"
    rubric = {}
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
    filter_pattern: str = None
) -> list[Task]:
    """Discover and load tasks from the tasks directory.

    Args:
        tasks_dir: Path to tasks directory. Defaults to eval/tasks/
        task_ids: Optional list of specific task IDs to load (e.g., ["e-001"])
        filter_pattern: Optional prefix filter (e.g., "e-" for easy tasks)

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
            task = load_task(task_path)
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
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


class AnthropicRunner:
    """Run tasks against Anthropic Claude models."""

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

    def run(self, task: Task, xlsx_json: dict = None) -> LLMResponse:
        """Execute a task against Claude."""
        # Build message content
        content = []

        # Add xlsx data as text if provided
        if xlsx_json:
            xlsx_text = json.dumps(xlsx_json, indent=2)
            content.append({
                "type": "text",
                "text": f"## Excel File Data\n\n```json\n{xlsx_text}\n```"
            })

        # Add the prompt
        content.append({
            "type": "text",
            "text": task.prompt
        })

        # Make API call
        start = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}]
        )
        latency_ms = (time.time() - start) * 1000

        # Extract response text
        raw_text = response.content[0].text

        # Try to parse JSON from response
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
    """Run tasks against OpenAI models."""

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

    def run(self, task: Task, xlsx_json: dict = None) -> LLMResponse:
        """Execute a task against OpenAI."""
        # Build message content
        content_parts = []

        # Add xlsx data as text if provided
        if xlsx_json:
            xlsx_text = json.dumps(xlsx_json, indent=2)
            content_parts.append(f"## Excel File Data\n\n```json\n{xlsx_text}\n```\n\n")

        # Add the prompt
        content_parts.append(task.prompt)

        full_content = "".join(content_parts)

        # Make API call
        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": full_content}]
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
    """Create a timestamped run directory."""
    if base_dir is None:
        base_dir = Path(__file__).parent / "results"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize model name for filesystem
    model_safe = model.replace("/", "-").replace(":", "-")
    run_dir = base_dir / f"{timestamp}_{model_safe}"

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "responses").mkdir(exist_ok=True)
    (run_dir / "scores").mkdir(exist_ok=True)

    return run_dir
