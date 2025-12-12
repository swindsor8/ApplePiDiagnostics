"""HDMI/display diagnostics.

Attempts to detect connected displays via `xrandr`, falling back to Raspberry Pi tools
when available. Returns connected display names and counts.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Dict, Any, List


def run_hdmi_detect() -> Dict[str, Any]:
    # prefer xrandr
    if shutil.which("xrandr"):
        try:
            out = subprocess.check_output(["xrandr", "--query"], text=True, stderr=subprocess.DEVNULL)
            displays: List[Dict[str, Any]] = []
            for ln in out.splitlines():
                if " connected" in ln:
                    parts = ln.split()
                    name = parts[0]
                    # try to find resolution token like 1920x1080
                    res = None
                    for p in parts:
                        if 'x' in p and p[0].isdigit():
                            res = p
                            break
                    displays.append({"line": ln.strip(), "name": name, "resolution": res})
            return {"status": "OK", "count": len(displays), "displays": displays}
        except Exception as e:
            return {"status": "FAIL", "note": str(e)}

    # fallback to vcgencmd or tvservice on Raspberry Pi
    if shutil.which("vcgencmd"):
        try:
            out = subprocess.check_output(["vcgencmd", "display_power", "0"], text=True)
            return {"status": "UNSUPPORTED", "note": "vcgencmd present but query not implemented"}
        except Exception as e:
            return {"status": "FAIL", "note": str(e)}

    return {"status": "UNSUPPORTED", "note": "No display detection tooling available"}


def run_hdmi_quick_test() -> Dict[str, Any]:
    return run_hdmi_detect()


if __name__ == "__main__":
    import json
    print(json.dumps(run_hdmi_quick_test()))
