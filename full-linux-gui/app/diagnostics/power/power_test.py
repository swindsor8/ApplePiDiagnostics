#!/usr/bin/env python3
"""Power, voltage, clock, and thermal throttling diagnostics for Raspberry Pi.

Decodes all 8 firmware throttle flags from ``vcgencmd get_throttled`` (or
``/sys/devices/platform/soc/soc:firmware/get_throttled``) and reads core/SDRAM
voltages, SoC temperature, and ARM clock frequency.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

_THROTTLE_BITS = {
    0: ("under_voltage_now", "Under-voltage currently detected"),
    1: ("freq_capped_now", "ARM frequency currently capped"),
    2: ("throttled_now", "CPU currently throttled"),
    3: ("soft_temp_limit_now", "Soft temperature limit currently active"),
    16: ("under_voltage_occurred", "Under-voltage occurred since boot"),
    17: ("freq_capped_occurred", "ARM frequency capping occurred since boot"),
    18: ("throttled_occurred", "Throttling occurred since boot"),
    19: ("soft_temp_limit_occurred", "Soft temperature limit occurred since boot"),
}


def decode_throttled_flags(raw_value: int) -> Dict[str, Any]:
    """Decode a Raspberry Pi ``get_throttled`` bitmask into active/historical flags."""
    active: List[str] = []
    historical: List[str] = []
    flags: Dict[str, bool] = {}

    for bit, (key, desc) in _THROTTLE_BITS.items():
        is_set = bool(raw_value & (1 << bit))
        flags[key] = is_set
        if is_set:
            if bit < 16:
                active.append(desc)
            else:
                historical.append(desc)

    return {
        "raw": hex(raw_value),
        "raw_int": raw_value,
        "flags": flags,
        "active_issues": active,
        "historical_issues": historical,
    }


def _run_vcgencmd(*args: str) -> Optional[str]:
    if not shutil.which("vcgencmd"):
        return None
    try:
        return subprocess.check_output(
            ["vcgencmd", *args],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).strip()
    except Exception:
        return None


def _read_sysfs_temperature() -> Optional[float]:
    tz = Path("/sys/class/thermal/thermal_zone0/temp")
    if tz.is_file():
        try:
            return int(tz.read_text(encoding="utf-8").strip()) / 1000.0
        except Exception:
            pass
    return None


def _read_sysfs_throttled() -> Optional[int]:
    path = Path("/sys/devices/platform/soc/soc:firmware/get_throttled")
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8").strip()
            return int(text, 16) if text.startswith("0x") else int(text, 16)
        except Exception:
            pass
    return None


def run_power_test() -> Dict[str, Any]:
    """Inspect Raspberry Pi power supply, voltages, temperature, and ARM clock."""
    throttled_int: Optional[int] = None
    vc_throttled = _run_vcgencmd("get_throttled")
    if vc_throttled:
        m = re.search(r"0x[0-9a-fA-F]+", vc_throttled)
        if m:
            throttled_int = int(m.group(0), 16)
    if throttled_int is None:
        throttled_int = _read_sysfs_throttled()

    voltages: Dict[str, float] = {}
    for rail in ("core", "sdram_c", "sdram_i", "sdram_p"):
        out = _run_vcgencmd("measure_volts", rail)
        if out:
            m = re.search(r"([0-9]+\.[0-9]+)V", out)
            if m:
                voltages[rail] = float(m.group(1))

    temp_c: Optional[float] = None
    vc_temp = _run_vcgencmd("measure_temp")
    if vc_temp:
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", vc_temp)
        if m:
            temp_c = float(m.group(1))
    if temp_c is None:
        temp_c = _read_sysfs_temperature()

    arm_clock_mhz: Optional[float] = None
    vc_clock = _run_vcgencmd("measure_clock", "arm")
    if vc_clock and "=" in vc_clock:
        try:
            arm_clock_mhz = round(int(vc_clock.split("=", 1)[1]) / 1_000_000.0, 1)
        except ValueError:
            pass

    if throttled_int is None and not voltages and temp_c is None:
        return {
            "status": "UNSUPPORTED",
            "note": "Raspberry Pi firmware power telemetry (vcgencmd) not available on this host",
            "throttled": None,
            "voltages": {},
            "temperature_c": None,
            "arm_clock_mhz": None,
        }

    decoded = decode_throttled_flags(throttled_int) if throttled_int is not None else None
    notes: List[str] = []
    status = "OK"

    if decoded:
        if decoded["active_issues"]:
            status = "FAIL"
            notes.extend(decoded["active_issues"])
        elif decoded["historical_issues"]:
            status = "WARNING"
            notes.extend(decoded["historical_issues"])
    else:
        notes.append("Firmware throttle flags unavailable (non-Pi host); thermal sensor read OK")

    if temp_c is not None:
        if temp_c >= 82.0:
            status = "FAIL"
            notes.append(f"Critical SoC temperature ({temp_c:.1f} °C)")
        elif temp_c >= 75.0 and status == "OK":
            status = "WARNING"
            notes.append(f"Elevated SoC temperature ({temp_c:.1f} °C)")

    if not notes:
        notes.append("Power supply and thermals look healthy (no under-voltage or throttling)")

    return {
        "status": status,
        "note": "; ".join(notes),
        "throttled": decoded,
        "voltages": voltages,
        "temperature_c": temp_c,
        "arm_clock_mhz": arm_clock_mhz,
    }


def run_power_quick_test() -> Dict[str, Any]:
    return run_power_test()


if __name__ == "__main__":
    import json
    print(json.dumps(run_power_quick_test(), indent=2))
