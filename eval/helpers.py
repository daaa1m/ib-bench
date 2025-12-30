"""
Shared utilities for the IB-bench evaluation pipeline.
"""

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


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
                            print(f"  Rate limited. Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})...")
                            time.sleep(wait_time)
                            wait_time *= 2  # Exponential backoff
                        else:
                            print(f"  Rate limited. Max retries ({max_retries}) exceeded.")
                            raise
                    else:
                        # Not a rate limit error, raise immediately
                        raise

            raise last_exception
        return wrapper
    return decorator


@dataclass
class Task:
    """Represents a SINGLE evaluation task."""

    id: str
    task_dir: Path
    task_type: str
    category: str
    description: str
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

    # Skip if meta.yaml is not a proper dict (e.g., just a comment blurb)
    if not isinstance(meta, dict):
        raise ValueError(f"meta.yaml is not a valid task definition (got {type(meta).__name__})")

    task_meta = meta.get("task", {})

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


def normalize_criteria(criteria) -> list[dict]:
    """Normalize criteria to list format.

    Handles both formats:
    - Dict format: {"criterion_id": {...specs...}}
    - List format: [{"id": "criterion_id", ...specs...}]
    """
    if isinstance(criteria, dict):
        # Convert dict format to list format
        return [{"id": cid, **spec} for cid, spec in criteria.items()]
    return criteria  # Already a list


def get_rubric_hash(rubric: dict) -> str:
    """Generate 8-char hash of rubric content for versioning."""
    content = json.dumps(rubric, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:8]


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

    def __init__(self, api_key: str = None, model: str = None):
        if not model:
            raise ValueError("model is required for AnthropicRunner")
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

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] = None) -> LLMResponse:
        """Execute a task against Claude with file upload via Files API."""
        files = input_files or []
        if files:
            return self._run_with_files(task, files)
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

    def _run_with_files(self, task: Task, input_files: list[Path]) -> LLMResponse:
        """Run with file upload - uploads files via Files API and uses code execution."""
        # Upload all files
        file_ids = []
        for input_file in input_files:
            print(f"  Uploading {input_file.name} to Files API...")
            with open(input_file, "rb") as f:
                file_obj = self.client.beta.files.upload(file=f)
                file_ids.append(file_obj.id)

        # Build message with file references
        content = []
        for file_id in file_ids:
            content.append({"type": "container_upload", "file_id": file_id})
        content.append({"type": "text", "text": task.prompt})

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
    """Run tasks against OpenAI models using Files API + Assistants API."""

    def __init__(self, api_key: str = None, model: str = None):
        if not model:
            raise ValueError("model is required for OpenAIRunner")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = model
        self._client = None
        self._assistant_id = None

    @property
    def client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def _get_or_create_assistant(self) -> str:
        """Create assistant with file_search and code_interpreter tools."""
        if self._assistant_id:
            return self._assistant_id

        assistant = self.client.beta.assistants.create(
            name="IB-bench Evaluator",
            model=self.model,
            tools=[{"type": "file_search"}, {"type": "code_interpreter"}],
        )
        self._assistant_id = assistant.id
        return self._assistant_id

    def _upload_file(self, path: Path) -> str:
        """Upload file to OpenAI Files API."""
        with open(path, "rb") as f:
            file = self.client.files.create(file=f, purpose="assistants")
        return file.id

    def _get_tools_for_file(self, path: Path) -> list[dict]:
        """Determine which tools to use based on file type."""
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return [{"type": "file_search"}]
        elif suffix in [".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg"]:
            return [{"type": "code_interpreter"}]
        else:
            # Default to both for unknown types
            return [{"type": "file_search"}, {"type": "code_interpreter"}]

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] = None) -> LLMResponse:
        """Execute a task using Assistants API with file attachments."""
        start = time.time()

        # Get or create assistant
        assistant_id = self._get_or_create_assistant()

        # Upload input files
        file_ids = []
        attachments = []

        files_to_upload = input_files or []
        for f in files_to_upload:
            if f and f.exists():
                print(f"  Uploading {f.name} to OpenAI Files API...")
                file_id = self._upload_file(f)
                file_ids.append(file_id)
                tools = self._get_tools_for_file(f)
                attachments.append({"file_id": file_id, "tools": tools})

        # Create thread with attachments
        thread = self.client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": task.prompt,
                    "attachments": attachments if attachments else None,
                }
            ]
        )

        # Run and poll for completion
        print(f"  Running assistant...")
        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=assistant_id
        )

        latency_ms = (time.time() - start) * 1000

        # Get response
        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        response_text = ""
        for msg in messages.data:
            if msg.role == "assistant":
                for content_block in msg.content:
                    if content_block.type == "text":
                        response_text += content_block.text.value + "\n"
                break  # Only get the first assistant message

        # Cleanup uploaded files
        for fid in file_ids:
            try:
                self.client.files.delete(fid)
            except Exception as e:
                print(f"  Warning: Failed to delete file {fid}: {e}")

        # Extract usage info
        input_tokens = run.usage.prompt_tokens if run.usage else 0
        output_tokens = run.usage.completion_tokens if run.usage else 0

        parsed_json = _extract_json(response_text)

        return LLMResponse(
            raw_text=response_text.strip(),
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def cleanup(self):
        """Delete the assistant when done."""
        if self._assistant_id:
            try:
                self.client.beta.assistants.delete(self._assistant_id)
                self._assistant_id = None
            except Exception as e:
                print(f"  Warning: Failed to delete assistant: {e}")


class GeminiRunner:
    """Run tasks against Google Gemini models using Files API + Code Execution."""

    def __init__(self, api_key: str = None, model: str = None):
        if not model:
            raise ValueError("model is required for GeminiRunner")
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _upload_file(self, path: Path) -> object:
        """Upload file to Gemini Files API."""
        print(f"  Uploading {path.name} to Gemini Files API...")
        return self.client.files.upload(file=str(path))

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] = None) -> LLMResponse:
        """Execute a task using Gemini with file upload and code execution."""
        from google.genai import types

        start = time.time()

        # Upload input files
        uploaded_files = []
        files_to_upload = input_files or []
        for f in files_to_upload:
            if f and f.exists():
                uploaded_file = self._upload_file(f)
                uploaded_files.append(uploaded_file)

        # Build contents with files and prompt
        contents = uploaded_files + [task.prompt]

        # Configure code execution tool
        config = types.GenerateContentConfig(
            tools=[types.Tool(code_execution=types.ToolCodeExecution)]
        )

        # Make API call
        print(f"  Running Gemini model...")
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        latency_ms = (time.time() - start) * 1000

        # Extract text from response parts
        response_text = ""
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                response_text += part.text + "\n"

        # Cleanup uploaded files
        for uploaded_file in uploaded_files:
            try:
                self.client.files.delete(name=uploaded_file.name)
            except Exception as e:
                print(f"  Warning: Failed to delete file {uploaded_file.name}: {e}")

        # Extract usage info
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0

        parsed_json = _extract_json(response_text)

        return LLMResponse(
            raw_text=response_text.strip(),
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )


