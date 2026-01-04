"""
Shared utilities for the IB-bench evaluation pipeline.
"""

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

import yaml
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Type Definitions
# -----------------------------------------------------------------------------

Provider = Literal["anthropic", "openai", "gemini"]
CriterionType = Literal["programmatic", "llm_judge", "human_judge"]
MatchType = Literal["substring_one_of", "regex_pattern"]


class RubricCriterion(TypedDict, total=False):
    """Single criterion in a rubric. All fields optional due to variation."""

    description: str
    type: CriterionType
    match_type: MatchType
    points: int
    accepted_values: list[str]
    valid_patterns: list[str]
    required_elements: list[str]
    forbidden_elements: list[str]
    gates_llm: bool
    search_full_response: bool
    core_concepts: list[str]


class Rubric(TypedDict, total=False):
    """Rubric structure loaded from rubric.json."""

    task_id: str
    version: str
    total_points: int
    criteria: dict[str, RubricCriterion]


class TaskMeta(TypedDict, total=False):
    """Task metadata from meta.yaml -> task section."""

    id: str
    title: str
    type: str
    category: str | list[str]
    input_type: str
    description: str


load_dotenv(Path(__file__).parent.parent / ".env")


class JudgeParseError(Exception):
    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response


def retry_on_rate_limit(max_retries: int = 3, initial_wait: int = 60):
    """Decorator to retry on rate limit errors with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_wait: Initial wait time in seconds (doubles each retry)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            wait_time = initial_wait

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error (429)
                    if "429" in error_str or "rate_limit" in error_str.lower():
                        last_exception = e
                        if attempt < max_retries:
                            print(
                                f"  Rate limited. Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})..."
                            )
                            time.sleep(wait_time)
                            wait_time *= 2  # Exponential backoff
                        else:
                            print(
                                f"  Rate limited. Max retries ({max_retries}) exceeded."
                            )
                            raise
                    else:
                        # Not a rate limit error, raise immediately
                        raise

            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Retry loop completed without success or exception")

        return wrapper

    return decorator


@dataclass
class Task:
    """Represents a single evaluation task."""

    id: str
    task_dir: Path
    task_type: str
    category: str | list[str]
    description: str
    prompt: str
    rubric: Rubric
    input_files: list[Path]


def load_task(task_dir: Path, include_rubric: bool = True) -> Task:
    """Load a single task from a directory."""
    # Parse meta.yaml
    meta_path = task_dir / "meta.yaml"
    with open(meta_path) as f:
        meta = yaml.safe_load(f)

    # Skip if meta.yaml is not a proper dict (e.g., just a comment blurb)
    if not isinstance(meta, dict):
        raise ValueError(
            f"meta.yaml is not a valid task definition (got {type(meta).__name__})"
        )

    task_meta = meta.get("task", {})

    # Read prompt
    prompt_path = task_dir / "prompt.md"
    prompt = prompt_path.read_text()

    # Read rubric (only if needed for scoring)
    rubric: Rubric = cast(Rubric, {})
    if include_rubric:
        rubric_path = task_dir / "rubric.json"
        if rubric_path.exists():
            with open(rubric_path) as f:
                rubric = cast(Rubric, json.load(f))

    # Find input files (glob pattern: input*.*)
    input_files = list(task_dir.glob("input*.*"))

    return Task(
        id=task_meta.get("id"),
        task_dir=task_dir,
        task_type=task_meta.get("type"),
        category=task_meta.get("category"),
        description=task_meta.get("description", ""),
        prompt=prompt,
        rubric=rubric,
        input_files=input_files,
    )


def load_tasks(
    tasks_dir: Path | None = None,
    task_ids: list[str] | None = None,
    filter_pattern: str | None = None,
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

        task_id = task_path.name

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


def get_rubric_hash(rubric: Rubric) -> str:
    """Generate 8-char hash of rubric content for versioning."""
    content = json.dumps(rubric, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def _extract_json(text: str) -> dict[str, Any] | None:
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


def get_runner(provider: Provider, model: str):
    """Factory function to get the appropriate runner.

    Uses lazy import to avoid circular dependencies.
    """
    from runners import AnthropicRunner, GeminiRunner, OpenAIRunner

    if provider == "anthropic":
        return AnthropicRunner(model=model)
    elif provider == "openai":
        return OpenAIRunner(model=model)
    elif provider == "gemini":
        return GeminiRunner(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_run_directory(model: str, base_dir: Path | None = None) -> Path:
    """Create a timestamped run directory under responses/{model}/{run_id}."""
    if base_dir is None:
        base_dir = Path(__file__).parent / "responses"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize model name for filesystem
    model_safe = model.replace("/", "-").replace(":", "-")
    run_dir = base_dir / model_safe / timestamp

    run_dir.mkdir(parents=True, exist_ok=True)

    return run_dir
