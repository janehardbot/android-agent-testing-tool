"""example.py — Basic agent control demonstration."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agent_control import ADBWrapper, UIController

def main():
    adb = ADBWrapper()
    devices = adb.list_devices()
    print(f"Connected devices: {devices}")
    if not devices:
        print("No devices found. Connect a device or start an emulator.")
        return

    print("Taking ADB screenshot (headless safe)...")
    if adb.screencap("/tmp/screen_adb.png"):
        print("  ✅ Saved to /tmp/screen_adb.png")

    ui = UIController()
    if ui.connect():
        ui.press_key("HOME")
        el = ui.find_element(text="Chrome")
        if el:
            print("Found Chrome — tapping")
            el.click()
        ui.get_screenshot("/tmp/screen_ui2.png")
    else:
        model = adb.run_shell("getprop ro.product.model")
        print(f"ADB-only mode. Device: {model}")

if __name__ == "__main__":
    main()
