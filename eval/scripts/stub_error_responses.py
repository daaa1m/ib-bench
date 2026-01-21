"""Create stub response JSONs for errored tasks in a run."""

import argparse
import json
from datetime import datetime
from pathlib import Path


def _load_errors(errors_path: Path) -> list[dict]:
    payload = json.loads(errors_path.read_text())
    return payload.get("errors", [])


def _resolve_model(responses_dir: Path) -> str:
    config_path = responses_dir / "config.json"
    if config_path.exists():
        try:
            payload = json.loads(config_path.read_text())
            model = payload.get("model")
            if model:
                return model
        except json.JSONDecodeError:
            pass
    return responses_dir.parent.name


def _build_stub(err: dict, model: str) -> dict:
    return {
        "task_id": err.get("task_id", "unknown"),
        "model": model,
        "timestamp": err.get("timestamp") or datetime.now().isoformat(),
        "input_files": err.get("input_files", []),
        "output_files": [],
        "raw_response": f"ERROR: {err.get('summary', '')}",
        "parsed_response": {},
        "stop_reason": "error",
        "usage": {"input_tokens": 0, "output_tokens": 0, "latency_ms": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create stub response files for errored tasks."
    )
    parser.add_argument("responses_dir", help="Path to eval/responses/<model>/<run>")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing response files",
    )
    args = parser.parse_args()

    responses_dir = Path(args.responses_dir).resolve()
    errors_path = responses_dir / "errors.json"
    if not errors_path.exists():
        print(f"errors.json not found in {responses_dir}")
        return 1

    errors = _load_errors(errors_path)
    if not errors:
        print("No errors found; nothing to stub.")
        return 0

    model = _resolve_model(responses_dir)
    created = 0

    for err in errors:
        task_id = err.get("task_id")
        if not task_id:
            continue

        response_path = responses_dir / f"{task_id}.json"
        if response_path.exists() and not args.force:
            continue

        payload = _build_stub(err, model)
        if args.dry_run:
            print(f"Would create {response_path}")
            continue

        response_path.write_text(json.dumps(payload, indent=2))
        created += 1

    print(f"Created {created} stub response(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
