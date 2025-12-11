#!/usr/bin/env python3
"""
Simple export helper: look for mounted media under /media or /run/media and copy reports.
Returns destination path string on success, or None.
"""
import shutil
from pathlib import Path
import os
import glob

def _find_mount_points():
    # Common locations on Linux desktops: /media/$USER/* or /run/media/$USER/*
    points = []
    user = os.getenv("USER")
    for base in [f"/run/media/{user}", "/media"]:
        if os.path.isdir(base):
            for d in Path(base).iterdir():
                if d.is_dir():
                    points.append(str(d))
    return points

def save_report_to_usb(report_dir: Path):
    mounts = _find_mount_points()
    if not mounts:
        return None
    # pick the first mount with space
    for m in mounts:
        try:
            dest = Path(m) / "Apple-Pi-Diagnostics"
            dest.mkdir(exist_ok=True)
            # copy latest report file(s)
            for p in sorted(report_dir.glob("*")):
                if p.is_file():
                    shutil.copy2(p, dest / p.name)
            return str(dest)
        except Exception:
            continue
    return None
