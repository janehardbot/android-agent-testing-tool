"""HTML and CSV report generation from test run results."""

import csv
import json
import os
from datetime import datetime, timezone
from typing import Optional


class ReportGenerator:
    """Generate HTML and CSV reports from run.json files."""

    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    def generate_html(self, run_result: dict, output_dir: Optional[str] = None) -> str:
        """Generate an HTML report from run results."""
        if output_dir is None:
            output_dir = run_result.get("output_dir", "/tmp/test_output")
        os.makedirs(output_dir, exist_ok=True)

        template_path = os.path.join(self.TEMPLATE_DIR, "report.html")
        if os.path.exists(template_path):
            try:
                from jinja2 import Template
                with open(template_path) as f:
                    template = Template(f.read())
                html = template.render(run=run_result, generated_at=datetime.now(timezone.utc).isoformat())
            except ImportError:
                html = self._fallback_html(run_result)
        else:
            html = self._fallback_html(run_result)

        report_path = os.path.join(output_dir, "report.html")
        with open(report_path, "w") as f:
            f.write(html)
        return report_path

    def generate_csv(self, run_result: dict, output_dir: Optional[str] = None) -> str:
        """Generate a CSV summary from run results."""
        if output_dir is None:
            output_dir = run_result.get("output_dir", "/tmp/test_output")
        os.makedirs(output_dir, exist_ok=True)

        csv_path = os.path.join(output_dir, "report.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Step", "Type", "Status", "Duration (ms)", "Error", "Screenshot"])
            for step in run_result.get("steps", []):
                writer.writerow([
                    step["name"],
                    step["type"],
                    step["status"],
                    f"{step['duration_ms']:.1f}",
                    step.get("error", ""),
                    step.get("screenshot", ""),
                ])
        return csv_path

    def _fallback_html(self, run: dict) -> str:
        """Generate HTML without Jinja2."""
        status_color = "#4caf50" if run["status"] == "pass" else "#f44336"
        rows = ""
        for s in run.get("steps", []):
            sc = "#4caf50" if s["status"] == "pass" else "#f44336" if s["status"] in ("fail", "error") else "#999"
            screenshot_cell = ""
            if s.get("screenshot") and os.path.exists(s["screenshot"]):
                fname = os.path.basename(s["screenshot"])
                screenshot_cell = f'<img src="{fname}" style="max-width:200px;max-height:150px;">'
            error_cell = s.get("error", "") or ""
            rows += f"""<tr>
                <td>{s['name']}</td><td>{s['type']}</td>
                <td style="color:{sc};font-weight:bold">{s['status']}</td>
                <td>{s['duration_ms']:.1f}ms</td>
                <td>{error_cell}</td><td>{screenshot_cell}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Test Report — {run['suite_name']}</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 2rem; background: #1a1a2e; color: #eee; }}
h1 {{ color: #e0e0e0; }} h2 {{ color: #aaa; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ padding: 8px 12px; border: 1px solid #333; text-align: left; }}
th {{ background: #16213e; }} tr:nth-child(even) {{ background: #0f3460; }}
.summary {{ display: flex; gap: 2rem; margin: 1rem 0; }}
.stat {{ background: #16213e; padding: 1rem; border-radius: 8px; min-width: 100px; text-align: center; }}
.stat .num {{ font-size: 2rem; font-weight: bold; }}
</style></head><body>
<h1>🧪 {run['suite_name']}</h1>
<p>Run ID: <code>{run['run_id']}</code> | Status: <span style="color:{status_color};font-weight:bold">{run['status'].upper()}</span> | Duration: {run['duration_ms']:.0f}ms</p>
<div class="summary">
    <div class="stat"><div class="num" style="color:#4caf50">{run['passed']}</div>Passed</div>
    <div class="stat"><div class="num" style="color:#f44336">{run['failed']}</div>Failed</div>
    <div class="stat"><div class="num" style="color:#ff9800">{run['errors']}</div>Errors</div>
    <div class="stat"><div class="num" style="color:#999">{run['skipped']}</div>Skipped</div>
</div>
<h2>Steps</h2>
<table><tr><th>Name</th><th>Type</th><th>Status</th><th>Duration</th><th>Error</th><th>Screenshot</th></tr>
{rows}
</table>
</body></html>"""
