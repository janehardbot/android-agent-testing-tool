"""agent_control — Android device control library for AI agents.

Usage:
    from agent_control import ADBWrapper, UIController

    adb = ADBWrapper()
    adb.list_devices()
    adb.screencap("/tmp/screen.png")

    ui = UIController()
    ui.connect()
    ui.tap(500, 300)
    ui.get_screenshot("/tmp/screen.png")
"""
from .adb_wrapper import ADBWrapper
from .ui_controller import UIController

__all__ = ["ADBWrapper", "UIController"]
