#!/usr/bin/env python3
"""Bootloader, EEPROM, board identity, and /boot/firmware health diagnostics."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional


def _read_text(path: Path) -> Optional[str]:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore").strip("\x00 \r\n")
    except OSError:
        pass
    return None


def _parse_cpuinfo_fields() -> Dict[str, str]:
    info: Dict[str, str] = {}
    text = _read_text(Path("/proc/cpuinfo"))
    if not text:
        return info
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        k = key.strip().lower()
        if k in ("hardware", "revision", "serial", "model"):
            info[k] = val.strip()
    return info


def run_bootloader_test() -> Dict[str, Any]:
    """Read Raspberry Pi board identity, EEPROM version, and boot partition files."""
    model = _read_text(Path("/proc/device-tree/model"))
    serial = _read_text(Path("/proc/device-tree/serial-number"))
    cpuinfo = _parse_cpuinfo_fields()
    if not serial:
        serial = cpuinfo.get("serial")
    revision = cpuinfo.get("revision")

    bootloader_version: Optional[str] = None
    if shutil.which("vcgencmd"):
        try:
            out = subprocess.check_output(
                ["vcgencmd", "bootloader_version"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=3,
            ).strip()
            if out:
                bootloader_version = " ".join(out.splitlines()[:2])
        except Exception:
            pass

    eeprom_status: Optional[str] = None
    if shutil.which("rpi-eeprom-update"):
        try:
            proc = subprocess.run(
                ["rpi-eeprom-update"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            combined = (proc.stdout or proc.stderr or "").strip()
            if combined:
                first_lines = [ln.strip() for ln in combined.splitlines() if ln.strip()][:4]
                eeprom_status = " | ".join(first_lines)
        except Exception:
            pass

    boot_dir: Optional[Path] = None
    for candidate in (Path("/boot/firmware"), Path("/boot")):
        if candidate.is_dir():
            boot_dir = candidate
            break

    is_pi = bool(model and "raspberry pi" in model.lower()) or bool(bootloader_version)

    found_files: List[str] = []
    missing_files: List[str] = []
    if boot_dir is not None and is_pi:
        required = ["config.txt", "cmdline.txt"]
        kernel_candidates = ["kernel8.img", "kernel_2712.img", "kernel7l.img", "kernel.img"]
        for name in required:
            if (boot_dir / name).exists():
                found_files.append(name)
            else:
                missing_files.append(name)
        present_kernels = [k for k in kernel_candidates if (boot_dir / k).exists()]
        if present_kernels:
            found_files.extend(present_kernels)
        else:
            missing_files.append("kernel image (kernel8.img/kernel_2712.img)")

    if not is_pi:
        return {
            "status": "UNSUPPORTED",
            "note": "Not running on Raspberry Pi hardware; EEPROM/bootloader checks skipped",
            "model": model or cpuinfo.get("model"),
            "serial": serial,
            "revision": revision,
            "bootloader_version": bootloader_version,
            "eeprom_status": eeprom_status,
            "boot_dir": str(boot_dir) if boot_dir else None,
            "found_files": found_files,
            "missing_files": missing_files,
        }

    status = "OK"
    notes: List[str] = []
    if missing_files:
        status = "WARNING"
        notes.append(f"Missing boot files in {boot_dir}: {', '.join(missing_files)}")
    if eeprom_status and "UPDATE AVAILABLE" in eeprom_status.upper():
        if status == "OK":
            status = "WARNING"
        notes.append("Bootloader EEPROM update available")
    if not notes:
        notes.append(f"Boot partition ({boot_dir}) and bootloader look healthy")

    return {
        "status": status,
        "note": "; ".join(notes),
        "model": model,
        "serial": serial,
        "revision": revision,
        "bootloader_version": bootloader_version,
        "eeprom_status": eeprom_status,
        "boot_dir": str(boot_dir) if boot_dir else None,
        "found_files": found_files,
        "missing_files": missing_files,
    }


def run_bootloader_quick_test() -> Dict[str, Any]:
    return run_bootloader_test()


if __name__ == "__main__":
    import json
    print(json.dumps(run_bootloader_quick_test(), indent=2))
