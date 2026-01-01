"""
Mark a task as blocked by content filter.

Usage:
    uv run python eval/mark_blocked.py MODEL/RUN_ID TASK_ID
    uv run python eval/mark_blocked.py gpt-5.2/20251231_120000 e-006
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Mark a task as blocked by content filter"
    )
    parser.add_argument("run_path", help="Run path (e.g., MODEL/RUN_ID)")
    parser.add_argument("task_id", help="Task ID to mark as blocked (e.g., e-006)")
    args = parser.parse_args()

    responses_dir = Path(__file__).parent / "responses" / args.run_path
    if not responses_dir.exists():
        print(f"Run directory not found: {responses_dir}")
        return 1

    # Load config to get model name
    config_file = responses_dir / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            run_config = json.load(f)
        model_name = run_config.get("model", "unknown")
    else:
        model_name = "unknown"

    # Check if response already exists
    response_path = responses_dir / f"{args.task_id}.json"
    if response_path.exists():
        print(f"Response already exists: {response_path}")
        print("Delete it first if you want to mark as blocked.")
        return 1

    # Create blocked response
    blocked_response = {
        "task_id": args.task_id,
        "model": model_name,
        "timestamp": datetime.now().isoformat(),
        "input_files": [],
        "output_files": [],
        "raw_response": "",
        "parsed_response": None,
        "stop_reason": "content_filter",
        "usage": {"input_tokens": 0, "output_tokens": 0, "latency_ms": 0},
    }

    with open(response_path, "w") as f:
        json.dump(blocked_response, f, indent=2)

    print(f"Marked {args.task_id} as blocked (content filter)")
    print(f"Saved to: {response_path}")
    return 0


if __name__ == "__main__":
    exit(main())
