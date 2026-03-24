# ADR-001: Architecture Decision — Android Agent Testing Tool

## Status: Accepted

## Context
We need an AI-agent-controlled Android testing tool that:
- Allows an AI agent to fully control an Android device
- Runs automated test suites
- Captures logs, screenshots, timing measurements
- Generates structured reports (HTML, JSON, CSV)
- Provides a web GUI dashboard

## Decision: Appium + UIAutomator2 + ADB hybrid

### Chosen Stack
| Layer | Technology | Reason |
|-------|------------|--------|
| Device control | `uiautomator2` (Python) | Direct Python API, no server needed, fast |
| Shell/ADB ops | `adbutils` | Clean Python ADB wrapper |
| Test definition | YAML/JSON | Human-readable, agent-writable |
| Reporting | Python + Jinja2 | HTML/JSON/CSV without heavy deps |
| Web GUI | FastAPI + vanilla JS | Consistent with Mission Control style |
| Screenshots | ADB screencap (fallback) | Works headless, no display required |

### Rejected Alternatives
- **Appium**: Adds server complexity, overkill for agent-only control
- **Maestro**: YAML-only, limited Python API, harder for agent to control dynamically
- **Espresso**: Android-only, requires app instrumentation, not external-agent-friendly
- **Detox**: React Native focused, not suitable for generic app testing

## Architecture Overview
```
Agent
  └─► agent_control/ (Python lib)
        ├── adb_wrapper.py      # shell, install, logcat
        ├── ui_controller.py    # tap, swipe, type, screenshot via uiautomator2
        └── element_finder.py   # find by id, text, class
  └─► test_runner/
        ├── runner.py           # YAML/JSON test executor
        ├── step_executor.py    # individual step handler
        └── screenshot.py       # ADB-based headless-safe capture
  └─► reporting/
        ├── logger.py           # structured JSON logs
        ├── report.py           # HTML/CSV/JSON report generator
        └── templates/          # Jinja2 HTML templates
  └─► web_gui/
        ├── main.py             # FastAPI app
        ├── static/             # JS frontend
        └── templates/          # HTML pages
```

## Complexity Estimates
- Phase 2 (Control Layer): Medium
- Phase 3 (Test Runner): Medium
- Phase 4 (Reporting): Low
- Phase 5 (Web GUI): Medium
