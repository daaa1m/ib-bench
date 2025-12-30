"""
Run evaluation on tasks.

Usage:
    # With config file (recommended)
    uv run python eval/run.py --config configs/quick-test.yaml
    uv run python eval/run.py --config configs/full-easy.yaml

    # Override config with CLI args
    uv run python eval/run.py --config configs/quick-test.yaml --model gpt-4o
    uv run python eval/run.py --config configs/quick-test.yaml --parallel 5

    # Without config (all CLI args)
    uv run python eval/run.py --tasks e-001 --model claude-sonnet-4-20250514
    uv run python eval/run.py --tasks e-001 e-002 --model claude-sonnet-4-20250514
    uv run python eval/run.py --filter e- --model claude-sonnet-4-20250514
    uv run python eval/run.py --provider openai --model gpt-4o --tasks e-001

    # Other options
    uv run python eval/run.py --resume MODEL/RUN_ID  # Resume interrupted run
    uv run python eval/run.py --parallel 5           # Run 5 tasks concurrently
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

import yaml

from helpers import load_tasks, get_runner, create_run_directory


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def merge_config_with_args(config: dict, args: argparse.Namespace) -> argparse.Namespace:
    """Merge config file values with CLI args. CLI args take precedence."""
    # Start with config values
    if "provider" in config and args.provider is None:
        args.provider = config["provider"]
    if "model" in config and args.model is None:
        args.model = config["model"]
    if "tasks" in config and args.tasks is None:
        args.tasks = config["tasks"]
    if "filter" in config and args.filter is None:
        args.filter = config["filter"]
    if "parallel" in config and args.parallel == 1:  # 1 is default
        args.parallel = config["parallel"]

    # Apply defaults
    if args.provider is None:
        args.provider = "anthropic"

    return args


def run_task(task, runner, run_dir: Path) -> dict:
    """Execute a single task and save the response."""
    print(f"Running task {task.id}...")

    # Find input files (xlsx, pdf, etc.)
    input_files = [f for f in task.input_files if f.suffix.lower() in [".xlsx", ".pdf", ".xls"]]

    if input_files:
        print(f"  Input files: {[f.name for f in input_files]}")

    response = runner.run(task, input_files=input_files)

    # Prepare response data
    response_data = {
        "task_id": task.id,
        "model": response.model,
        "timestamp": datetime.now().isoformat(),
        "input_files": [f.name for f in input_files],
        "raw_response": response.raw_text,
        "parsed_response": response.parsed_json,
        "usage": {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "latency_ms": response.latency_ms,
        },
    }

    # Save response (run_dir is already under results/responses/)
    response_path = run_dir / f"{task.id}.json"
    with open(response_path, "w") as f:
        json.dump(response_data, f, indent=2)

    print(f"  Saved response to {response_path}")
    print(f"  Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"  Latency: {response.latency_ms:.0f}ms")

    return response_data


async def run_task_async(task, runner, run_dir: Path, semaphore) -> dict:
    """Execute a single task asynchronously with rate limiting."""
    async with semaphore:
        print(f"Running task {task.id}...")

        input_files = [f for f in task.input_files if f.suffix.lower() in [".xlsx", ".pdf", ".xls"]]

        # Run sync runner in thread pool
        response = await asyncio.to_thread(runner.run, task, input_files)

        # Prepare and save response
        response_data = {
            "task_id": task.id,
            "model": response.model,
            "timestamp": datetime.now().isoformat(),
            "input_files": [f.name for f in input_files],
            "raw_response": response.raw_text,
            "parsed_response": response.parsed_json,
            "usage": {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
            },
        }

        response_path = run_dir / f"{task.id}.json"
        with open(response_path, "w") as f:
            json.dump(response_data, f, indent=2)

        print(f"  {task.id}: {response.input_tokens} in / {response.output_tokens} out ({response.latency_ms:.0f}ms)")
        return {"task_id": task.id, "status": "success"}


async def run_tasks_parallel(tasks, runner, run_dir: Path, max_concurrent: int) -> list:
    """Run multiple tasks concurrently with rate limiting."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def safe_run(task):
        try:
            return await run_task_async(task, runner, run_dir, semaphore)
        except Exception as e:
            print(f"  ERROR {task.id}: {e}")
            return {"task_id": task.id, "status": "error", "error": str(e)}

    results = await asyncio.gather(*[safe_run(t) for t in tasks])
    return list(results)


