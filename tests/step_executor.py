"""Step executor — runs individual test steps using agent_control layer."""

import time
import os
from dataclasses import dataclass, field
from typing import Optional

from agent_control.adb_wrapper import ADBWrapper
from agent_control.ui_controller import UIController


@dataclass
class StepResult:
    """Result of executing a single test step."""
    step_name: str
    step_type: str
    status: str  # "pass", "fail", "error", "skipped"
    duration_ms: float = 0.0
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


class StepExecutor:
    """Executes individual test steps against a device."""

    def __init__(self, adb: ADBWrapper, ui: UIController, output_dir: str = "/tmp/test_output"):
        self.adb = adb
        self.ui = ui
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def execute(self, step: dict, step_index: int) -> StepResult:
        step_type = step.get("type", "unknown")
        step_name = step.get("name", f"step_{step_index}")
        max_retries = step.get("max_retries", 0)

        last_result = None
        for attempt in range(max_retries + 1):
            last_result = self._execute_single(step, step_name, step_type, step_index, attempt)
            if last_result.status == "pass":
                return last_result
        return last_result

    def _execute_single(self, step: dict, step_name: str, step_type: str,
                        step_index: int, attempt: int) -> StepResult:
        start = time.monotonic()
        try:
            handler = self._get_handler(step_type)
            if handler is None:
                return StepResult(
                    step_name=step_name, step_type=step_type, status="error",
                    error=f"Unknown step type: {step_type}"
                )
            handler(step)
            duration = (time.monotonic() - start) * 1000

            # Take screenshot after step if requested
            screenshot_path = None
            if step.get("screenshot", True):
                screenshot_path = os.path.join(
                    self.output_dir, f"{step_index:03d}_{step_name}_a{attempt}.png"
                )
                try:
                    self.adb.screencap(screenshot_path)
                except Exception:
                    screenshot_path = None

            return StepResult(
                step_name=step_name, step_type=step_type, status="pass",
                duration_ms=duration, screenshot_path=screenshot_path
            )
        except AssertionError as e:
            duration = (time.monotonic() - start) * 1000
            return StepResult(
                step_name=step_name, step_type=step_type, status="fail",
                duration_ms=duration, error=str(e)
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return StepResult(
                step_name=step_name, step_type=step_type, status="error",
                duration_ms=duration, error=str(e)
            )

    def _get_handler(self, step_type: str):
        handlers = {
            "tap": self._handle_tap,
            "swipe": self._handle_swipe,
            "type_text": self._handle_type_text,
            "press_key": self._handle_press_key,
            "screenshot": self._handle_screenshot,
            "assert_text": self._handle_assert_text,
            "wait": self._handle_wait,
            "launch_app": self._handle_launch_app,
        }
        return handlers.get(step_type)

    def _handle_tap(self, step: dict):
        x, y = step["x"], step["y"]
        self.ui.tap(x, y)

    def _handle_swipe(self, step: dict):
        self.ui.swipe(step["x1"], step["y1"], step["x2"], step["y2"],
                      duration_ms=step.get("duration_ms", 300))

    def _handle_type_text(self, step: dict):
        self.ui.type_text(step["text"])

    def _handle_press_key(self, step: dict):
        self.adb.run_shell(f"input keyevent {step['keycode']}")

    def _handle_screenshot(self, step: dict):
        path = step.get("output_path", os.path.join(self.output_dir, "manual_screenshot.png"))
        self.adb.screencap(path)

    def _handle_assert_text(self, step: dict):
        expected = step["text"]
        element = self.ui.find_element(text=expected)
        if element is None:
            raise AssertionError(f"Text '{expected}' not found on screen")

    def _handle_wait(self, step: dict):
        time.sleep(step.get("seconds", 1))

    def _handle_launch_app(self, step: dict):
        package = step["package"]
        activity = step.get("activity", "")
        if activity:
            self.adb.run_shell(f"am start -n {package}/{activity}")
        else:
            self.adb.run_shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")


