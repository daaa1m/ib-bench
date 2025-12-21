"""
Run evaluation on tasks.

Usage:
    uv run python eval/run.py --tasks e-001          # Run specific task
    uv run python eval/run.py --tasks e-001 e-002    # Run multiple tasks
    uv run python eval/run.py --filter e-            # Run all easy tasks (by prefix)
    uv run python eval/run.py --tasks e-001 --filter e-  # Combine both
    uv run python eval/run.py --provider openai      # Use OpenAI instead of Anthropic
    uv run python eval/run.py --model gpt-4o         # Specify model
    uv run python eval/run.py --resume RUN_ID        # Resume interrupted run
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from helpers import load_tasks, get_runner, create_run_directory


def run_task(task, runner, run_dir: Path) -> dict:
    """Execute a single task and save the response."""
    print(f"Running task {task.id}...")

    # Find input files (xlsx, pdf, etc.)
    input_files = [f for f in task.input_files if f.suffix in [".xlsx", ".pdf", ".xls"]]
    input_file = input_files[0] if input_files else None

    if len(input_files) > 1:
        print(
            f"  Warning: Task has {len(input_files)} input files, only using {input_file.name}"
        )
        print(f"  Ignored: {[f.name for f in input_files[1:]]}")

    response = runner.run(task, input_file=input_file)

    # Prepare response data
    response_data = {
        "task_id": task.id,
        "model": response.model,
        "timestamp": datetime.now().isoformat(),
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


def main():
    parser = argparse.ArgumentParser(description="Run IB-bench evaluation")
    parser.add_argument(
        "--tasks", nargs="+", help="Task IDs to run (e.g., e-001 e-002)"
    )
    parser.add_argument("--filter", help="Task ID prefix filter (e.g., 'e-' for easy)")
    parser.add_argument(
        "--provider", default="anthropic", choices=["anthropic", "openai"]
    )
    parser.add_argument("--model", required=True, help="Model identifier (e.g., claude-sonnet-4-20250514, gpt-4o)")
    parser.add_argument("--resume", help="Run ID to resume")
    args = parser.parse_args()

    # Require at least one of --tasks or --filter
    if not args.tasks and not args.filter:
        parser.error("At least one of --tasks or --filter is required")

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
    if args.resume:
        run_dir = Path(__file__).parent / "results" / "responses" / args.resume
        if not run_dir.exists():
            print(f"Run directory not found: {run_dir}")
            return
    else:
        run_dir = create_run_directory(model_name)

    print(f"Run directory: {run_dir}")

    # Save config
    config = {
        "provider": args.provider,
        "model": model_name,
        "task_ids": [t.id for t in tasks],
        "started_at": datetime.now().isoformat(),
    }
    config_path = run_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    # Run each task
    results = []
    for task in tasks:
        # Skip if response already exists (for resume)
        response_path = run_dir / f"{task.id}.json"
        if response_path.exists() and args.resume:
            print(f"Skipping {task.id} (already completed)")
            continue

        try:
            result = run_task(task, runner, run_dir)
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
    config["completed_at"] = datetime.now().isoformat()
    config["results_summary"] = results
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nRun complete! Results in: {run_dir}")
    print(f"Run ID: {run_dir.name}")


if __name__ == "__main__":
    main()
