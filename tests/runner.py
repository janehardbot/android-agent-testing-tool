"""Test runner — loads and executes test suites from YAML/JSON specs."""

import json
import time
import uuid
import os
from typing import List, Optional

from agent_control.adb_wrapper import ADBWrapper
from agent_control.ui_controller import UIController
from .step_executor import StepExecutor, StepResult


class TestRunner:
    """Loads test suites from YAML/JSON and executes them sequentially."""

    def __init__(self, device_serial: Optional[str] = None, output_base: str = "/tmp/test_output"):
        self.adb = ADBWrapper(device_serial)
        self.ui = UIController()
        self.output_base = output_base
        self.device_serial = device_serial

    def load_suite(self, suite_path: str) -> dict:
        """Load a test suite from YAML or JSON file."""
        with open(suite_path, "r") as f:
            if suite_path.endswith((".yaml", ".yml")):
                try:
                    import yaml
                    return yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML required for YAML suites: pip install pyyaml")
            else:
                return json.load(f)

    def run_suite(self, suite_path: str) -> dict:
        """Execute a full test suite and return structured results."""
        suite = self.load_suite(suite_path)
        run_id = str(uuid.uuid4())[:8]
        output_dir = os.path.join(self.output_base, run_id)
        os.makedirs(output_dir, exist_ok=True)

        executor = StepExecutor(self.adb, self.ui, output_dir)

        suite_name = suite.get("name", os.path.basename(suite_path))
        steps = suite.get("steps", [])

        results: List[StepResult] = []
        suite_start = time.monotonic()
        abort = False

        for i, step in enumerate(steps):
            if abort:
                results.append(StepResult(
                    step_name=step.get("name", f"step_{i}"),
                    step_type=step.get("type", "unknown"),
                    status="skipped"
                ))
                continue

            result = executor.execute(step, i)
            results.append(result)

            # Abort remaining steps on failure if suite config says so
            if result.status in ("fail", "error") and suite.get("abort_on_failure", True):
                abort = True

        suite_duration = (time.monotonic() - suite_start) * 1000

        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")
        errors = sum(1 for r in results if r.status == "error")
        skipped = sum(1 for r in results if r.status == "skipped")

        overall = "pass" if failed == 0 and errors == 0 else "fail"

        run_result = {
            "run_id": run_id,
            "suite_name": suite_name,
            "suite_path": suite_path,
            "status": overall,
            "total_steps": len(steps),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "duration_ms": suite_duration,
            "output_dir": output_dir,
            "steps": [
                {
                    "name": r.step_name,
                    "type": r.step_type,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "screenshot": r.screenshot_path,
                    "error": r.error,
                }
                for r in results
            ],
        }

        # Write run result to output dir
        result_path = os.path.join(output_dir, "run.json")
        with open(result_path, "w") as f:
            json.dump(run_result, f, indent=2)

        return run_result

    def run_suite_from_dict(self, suite: dict) -> dict:
        """Execute a suite from an already-loaded dict (for API use)."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(suite, f)
            temp_path = f.name
        try:
            return self.run_suite(temp_path)
        finally:
            os.unlink(temp_path)
