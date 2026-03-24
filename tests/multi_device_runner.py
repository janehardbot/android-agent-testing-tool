"""Multi-device test runner — coordinates steps across two or more ADB devices."""

import json
import os
import re
import time
import uuid
from typing import Dict, Optional

from agent_control.adb_wrapper import ADBWrapper
from agent_control.ui_controller import UIController
from .step_executor import StepExecutor, StepResult


class CallStepExecutor(StepExecutor):
    """Extends StepExecutor with call-related and multi-device step types."""

    def __init__(self, adb: ADBWrapper, ui: UIController,
                 output_dir: str = "/tmp/test_output", device_label: str = "A"):
        super().__init__(adb, ui, output_dir)
        self.device_label = device_label

    def _get_handler(self, step_type: str):
        extra = {
            "call": self._handle_call,
            "answer_call": self._handle_answer_call,
            "end_call": self._handle_end_call,
            "assert_call_state": self._handle_assert_call_state,
            "wake_device": self._handle_wake_device,
        }
        base = super()._get_handler(step_type)
        return extra.get(step_type, base)

    def _handle_call(self, step: dict):
        number = step["number"]
        self.adb.run_shell(f"am start -a android.intent.action.CALL -d tel:{number}")

    def _handle_answer_call(self, step: dict):
        # Answer incoming call via input keyevent KEYCODE_CALL (5)
        self.adb.run_shell("input keyevent 5")

    def _handle_end_call(self, step: dict):
        # End call via KEYCODE_ENDCALL (6)
        self.adb.run_shell("input keyevent 6")

    def _handle_assert_call_state(self, step: dict):
        """Check telephony call state: IDLE, RINGING, OFFHOOK."""
        expected = step.get("expected_state", "OFFHOOK").upper()
        # Read telephony state via dumpsys
        output = self.adb.run_shell("dumpsys telephony.registry | grep mCallState")
        # mCallState=0 → IDLE, 1 → RINGING, 2 → OFFHOOK
        state_map = {"0": "IDLE", "1": "RINGING", "2": "OFFHOOK"}
        match = re.search(r"mCallState=(\d)", output)
        if not match:
            raise AssertionError(f"Could not read call state. dumpsys output: {output[:200]}")
        actual = state_map.get(match.group(1), f"UNKNOWN({match.group(1)})")
        if actual != expected:
            raise AssertionError(f"Call state: expected {expected}, got {actual}")

    def _handle_wake_device(self, step: dict):
        """Wake + unlock device (assumes no PIN or swipe-to-unlock)."""
        self.adb.run_shell("input keyevent KEYCODE_WAKEUP")
        time.sleep(0.5)
        # Swipe up to dismiss lock screen
        self.adb.run_shell("input swipe 540 1800 540 900 300")


class MultiDeviceRunner:
    """Runs test suites that span multiple ADB devices (A and B)."""

    def __init__(self, device_a: str, device_b: str,
                 variables: Optional[Dict[str, str]] = None,
                 output_base: str = "/tmp/test_output"):
        self.device_a = device_a
        self.device_b = device_b
        self.variables = variables or {}
        self.output_base = output_base

    def _make_executor(self, serial: str, label: str, output_dir: str) -> CallStepExecutor:
        adb = ADBWrapper(serial)
        ui = UIController(serial)
        return CallStepExecutor(adb, ui, output_dir, device_label=label)

    def _resolve_vars(self, step: dict) -> dict:
        """Replace {{VAR}} placeholders in step values."""
        resolved = {}
        for k, v in step.items():
            if isinstance(v, str):
                for var, val in self.variables.items():
                    v = v.replace(f"{{{{{var}}}}}", val)
            resolved[k] = v
        return resolved

    def load_suite(self, suite_path: str) -> dict:
        with open(suite_path) as f:
            if suite_path.endswith((".yaml", ".yml")):
                import yaml
                return yaml.safe_load(f)
            return json.load(f)

    def run_suite(self, suite_path: str) -> dict:
        suite = self.load_suite(suite_path)
        run_id = str(uuid.uuid4())[:8]
        output_dir = os.path.join(self.output_base, run_id)
        os.makedirs(output_dir, exist_ok=True)

        exec_a = self._make_executor(self.device_a, "A", output_dir)
        exec_b = self._make_executor(self.device_b, "B", output_dir)

        steps = suite.get("steps", [])
        results = []
        suite_start = time.monotonic()
        abort = False

        for i, raw_step in enumerate(steps):
            step = self._resolve_vars(raw_step)
            step_name = step.get("name", f"step_{i}")
            step_device = step.get("device", "A").upper()

            if abort:
                results.append(StepResult(
                    step_name=step_name,
                    step_type=step.get("type", "unknown"),
                    status="skipped"
                ))
                continue

            executor = exec_a if step_device == "A" else exec_b
            result = executor.execute(step, i)
            results.append(result)

            if result.status in ("fail", "error") and suite.get("abort_on_failure", True):
                abort = True

        duration = (time.monotonic() - suite_start) * 1000
        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")
        errors = sum(1 for r in results if r.status == "error")
        skipped = sum(1 for r in results if r.status == "skipped")

        run_result = {
            "run_id": run_id,
            "suite_name": suite.get("name", "Unknown"),
            "suite_path": suite_path,
            "status": "pass" if failed == 0 and errors == 0 else "fail",
            "total_steps": len(steps),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "duration_ms": duration,
            "output_dir": output_dir,
            "devices": {"A": self.device_a, "B": self.device_b},
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

        with open(os.path.join(output_dir, "run.json"), "w") as f:
            json.dump(run_result, f, indent=2)

        return run_result
