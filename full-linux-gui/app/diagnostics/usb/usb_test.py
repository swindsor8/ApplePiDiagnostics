"""USB enumeration diagnostics.

Uses `lsusb` if available; otherwise returns UNSUPPORTED.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Dict, Any, List


def run_usb_enumeration() -> Dict[str, Any]:
    if not shutil.which("lsusb"):
        return {"status": "UNSUPPORTED", "note": "lsusb not available"}

    try:
        out = subprocess.check_output(["lsusb"], text=True)
        devices: List[str] = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return {"status": "OK", "count": len(devices), "devices": devices}
    except Exception as e:
        return {"status": "FAIL", "note": str(e)}


def run_usb_quick_test() -> Dict[str, Any]:
    return run_usb_enumeration()


def run_usb_speed_test(mount_point: str, file_size_mb: int = 16) -> Dict[str, Any]:
    """Measure sequential write/read performance on a mounted USB filesystem.

    If `mount_point` is not writable or doesn't exist, returns FAIL.
    """
    import time
    import tempfile
    import os

    if not mount_point or not os.path.isdir(mount_point):
        return {"status": "FAIL", "note": "mount_point not found"}

    try:
        fname = os.path.join(mount_point, f"apd_usb_test_{int(time.time())}.bin")
        data = b"\xAA" * 1024 * 1024
        t0 = time.time()
        with open(fname, "wb") as f:
            for _ in range(file_size_mb):
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        t1 = time.time()
        write_mb_s = file_size_mb / max(1e-6, (t1 - t0))

        # read back
        t0 = time.time()
        with open(fname, "rb") as f:
            while True:
                d = f.read(1024 * 1024)
                if not d:
                    break
        t1 = time.time()
        read_mb_s = file_size_mb / max(1e-6, (t1 - t0))

        try:
            os.remove(fname)
        except Exception:
            pass

        return {"status": "OK", "write_mb_s": write_mb_s, "read_mb_s": read_mb_s}
    except Exception as e:
        return {"status": "FAIL", "note": str(e)}


if __name__ == "__main__":
    import json
    print(json.dumps(run_usb_quick_test()))
