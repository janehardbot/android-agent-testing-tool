"""Structured JSON logger for test runs."""

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


class RunLogger:
    """Writes structured JSON run logs to output directories."""

    def __init__(self, output_base: str = "/tmp/test_output"):
        self.output_base = output_base

    def log_run(self, run_result: dict, output_dir: Optional[str] = None) -> str:
        """Write a structured run log to the output directory."""
        if output_dir is None:
            output_dir = run_result.get("output_dir", self.output_base)
        os.makedirs(output_dir, exist_ok=True)

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_result["run_id"],
            "suite_name": run_result["suite_name"],
            "status": run_result["status"],
            "total_steps": run_result["total_steps"],
            "passed": run_result["passed"],
            "failed": run_result["failed"],
            "errors": run_result["errors"],
            "skipped": run_result["skipped"],
            "duration_ms": run_result["duration_ms"],
            "steps": [
                {
                    "name": s["name"],
                    "type": s["type"],
                    "status": s["status"],
                    "duration_ms": s["duration_ms"],
                    "screenshot_path": s.get("screenshot"),
                    "error": s.get("error"),
                }
                for s in run_result["steps"]
            ],
        }

        log_path = os.path.join(output_dir, "run.json")
        with open(log_path, "w") as f:
            json.dump(log_entry, f, indent=2)

        return log_path

    def append_to_history(self, run_result: dict, history_file: str = "run_history.jsonl") -> str:
        """Append a summary line to the run history JSONL file."""
        history_path = os.path.join(self.output_base, history_file)
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_result["run_id"],
            "suite_name": run_result["suite_name"],
            "status": run_result["status"],
            "passed": run_result["passed"],
            "failed": run_result["failed"],
            "duration_ms": run_result["duration_ms"],
        }
        with open(history_path, "a") as f:
            f.write(json.dumps(summary) + "\n")
        return history_path