def get_runner(provider: str, model: str):
    """Factory function to get the appropriate runner."""
    if provider == "anthropic":
        return AnthropicRunner(model=model)
    elif provider == "openai":
        return OpenAIRunner(model=model)
    elif provider == "gemini":
        return GeminiRunner(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_run_directory(model: str, base_dir: Path = None) -> Path:
    """Create a timestamped run directory under results/responses/{model}/{run_id}."""
    if base_dir is None:
        base_dir = Path(__file__).parent / "results" / "responses"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize model name for filesystem
    model_safe = model.replace("/", "-").replace(":", "-")
    run_dir = base_dir / model_safe / timestamp

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
        # Format criteria for the prompt (normalize to list format)
        criteria = normalize_criteria(rubric.get("criteria", []))
        criteria_text = "\n".join(
            [
                f"- **{c['id']}** ({c.get('points', 0)} points): {c['description']}"
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
            print(f"  Raw response preview: {raw_text[:500]}...")
            return {"scores": {}, "weighted_total": 0.0, "raw_response": raw_text}

        # Calculate weighted total
        scores = parsed.get("scores", {})
        weighted_total = 0.0
        total_weight = 0.0

        for criterion in criteria:
            cid = criterion["id"]
            points = criterion.get("points", 0)
            if cid in scores:
                score_val = scores[cid].get("score", 0)
                weighted_total += score_val * points
                total_weight += points

        # Normalize to 0-1 scale if weights don't sum to 1
        if total_weight > 0:
            weighted_total = weighted_total / total_weight

        parsed["weighted_total"] = weighted_total
        return parsed
