"""HDMI/display diagnostics.

Attempts to detect connected displays via `xrandr`, falling back to Linux DRM
sysfs (`/sys/class/drm`) and read-only `vcgencmd` queries when available.
Returns connected display names and counts.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Dict, Any, List


def _detect_via_drm_sysfs() -> List[Dict[str, Any]]:
    """Inspect /sys/class/drm/card*-*/status for connected displays."""
    displays: List[Dict[str, Any]] = []
    drm_root = Path("/sys/class/drm")
    if not drm_root.is_dir():
        return displays

    for status_file in sorted(drm_root.glob("card*-*/status")):
        try:
            state = status_file.read_text(encoding="utf-8", errors="ignore").strip().lower()
        except OSError:
            continue
        if state != "connected":
            continue

        connector_dir = status_file.parent
        name = connector_dir.name
        resolution = None
        modes_file = connector_dir / "modes"
        if modes_file.is_file():
            try:
                first_mode = modes_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                if first_mode:
                    resolution = first_mode[0].strip() or None
            except OSError:
                pass
        displays.append({"name": name, "resolution": resolution, "line": f"{name} connected"})
    return displays


def run_hdmi_detect() -> Dict[str, Any]:
    # Prefer xrandr when an X11 display is active
    if shutil.which("xrandr"):
        try:
            out = subprocess.check_output(
                ["xrandr", "--query"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            displays: List[Dict[str, Any]] = []
            for ln in out.splitlines():
                if " connected" in ln:
                    parts = ln.split()
                    name = parts[0]
                    res = None
                    for p in parts:
                        if "x" in p and p[0].isdigit():
                            res = p
                            break
                    displays.append({"line": ln.strip(), "name": name, "resolution": res})
            return {"status": "OK", "count": len(displays), "displays": displays}
        except Exception:
            # Fall through to DRM sysfs / vcgencmd when DISPLAY isn't set or xrandr fails
            pass

    # Fallback 1: Linux DRM sysfs (works on Pi 4/5 KMS without X11)
    drm_displays = _detect_via_drm_sysfs()
    if drm_displays:
        return {"status": "OK", "count": len(drm_displays), "displays": drm_displays}

    # Fallback 2: read-only vcgencmd query (-1 queries state; NEVER pass 0, which turns HDMI off)
    if shutil.which("vcgencmd"):
        try:
            out = subprocess.check_output(
                ["vcgencmd", "display_power", "-1"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
            powered = out.endswith("=1")
            return {
                "status": "OK" if powered else "WARNING",
                "count": 1 if powered else 0,
                "displays": [{"name": "HDMI", "resolution": None, "line": out}] if powered else [],
                "note": out,
            }
        except Exception as e:
            return {"status": "FAIL", "note": str(e)}

    return {"status": "UNSUPPORTED", "note": "No display detection tooling available"}


def run_hdmi_quick_test() -> Dict[str, Any]:
    return run_hdmi_detect()


if __name__ == "__main__":
    import json
    print(json.dumps(run_hdmi_quick_test()))
