# Android Agent Testing Tool

AI-agent-controlled Android automation framework for test execution, logging, reporting, and web GUI.

## Stack
- **Device control:** `uiautomator2` + `adbutils` (Python)
- **Test format:** YAML / JSON
- **Reporting:** HTML, JSON, CSV
- **Web GUI:** FastAPI + vanilla JS

## Project Structure
```
agent_control/   # Device control library (ADB, UIAutomator2)
tests/           # Test suite runner + YAML/JSON specs
reporting/       # Log capture, report generation
web_gui/         # FastAPI dashboard
docs/            # Architecture docs (ADR)
```

## Setup
```bash
pip install -r requirements.txt
adb devices  # ensure device/emulator connected
python web_gui/main.py  # start dashboard on :8765
```

## Status
- [x] Phase 1: Architecture Decision (ADR-001)
- [ ] Phase 2: Agent Control Layer
- [ ] Phase 3: Test Execution Engine
- [ ] Phase 4: Logging & Reporting
- [ ] Phase 5: Web GUI
