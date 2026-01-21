"""
Run evaluation on tasks.

Usage:
    uv run python eval/run.py --config configs/quick-test.yaml
    uv run python eval/run.py --config configs/full-easy.yaml
    uv run python eval/run.py --config configs/quick-test.yaml --resume MODEL/RUN_ID

Config examples live in eval/configs.example. Copy to eval/configs for local overrides.
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

from helpers import (
    Provider,
    Task,
    build_error_report,
    create_run_directory,
    get_runner,
    load_tasks,
)
from runners import (
    AnthropicRunner,
    AzureAgentRunner,
    GeminiRunner,
    LLMResponse,
    OpenAIRunner,
)

Runner = AnthropicRunner | OpenAIRunner | GeminiRunner | AzureAgentRunner


class UsageData(TypedDict):
    input_tokens: int
    output_tokens: int
    latency_ms: float


class ResponseData(TypedDict):
    task_id: str
    model: str
    timestamp: str
    input_files: list[str]
    output_files: list[str]
    raw_response: str
    parsed_response: dict[str, Any] | None
    stop_reason: str
    usage: UsageData


class TaskResult(TypedDict, total=False):
    task_id: str
    status: str
    error: str


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def _select_input_files(task: Task) -> list[Path]:
    return [
        f for f in task.input_files if f.suffix.lower() in [".xlsx", ".pdf", ".xls"]
    ]


def _write_error_log(run_dir: Path, errors: list[dict[str, Any]]) -> None:
    if not errors:
        return
    error_path = run_dir / "errors.json"
    existing_errors: list[dict[str, Any]] = []
    if error_path.exists():
        try:
            with open(error_path) as f:
                existing_payload = json.load(f)
                existing_errors = existing_payload.get("errors", [])
        except (json.JSONDecodeError, IOError):
            existing_errors = []

    merged_errors = existing_errors + errors
    payload = {"errors": merged_errors, "count": len(merged_errors)}
    with open(error_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nErrors logged to: {error_path}")


def _save_output_files(task_id: str, response: LLMResponse, run_dir: Path) -> list[str]:
    output_file_paths = []
    if response.output_files:
        for i, out_file in enumerate(response.output_files):
            ext = (
                out_file.filename.split(".")[-1] if "." in out_file.filename else "bin"
            )
            output_path = run_dir / f"{task_id}_output_{i + 1}.{ext}"
            with open(output_path, "wb") as f:
                f.write(out_file.content)
            output_file_paths.append(output_path.name)
            print(f"  Saved output file: {output_path.name}")
    return output_file_paths


def _build_response_data(
    task_id: str,
    response: LLMResponse,
    input_files: list[Path],
    output_file_paths: list[str],
) -> ResponseData:
    response_data: ResponseData = {
        "task_id": task_id,
        "model": response.model,
        "timestamp": datetime.now().isoformat(),
        "input_files": [f.name for f in input_files],
        "output_files": output_file_paths,
        "raw_response": response.raw_text,
        "parsed_response": response.parsed_json,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "latency_ms": response.latency_ms,
        },
    }
    return response_data


def _write_response_json(
    run_dir: Path, task_id: str, response_data: ResponseData
) -> Path:
    response_path = run_dir / f"{task_id}.json"
    with open(response_path, "w") as f:
        json.dump(response_data, f, indent=2)
    return response_path


def _print_error(
    task_id: str,
    error: Exception,
    run_id: str,
    verbose: bool,
    provider: str,
    model: str,
    input_files: list[Path],
) -> dict[str, Any]:
    details, summary, next_steps = build_error_report(error, verbose=True)
    next_steps.append(f"Retry with --resume {run_id}")

    print(f"  ERROR {task_id}: {summary}")
    if next_steps:
        print("  Next steps:")
        for step in next_steps:
            print(f"    - {step}")
    if verbose:
        print("  Details:")
        print(json.dumps(details, indent=2))

    return {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "summary": summary,
        "details": details,
        "next_steps": next_steps,
        "input_files": [f.name for f in input_files],
    }


def run_task(task: Task, runner: Runner, run_dir: Path) -> ResponseData:
    """Execute a single task and save the response."""
    print(f"Running task {task.id}...")

    input_files = _select_input_files(task)

    if input_files:
        print(f"  Input files: {[f.name for f in input_files]}")

    response = runner.run(task, input_files=input_files)

    output_file_paths = _save_output_files(task.id, response, run_dir)
    response_data = _build_response_data(
        task.id, response, input_files, output_file_paths
    )

    # Save response, and dump it as json e.g., e-001.json
    # run_dir => ...{model}/{timestamp}
    response_path = _write_response_json(run_dir, task.id, response_data)

    print(f"  Saved response to {response_path}")
    print(f"  Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"  Latency: {response.latency_ms:.0f}ms")

    return response_data


async def run_task_async(
    task: Task, runner: Runner, run_dir: Path, semaphore: asyncio.Semaphore
) -> TaskResult:
    """Execute a single task asynchronously with rate limiting."""
    async with semaphore:
        print(f"Running task {task.id}...")

        input_files = _select_input_files(task)

        # Run sync runner in thread pool
        response = await asyncio.to_thread(runner.run, task, input_files)

        output_file_paths = _save_output_files(task.id, response, run_dir)
        response_data = _build_response_data(
            task.id, response, input_files, output_file_paths
        )
        _write_response_json(run_dir, task.id, response_data)

        print(
            f"  {task.id}: {response.input_tokens} in / {response.output_tokens} out ({response.latency_ms:.0f}ms)"
        )
        return {"task_id": task.id, "status": "success"}


async def run_tasks_parallel(
    tasks: list[Task],
    runner: Runner,
    run_dir: Path,
    max_concurrent: int,
    errors: list[dict[str, Any]],
    errors_lock: asyncio.Lock,
    verbose: bool,
    provider: str,
    model: str,
    run_id: str,
) -> list[TaskResult]:
    """Run multiple tasks concurrently with rate limiting."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def safe_run(task: Task) -> TaskResult:
        try:
            return await run_task_async(task, runner, run_dir, semaphore)
        except Exception as e:
            input_files = _select_input_files(task)
            error_entry = _print_error(
                task.id,
                e,
                run_id,
                verbose,
                provider,
                model,
                input_files,
            )
            async with errors_lock:
                errors.append(error_entry)
            result: TaskResult = {
                "task_id": task.id,
                "status": "error",
                "error": error_entry["summary"],
            }
            return result

    results = await asyncio.gather(*[safe_run(t) for t in tasks])
    return list(results)


