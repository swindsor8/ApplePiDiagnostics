#!/usr/bin/env python3
"""Export helper for USB flash drives.

Checks mounted removable drives under /media, /run/media, and /mnt/apd-usb,
and on Raspberry Pi OS Lite (which has no desktop automounter) attempts to
mount any unmounted removable USB partition via ``udisksctl`` before copying.
Returns destination path string on success, or None.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional


def _find_mount_points() -> List[str]:
    """Return writable mount directories for connected USB media."""
    points: List[str] = []
    seen = set()
    user = os.getenv("USER") or ""

    def _add(path: Path) -> None:
        resolved = str(path)
        if resolved not in seen and path.is_dir() and os.path.ismount(resolved):
            seen.add(resolved)
            points.append(resolved)

    search_roots = [
        Path(f"/run/media/{user}") if user else None,
        Path(f"/media/{user}") if user else None,
        Path("/media"),
        Path("/mnt/apd-usb"),
    ]
    for base in search_roots:
        if base is None or not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            if os.path.ismount(str(child)):
                _add(child)
            else:
                # Handle /media/<user>/<volume>
                try:
                    for sub in sorted(child.iterdir()):
                        if sub.is_dir() and os.path.ismount(str(sub)):
                            _add(sub)
                except OSError:
                    pass

    # Fallback: check lsblk for mounted USB/removable partitions anywhere
    if shutil.which("lsblk"):
        try:
            out = subprocess.check_output(
                ["lsblk", "-J", "-o", "NAME,RM,TYPE,MOUNTPOINT,TRAN"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            data = json.loads(out)
            for dev in data.get("blockdevices", []):
                is_usb = dev.get("tran") == "usb" or bool(dev.get("rm"))
                if not is_usb:
                    continue
                for node in [dev, *(dev.get("children") or [])]:
                    mp = node.get("mountpoint")
                    if mp and mp not in ("/", "/boot", "/boot/firmware") and os.path.isdir(mp):
                        if mp not in seen:
                            seen.add(mp)
                            points.append(mp)
        except Exception:
            pass

    return points


def _try_automount_usb() -> List[str]:
    """Attempt to mount unmounted removable USB partitions via udisksctl."""
    mounted: List[str] = []
    if not shutil.which("lsblk") or not shutil.which("udisksctl"):
        return mounted
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,RM,TYPE,MOUNTPOINT,TRAN,FSTYPE"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        data = json.loads(out)
        for dev in data.get("blockdevices", []):
            is_usb = dev.get("tran") == "usb" or bool(dev.get("rm"))
            if not is_usb:
                continue
            for part in dev.get("children") or [dev]:
                if part.get("mountpoint") or not part.get("fstype"):
                    continue
                dev_node = f"/dev/{part['name']}"
                proc = subprocess.run(
                    ["udisksctl", "mount", "--no-user-interaction", "-b", dev_node],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if proc.returncode == 0 and " at " in proc.stdout:
                    mp = proc.stdout.split(" at ", 1)[1].strip().rstrip(".")
                    if os.path.isdir(mp):
                        mounted.append(mp)
    except Exception:
        pass
    return mounted


def save_report_to_usb(report_dir: Path) -> Optional[str]:
    mounts = _find_mount_points()
    if not mounts:
        mounts = _try_automount_usb()
    if not mounts:
        return None
    for m in mounts:
        try:
            dest = Path(m) / "Apple-Pi-Diagnostics"
            dest.mkdir(exist_ok=True)
            for p in sorted(Path(report_dir).glob("*")):
                if p.is_file():
                    shutil.copy2(p, dest / p.name)
            return str(dest)
        except Exception:
            continue
    return None
