"""FastAPI web dashboard for the Android Agent Testing Tool."""

import json
import os
import glob
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent_control.adb_wrapper import ADBWrapper
from tests.runner import TestRunner
from reporting.logger import RunLogger
from reporting.report import ReportGenerator

app = FastAPI(title="Android Agent Testing Tool", version="0.1.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
OUTPUT_BASE = os.environ.get("AATT_OUTPUT_DIR", "/tmp/test_output")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard showing device status, recent runs, and trigger button."""
    # Get device info
    adb = ADBWrapper()
    try:
        devices = adb.list_devices()
    except Exception:
        devices = []

    # Get recent runs
    runs = _get_recent_runs(limit=10)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "devices": devices,
        "runs": runs,
        "now": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/devices")
async def api_devices():
    """List connected ADB devices."""
    adb = ADBWrapper()
    try:
        devices = adb.list_devices()
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        return {"devices": [], "count": 0, "error": str(e)}


@app.get("/api/runs")
async def api_runs(limit: int = 20):
    """List recent test runs."""
    runs = _get_recent_runs(limit=limit)
    return {"runs": runs}


@app.get("/api/runs/{run_id}")
async def api_run_detail(run_id: str):
    """Get detail for a specific run."""
    run_dir = os.path.join(OUTPUT_BASE, run_id)
    run_json = os.path.join(run_dir, "run.json")
    if not os.path.exists(run_json):
        raise HTTPException(status_code=404, detail="Run not found")
    with open(run_json) as f:
        return json.load(f)


@app.get("/api/runs/{run_id}/report")
async def api_run_report(run_id: str):
    """Get or generate HTML report for a run."""
    run_dir = os.path.join(OUTPUT_BASE, run_id)
    report_path = os.path.join(run_dir, "report.html")

    if not os.path.exists(report_path):
        run_json = os.path.join(run_dir, "run.json")
        if not os.path.exists(run_json):
            raise HTTPException(status_code=404, detail="Run not found")
        with open(run_json) as f:
            run_result = json.load(f)
        gen = ReportGenerator()
        gen.generate_html(run_result, run_dir)

    return FileResponse(report_path, media_type="text/html")


@app.post("/api/trigger")
async def api_trigger(request: Request):
    """Trigger a test run from a suite file path or inline suite."""
    body = await request.json()
    suite_path = body.get("suite_path")
    suite_data = body.get("suite")

    runner = TestRunner(output_base=OUTPUT_BASE)
    logger = RunLogger(output_base=OUTPUT_BASE)
    reporter = ReportGenerator()

    try:
        if suite_data:
            result = runner.run_suite_from_dict(suite_data)
        elif suite_path:
            result = runner.run_suite(suite_path)
        else:
            raise HTTPException(status_code=400, detail="Provide suite_path or suite")

        logger.log_run(result)
        logger.append_to_history(result)
        reporter.generate_html(result)
        reporter.generate_csv(result)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/suites")
async def api_suites():
    """List available test suite files."""
    suite_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests")
    suites = []
    for pattern in ("*.yaml", "*.yml", "*.json"):
        for path in glob.glob(os.path.join(suite_dir, pattern)):
            if os.path.basename(path).startswith("__"):
                continue
            suites.append({
                "name": os.path.basename(path),
                "path": path,
            })
    return {"suites": suites}


def _get_recent_runs(limit: int = 10) -> list:
    """Get recent runs from the output directory."""
    runs = []
    if not os.path.exists(OUTPUT_BASE):
        return runs
    for entry in sorted(os.listdir(OUTPUT_BASE), reverse=True):
        run_json = os.path.join(OUTPUT_BASE, entry, "run.json")
        if os.path.isfile(run_json):
            try:
                with open(run_json) as f:
                    data = json.load(f)
                runs.append({
                    "run_id": data.get("run_id", entry),
                    "suite_name": data.get("suite_name", "Unknown"),
                    "status": data.get("status", "unknown"),
                    "passed": data.get("passed", 0),
                    "failed": data.get("failed", 0),
                    "duration_ms": data.get("duration_ms", 0),
                    "timestamp": data.get("timestamp", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        if len(runs) >= limit:
            break
    return runs


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
