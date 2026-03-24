"""ui_controller.py — Android UI automation via uiautomator2 with ADB fallback."""
from typing import Optional
from .adb_wrapper import ADBWrapper

try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False


class UIController:
    def __init__(self, serial: Optional[str] = None):
        self.serial = serial
        self._device = None
        self._adb = ADBWrapper(serial=serial)

    def connect(self, serial: Optional[str] = None) -> bool:
        """Connect to device via uiautomator2."""
        if not HAS_U2:
            print("uiautomator2 not installed — ADB-only mode")
            return False
        try:
            target = serial or self.serial
            self._device = u2.connect(target) if target else u2.connect()
            info = self._device.info
            print(f"Connected: {info.get('productName')} ({info.get('displayWidth')}x{info.get('displayHeight')})")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def tap(self, x: int, y: int) -> bool:
        """Tap at screen coordinates."""
        if self._device:
            self._device.click(x, y)
        else:
            self._adb.run_shell(f"input tap {x} {y}")
        return True

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.3) -> bool:
        """Swipe gesture."""
        if self._device:
            self._device.swipe(x1, y1, x2, y2, duration=duration)
        else:
            self._adb.run_shell(f"input swipe {x1} {y1} {x2} {y2} {int(duration*1000)}")
        return True

    def type_text(self, text: str) -> bool:
        """Type text into focused element."""
        if self._device:
            self._device.send_keys(text)
        else:
            self._adb.run_shell(f"input text '{text.replace(' ', '%s')}'")
        return True

    def press_key(self, keycode: str) -> bool:
        """Press key by name: HOME, BACK, ENTER, etc."""
        self._adb.run_shell(f"input keyevent KEYCODE_{keycode.upper()}")
        return True

    def find_element(self, text=None, resource_id=None, class_name=None, description=None):
        """Find UI element. Returns UiObject or None."""
        if not self._device:
            return None
        sel = {}
        if text: sel["text"] = text
        if resource_id: sel["resourceId"] = resource_id
        if class_name: sel["className"] = class_name
        if description: sel["description"] = description
        el = self._device(**sel)
        return el if el.exists else None

    def get_screenshot(self, output_path: str) -> bool:
        """Screenshot — uiautomator2 preferred, ADB screencap as headless fallback."""
        if self._device:
            try:
                self._device.screenshot(output_path)
                return True
            except Exception:
                pass
        return self._adb.screencap(output_path)

    def wait_for_element(self, text=None, resource_id=None, timeout: int = 10) -> bool:
        """Wait for element to appear within timeout seconds."""
        if not self._device:
            return False
        sel = {}
        if text: sel["text"] = text
        if resource_id: sel["resourceId"] = resource_id
        return self._device(**sel).wait(timeout=timeout)

    def get_screen_text(self) -> str:
        """Dump all visible UI text."""
        if self._device:
            try:
                return self._device.dump_hierarchy()
            except Exception:
                pass
        return self._adb.run_shell("uiautomator dump /dev/stdout")
