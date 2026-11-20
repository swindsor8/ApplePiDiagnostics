#!/usr/bin/env python3
"""Read-only hardware bus and peripheral probes: I2C, SPI, Camera, Bluetooth, Audio."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List


def _probe_i2c() -> List[str]:
    dev_root = Path("/dev")
    if not dev_root.is_dir():
        return []
    return sorted(p.name for p in dev_root.glob("i2c-*"))


def _probe_spi() -> List[str]:
    dev_root = Path("/dev")
    if not dev_root.is_dir():
        return []
    return sorted(p.name for p in dev_root.glob("spidev*"))


def _probe_bluetooth() -> List[str]:
    bt_root = Path("/sys/class/bluetooth")
    if not bt_root.is_dir():
        return []
    return sorted(p.name for p in bt_root.iterdir())


def _probe_audio() -> List[str]:
    cards: List[str] = []
    if shutil.which("aplay"):
        try:
            out = subprocess.check_output(
                ["aplay", "-l"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            for ln in out.splitlines():
                if ln.startswith("card "):
                    cards.append(ln.strip())
            if cards:
                return cards
        except Exception:
            pass
    asound = Path("/proc/asound/cards")
    if asound.is_file():
        try:
            for ln in asound.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = ln.strip()
                if stripped and stripped[0].isdigit():
                    cards.append(stripped)
        except OSError:
            pass
    return cards


def _probe_cameras() -> List[str]:
    for tool in ("rpicam-hello", "libcamera-hello"):
        if shutil.which(tool):
            try:
                out = subprocess.check_output(
                    [tool, "--list-cameras"],
                    text=True,
                    stderr=subprocess.STDOUT,
                    timeout=5,
                )
                cams = [
                    ln.strip()
                    for ln in out.splitlines()
                    if ln.strip() and ln.strip()[0].isdigit() and ":" in ln
                ]
                if cams:
                    return cams
            except Exception:
                pass
    dev_root = Path("/dev")
    if dev_root.is_dir():
        v4l = sorted(p.name for p in dev_root.glob("video*"))
        if v4l:
            return v4l[:4]
    return []


def run_peripherals_test() -> Dict[str, Any]:
    """Probe I2C, SPI, Camera, Bluetooth, and Audio subsystems safely."""
    i2c = _probe_i2c()
    spi = _probe_spi()
    bluetooth = _probe_bluetooth()
    audio = _probe_audio()
    cameras = _probe_cameras()

    detected = sum(1 for group in (i2c, spi, bluetooth, audio, cameras) if group)
    status = "OK" if detected > 0 else "UNSUPPORTED"

    parts: List[str] = []
    parts.append(f"I2C: {len(i2c)}")
    parts.append(f"SPI: {len(spi)}")
    parts.append(f"BT: {len(bluetooth)}")
    parts.append(f"Audio: {len(audio)}")
    parts.append(f"Cam: {len(cameras)}")

    return {
        "status": status,
        "note": " · ".join(parts),
        "count": detected,
        "i2c_buses": i2c,
        "spi_devices": spi,
        "bluetooth_adapters": bluetooth,
        "audio_devices": audio,
        "cameras": cameras,
    }


def run_peripherals_quick_test() -> Dict[str, Any]:
    return run_peripherals_test()


if __name__ == "__main__":
    import json
    print(json.dumps(run_peripherals_quick_test(), indent=2))
