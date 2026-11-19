#!/usr/bin/env python3
"""
Save reports to the SD card's FAT32 boot partition (/boot/firmware on Bookworm,
falling back to /boot on older Raspberry Pi OS releases).
Returns destination path on success or None.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import shutil


def _find_boot_dir() -> Optional[Path]:
    for candidate in (Path("/boot/firmware"), Path("/boot")):
        if candidate.is_dir():
            return candidate
    return None


def save_report_to_sdboot(report_dir: Path):
    boot_dir = _find_boot_dir()
    if boot_dir is None:
        return None
    dest = boot_dir / "Apple-Pi-Diagnostics"
    try:
        dest.mkdir(exist_ok=True)
        for p in sorted(Path(report_dir).glob("*")):
            if p.is_file():
                shutil.copy2(p, dest / p.name)
        return str(dest)
    except Exception:
        return None