def main():
    parser = argparse.ArgumentParser(
        description="Run IB-bench evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config configs/quick-test.yaml
  %(prog)s --config configs/full-easy.yaml
  %(prog)s --config configs/quick-test.yaml --resume MODEL/RUN_ID
        """,
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to YAML config file (e.g., configs/quick-test.yaml)",
    )
    parser.add_argument("--resume", help="Run ID to resume (e.g., MODEL/RUN_ID)")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full API error details on failure",
    )
    args = parser.parse_args()

    # Load config file
    config_path = Path(__file__).parent / args.config
    if not config_path.exists():
        config_path = args.config  # Try absolute path
    if not config_path.exists():
        parser.error(f"Config file not found: {args.config}")

    config = load_config(config_path)
    print(f"Loaded config from: {config_path}")

    # Extract config values
    provider: str | None = config.get("provider")
    model: str | None = config.get("model")
    task_ids: list[str] | None = config.get("tasks")
    filter_pattern: str | None = config.get("filter")
    parallel: int = config.get("parallel", 1)
    web_search_mode: str | None = config.get("web_search_mode")

    # Validate required fields
    if not provider:
        parser.error("Config must specify 'provider'")
    if not model:
        parser.error("Config must specify 'model'")
    if not task_ids and not filter_pattern:
        parser.error("Config must specify 'tasks' or 'filter'")

    # Load tasks (no rubric needed for running, only for scoring)
    tasks = load_tasks(
        task_ids=task_ids, filter_pattern=filter_pattern, include_rubric=False
    )
    if not tasks:
        print("No tasks found!")
        print(f"Looked for task IDs: {task_ids}")
        return

    print(f"Found {len(tasks)} task(s) to run")

    runner_kwargs: dict[str, Any] = {}
    if provider == "azure-v2" and web_search_mode:
        runner_kwargs["web_search_mode"] = web_search_mode
    runner = get_runner(cast(Provider, provider), model, **runner_kwargs)
    model_name = runner.model

    # Create or resume run directory
    existing_results = []
    original_started_at = None
    if args.resume:
        run_dir = Path(__file__).parent / "responses" / args.resume
        if not run_dir.exists():
            print(f"Run directory not found: {run_dir}")
            return
        # Load existing config to preserve results_summary and started_at
        existing_config_path = run_dir / "config.json"
        if existing_config_path.exists():
            with open(existing_config_path) as f:
                existing_config = json.load(f)
                existing_results = existing_config.get("results_summary", [])
                original_started_at = existing_config.get("started_at")
    else:
        run_dir = create_run_directory(model_name)

    print(f"Run directory: {run_dir}")
    run_id = f"{run_dir.parent.name}/{run_dir.name}"

    # Save config
    run_config = {
        "provider": provider,
        "model": model_name,
        "task_ids": [t.id for t in tasks],
        "parallel": parallel,
        "config_file": str(args.config),
        "started_at": original_started_at or datetime.now().isoformat(),
    }
    if web_search_mode:
        run_config["web_search_mode"] = web_search_mode
    run_config_path = run_dir / "config.json"
    with open(run_config_path, "w") as f:
        json.dump(run_config, f, indent=2)

    # Filter out already-completed tasks if resuming
    tasks_to_run = []
    for task in tasks:
        response_path = run_dir / f"{task.id}.json"
        if response_path.exists() and args.resume:
            print(f"Skipping {task.id} (already completed)")
        else:
            tasks_to_run.append(task)

    # Early exit if nothing to run
    if not tasks_to_run:
        print("\nAll tasks already completed!")
        return

    # Run tasks (parallel or sequential)
    errors: list[dict[str, Any]] = []
    if parallel > 1 and len(tasks_to_run) > 1:
        print(f"Running {len(tasks_to_run)} task(s) with {parallel} concurrent...")

        async def run_parallel_with_errors() -> list[TaskResult]:
            errors_lock = asyncio.Lock()
            return await run_tasks_parallel(
                tasks_to_run,
                runner,
                run_dir,
                parallel,
                errors,
                errors_lock,
                args.verbose,
                provider,
                model_name,
                run_id,
            )

        results = asyncio.run(run_parallel_with_errors())
    else:
        print(f"Running {len(tasks_to_run)} task(s) sequentially...")
        results: list[TaskResult] = []
        for task in tasks_to_run:
            try:
                run_task(task, runner, run_dir)
                result: TaskResult = {"task_id": task.id, "status": "success"}
                results.append(result)
            except Exception as e:
                input_files = _select_input_files(task)
                error_entry = _print_error(
                    task.id,
                    e,
                    run_id,
                    args.verbose,
                    provider,
                    model_name,
                    input_files,
                )
                errors.append(error_entry)
                result = {
                    "task_id": task.id,
                    "status": "error",
                    "error": error_entry["summary"],
                }
                results.append(result)

    successful = [r for r in results if r.get("status") == "success"]
    if not successful and not args.resume:
        if errors:
            print(f"\nNo successful responses. Preserving {run_dir} for error review")
        else:
            import shutil

            print(f"\nNo successful responses. Cleaning up {run_dir}")
            shutil.rmtree(run_dir)
            return

    existing_task_ids = {r.get("task_id") for r in existing_results}
    merged_results = existing_results + [
        r for r in results if r.get("task_id") not in existing_task_ids
    ]

    run_config["completed_at"] = datetime.now().isoformat()
    run_config["results_summary"] = merged_results
    with open(run_config_path, "w") as f:
        json.dump(run_config, f, indent=2)

    _write_error_log(run_dir, errors)

    print(f"\nRun complete! Results in: {run_dir}")
    print(f"Run ID: {run_dir.name}")


if __name__ == "__main__":
    main()
