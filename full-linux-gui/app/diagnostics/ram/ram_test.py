#!/usr/bin/env python3
"""RAM diagnostic: allocate, write, verify memory buffers to detect faults and
measure throughput.

API:
    run_ram_test(total_mb=256, chunk_mb=16, passes=1, progress_callback=None)

The test will allocate `chunk_mb` chunks repeatedly until `total_mb` is covered
(or until memory allocation fails), write a pattern, read back and verify.
It reports throughput and errors and supports a `progress_callback(sample_dict)`
for live updates (same pattern as CPU test).
"""
from __future__ import annotations

import time
from typing import Optional, Dict, Any, List

import psutil


def _make_pattern(size: int) -> bytearray:
    # simple pseudo-random pattern deterministic by index
    b = bytearray(size)
    for i in range(size):
        b[i] = (i * 31 + 17) & 0xFF
    return b


def run_ram_test(total_mb: int = 256, chunk_mb: int = 16, passes: int = 1, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """Run RAM write/read verification.

    Args:
        total_mb: target total memory to test in megabytes (default 256MB).
        chunk_mb: size of each test buffer in megabytes (default 16MB).
        passes: number of full-pass iterations to perform.
        progress_callback: optional callable receiving progress dicts.

    Returns:
        Dict with `status`, `tested_mb`, `errors`, `throughput_mb_s`, `samples`.
    """
    samples: List[Dict[str, Any]] = []
    errors: List[str] = []
    tested_mb = 0

    chunk = max(1, int(chunk_mb)) * 1024 * 1024
    target_bytes = int(total_mb) * 1024 * 1024

    # safety: do not attempt to allocate more than ~75% available memory
    mem = psutil.virtual_memory()
    safe_limit = int(mem.available * 0.75)
    if target_bytes > safe_limit:
        # reduce target to safe_limit
        target_bytes = safe_limit

    start_time = time.time()
    try:
        for p in range(max(1, int(passes))):
            bytes_written = 0
            while bytes_written < target_bytes:
                to_alloc = min(chunk, target_bytes - bytes_written)
                t0 = time.time()
                try:
                    buf = bytearray(to_alloc)
                except MemoryError as me:
                    errors.append(f"Allocation failed at {bytes_written} bytes: {me}")
                    break

                # write pattern
                pat = _make_pattern(to_alloc)
                buf[:] = pat
                write_time = time.time() - t0

                # read/verify
                t1 = time.time()
                if buf != pat:
                    errors.append(f"Data mismatch at offset {bytes_written}")
                read_time = time.time() - t1

                bytes_written += to_alloc
                tested_mb = bytes_written / (1024 * 1024)

                sample = {
                    "pass": p + 1,
                    "tested_mb": tested_mb,
                    "chunk_mb": to_alloc / (1024 * 1024),
                    "write_time_s": write_time,
                    "read_time_s": read_time,
                    "timestamp": time.time(),
                }
                samples.append(sample)
                try:
                    if progress_callback:
                        progress_callback(sample)
                except Exception:
                    pass

                # free buffer
                del buf
                del pat

            # end while for this pass
    except Exception as e:
        errors.append(str(e))

    elapsed = max(1e-6, time.time() - start_time)
    throughput_mb_s = (tested_mb / elapsed) if elapsed > 0 else 0.0

    status = "OK" if not errors else "FAIL"

    return {
        "status": status,
        "tested_mb": tested_mb,
        "errors": errors,
        "throughput_mb_s": throughput_mb_s,
        "samples": samples,
    }


def run_ram_quick_test(total_mb: int = 64, chunk_mb: int = 16, passes: int = 1, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """Quick RAM test wrapper with smaller defaults."""
    return run_ram_test(total_mb=total_mb, chunk_mb=chunk_mb, passes=passes, progress_callback=progress_callback)


def run_ram_stress_ng(total_mb: int = 512, workers: int = 1, duration: int = 60) -> Dict[str, Any]:
    """Run stress-ng VM stress test if available; fallback to run_ram_test.

    Uses `stress-ng --vm <workers> --vm-bytes <total_mb>M --timeout <duration>s`.
    Returns a dict with status and subprocess output or fallback summary.
    """
    import shutil
    import subprocess

    if shutil.which("stress-ng"):
        cmd = [
            "stress-ng",
            "--vm",
            str(workers),
            "--vm-bytes",
            f"{int(total_mb)}M",
            "--timeout",
            f"{int(duration)}s",
            "--metrics-brief",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            status = "OK" if proc.returncode == 0 else "FAIL"
            return {"status": status, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    # fallback to internal RAM test
    res = run_ram_test(total_mb=min(int(total_mb), 256), chunk_mb=int(chunk_mb) if (chunk_mb := 16) else 16, passes=1)
    res.update({"note": "stress-ng not installed; used internal RAM test fallback"})
    return res


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(prog="ram_test")
    parser.add_argument("--total-mb", type=int, default=256, help="total MB to test")
    parser.add_argument("--chunk-mb", type=int, default=16, help="chunk MB size")
    parser.add_argument("--passes", type=int, default=1, help="number of passes")
    args = parser.parse_args()
    out = run_ram_test(total_mb=args.total_mb, chunk_mb=args.chunk_mb, passes=args.passes)
    print(json.dumps(out, indent=2))
