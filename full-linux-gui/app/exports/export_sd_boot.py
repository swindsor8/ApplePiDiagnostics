#!/usr/bin/env python3
"""
Save reports to the SD card's boot partition (/boot). This is FAT32 and readable on other OSes.
Returns destination path on success or None.
"""
from pathlib import Path
import shutil
import os

def save_report_to_sdboot(report_dir: Path):
    boot_dir = Path("/boot")  # on running Pi, /boot is the FAT partition
    if not boot_dir.is_dir():
        return None
    dest = boot_dir / "Apple-Pi-Diagnostics"
    try:
        dest.mkdir(exist_ok=True)
        for p in sorted(report_dir.glob("*")):
            if p.is_file():
                shutil.copy2(p, dest / p.name)
        return str(dest)
    except Exception:
        return None
