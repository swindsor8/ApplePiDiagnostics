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


def run_ram_test(total_mb: int = 256, chunk_mb: int = 16, passes: int = 1, progress_callback: Optional[callable] = None, stop_event: Optional[object] = None) -> Dict[str, Any]:
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
            while bytes_written < target_bytes and (stop_event is None or not getattr(stop_event, 'is_set', lambda: False)()):
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

            # allow early cancellation between passes
            if stop_event is not None and getattr(stop_event, 'is_set', lambda: False)():
                break

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


def run_ram_quick_test(total_mb: int = 64, chunk_mb: int = 16, passes: int = 1, progress_callback: Optional[callable] = None, stop_event: Optional[object] = None) -> Dict[str, Any]:
    """Quick RAM test wrapper with smaller defaults."""
    return run_ram_test(total_mb=total_mb, chunk_mb=chunk_mb, passes=passes, progress_callback=progress_callback, stop_event=stop_event)


def run_ram_stress_ng(total_mb: int = 512, workers: int = 1, duration: int = 60) -> Dict[str, Any]:
    """Stress function removed: return UNSUPPORTED response.

    For portability we no longer depend on `stress-ng`. Use `run_ram_quick_test`
    or `run_ram_test` for internal RAM verification.
    """
    return {
        "status": "UNSUPPORTED",
        "note": "stress-ng based RAM stress test removed; use run_ram_quick_test or run_ram_test instead",
    }


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