def main():
    parser = argparse.ArgumentParser(
        description="Run IB-bench evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config configs/quick-test.yaml
  %(prog)s --config configs/quick-test.yaml --model gpt-4o
  %(prog)s --tasks e-001 --model claude-sonnet-4-20250514
        """
    )
    parser.add_argument(
        "--config", type=Path, help="Path to YAML config file (e.g., configs/quick-test.yaml)"
    )
    parser.add_argument(
        "--tasks", nargs="+", help="Task IDs to run (e.g., e-001 e-002)"
    )
    parser.add_argument("--filter", help="Task ID prefix filter (e.g., 'e-' for easy)")
    parser.add_argument(
        "--provider", default=None, choices=["anthropic", "openai", "gemini"],
        help="Provider (default: anthropic)"
    )
    parser.add_argument("--model", help="Model identifier (e.g., claude-sonnet-4-20250514, gpt-4o)")
    parser.add_argument("--resume", help="Run ID to resume")
    parser.add_argument("--parallel", type=int, default=1, help="Number of concurrent tasks (default: 1 = sequential)")
    args = parser.parse_args()

    # Load config file if provided
    config = {}
    if args.config:
        config_path = Path(__file__).parent / args.config
        if not config_path.exists():
            # Try absolute path
            config_path = args.config
        if not config_path.exists():
            parser.error(f"Config file not found: {args.config}")
        config = load_config(config_path)
        print(f"Loaded config from: {config_path}")

    # Merge config with CLI args (CLI takes precedence)
    args = merge_config_with_args(config, args)

    # Validate required fields
    if not args.model:
        parser.error("--model is required (via config or CLI)")
    if not args.tasks and not args.filter:
        parser.error("At least one of --tasks or --filter is required (via config or CLI)")

    # Load tasks (no rubric needed for running, only for scoring)
    tasks = load_tasks(
        task_ids=args.tasks, filter_pattern=args.filter, include_rubric=False
    )
    if not tasks:
        print("No tasks found!")
        print(f"Looked for task IDs: {args.tasks}")
        return

    print(f"Found {len(tasks)} task(s) to run")

    # Initialize runner
    runner = get_runner(args.provider, args.model)
    model_name = runner.model

    # Create or resume run directory
    existing_results = []
    original_started_at = None
    if args.resume:
        run_dir = Path(__file__).parent / "results" / "responses" / args.resume
        if not run_dir.exists():
            print(f"Run directory not found: {run_dir}")
            return
        # Load existing config to preserve results_summary and started_at
        config_path = run_dir / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                existing_config = json.load(f)
                existing_results = existing_config.get("results_summary", [])
                original_started_at = existing_config.get("started_at")
    else:
        run_dir = create_run_directory(model_name)

    print(f"Run directory: {run_dir}")

    # Save config
    run_config = {
        "provider": args.provider,
        "model": model_name,
        "task_ids": [t.id for t in tasks],
        "parallel": args.parallel,
        "config_file": str(args.config) if args.config else None,
        "started_at": original_started_at or datetime.now().isoformat(),
    }
    config_path = run_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(run_config, f, indent=2)

    # Filter out already-completed tasks if resuming
    tasks_to_run = []
    for task in tasks:
        response_path = run_dir / f"{task.id}.json"
        if response_path.exists() and args.resume:
            print(f"Skipping {task.id} (already completed)")
        else:
            tasks_to_run.append(task)

    # Run tasks (parallel or sequential)
    if args.parallel > 1 and len(tasks_to_run) > 1:
        print(f"Running {len(tasks_to_run)} task(s) with {args.parallel} concurrent...")
        results = asyncio.run(run_tasks_parallel(tasks_to_run, runner, run_dir, args.parallel))
    else:
        results = []
        for task in tasks_to_run:
            try:
                run_task(task, runner, run_dir)
                results.append({"task_id": task.id, "status": "success"})
            except Exception as e:
                print(f"  ERROR: {e}")
                results.append({"task_id": task.id, "status": "error", "error": str(e)})

    # Clean up if no successful responses
    successful = [r for r in results if r["status"] == "success"]
    if not successful and not args.resume:
        import shutil

        print(f"\nNo successful responses. Cleaning up {run_dir}")
        shutil.rmtree(run_dir)
        return

    # Update config with completion info
    # Merge existing results with new results (existing first, then new)
    existing_task_ids = {r["task_id"] for r in existing_results}
    merged_results = existing_results + [r for r in results if r["task_id"] not in existing_task_ids]

    run_config["completed_at"] = datetime.now().isoformat()
    run_config["results_summary"] = merged_results
    with open(config_path, "w") as f:
        json.dump(run_config, f, indent=2)

    print(f"\nRun complete! Results in: {run_dir}")
    print(f"Run ID: {run_dir.name}")


if __name__ == "__main__":
    main()
