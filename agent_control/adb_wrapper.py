"""adb_wrapper.py — ADB device control via adbutils + subprocess fallback."""
import subprocess
from typing import Optional

try:
    import adbutils
    HAS_ADBUTILS = True
except ImportError:
    HAS_ADBUTILS = False


class ADBWrapper:
    def __init__(self, serial: Optional[str] = None):
        self.serial = serial
        self._device = None
        if HAS_ADBUTILS:
            adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
            self._device = adb.device(serial) if serial else adb.device()

    def _adb(self, *args) -> subprocess.CompletedProcess:
        cmd = ["adb"] + (["-s", self.serial] if self.serial else []) + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    def run_shell(self, cmd: str) -> str:
        """Run ADB shell command, return stdout."""
        if self._device:
            return self._device.shell(cmd)
        return self._adb("shell", cmd).stdout.strip()

    def install_apk(self, path: str) -> str:
        """Install APK on device."""
        r = self._adb("install", "-r", path)
        return r.stdout + r.stderr

    def get_logcat(self, lines: int = 100) -> str:
        """Fetch recent logcat output."""
        return self.run_shell(f"logcat -d -t {lines}")

    def list_devices(self) -> list:
        """List connected ADB device serials."""
        if HAS_ADBUTILS:
            adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
            return [d.serial for d in adb.device_list()]
        lines = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout.splitlines()[1:]
        return [l.split()[0] for l in lines if l.strip() and "offline" not in l]

    def screencap(self, output_path: str) -> bool:
        """Screenshot via ADB — headless safe, no display required."""
        cmd = ["adb"] + (["-s", self.serial] if self.serial else []) + ["exec-out", "screencap", "-p"]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=15)
            if r.returncode == 0 and r.stdout:
                with open(output_path, "wb") as f:
                    f.write(r.stdout)
                return True
        except Exception:
            pass
        return False

    def push_file(self, local: str, remote: str) -> str:
        return self._adb("push", local, remote).stdout

    def pull_file(self, remote: str, local: str) -> str:
        return self._adb("pull", remote, local).stdout
