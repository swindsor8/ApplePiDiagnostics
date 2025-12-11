#!/usr/bin/env python3
"""CPU diagnostic: light stress + measurement utility.

This module exposes `run_cpu_test()` which will spawn worker processes
that burn CPU for a short duration while sampling system CPU usage and
(when available) CPU temperature sensors. The function returns a dict
containing measured metrics which can later be used to determine pass/fail.

Defaults are conservative (10s duration). Callers (GUI) can increase the
duration when running full diagnostics.
"""
from __future__ import annotations

import time
import multiprocessing as mp
from typing import Optional, Dict, Any

import psutil


def _cpu_worker(stop_ts: float) -> None:
    """Busy work loop that runs until stop_ts."""
    x = 0
    # simple integer operations to keep CPU busy
    while time.time() < stop_ts:
        x = (x + 1) * 3 % 1000003


def run_cpu_test(duration: int = 10, workers: Optional[int] = None, sample_interval: float = 1.0, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """Run a CPU stress/measurement test.

    Args:
        duration: seconds to run the stress workers (default 10).
        workers: number of worker processes to spawn. Defaults to logical CPU count.
        sample_interval: seconds between CPU usage samples.

    Returns:
        A dict with keys: `status`, `duration`, `workers`, `avg_cpu_percent`,
        `per_cpu_percent` (list), `samples` (list of per-interval averages),
        `max_temperature` (if available), and `notes`/`errors`.
    """
    if workers is None:
        workers = psutil.cpu_count(logical=True) or 1

    stop_ts = time.time() + max(1, int(duration))

    processes = []
    for _ in range(workers):
        p = mp.Process(target=_cpu_worker, args=(stop_ts,))
        p.daemon = True
        p.start()
        processes.append(p)

    samples = []
    start = time.time()
    # Use psutil.cpu_percent with interval to sample system usage
    try:
        while time.time() < stop_ts:
            percents = psutil.cpu_percent(interval=sample_interval, percpu=True)
            # average across all CPUs for this interval
            avg = sum(percents) / len(percents) if percents else 0.0
            sample = {"percpu": percents, "avg": avg, "ts": time.time()}
            samples.append(sample)
            # invoke progress callback if provided
            try:
                if progress_callback:
                    progress_callback(sample)
            except Exception:
                # swallow callback errors — we still want to finish the test
                pass
    except Exception as e:
        # sampling failure — record and continue to shutdown workers
        samples.append({"error": str(e), "ts": time.time()})

    # ensure workers are terminated
    for p in processes:
        try:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)
        except Exception:
            pass

    # aggregate results
    per_cpu_samples = []
    avg_samples = []
    for s in samples:
        if "percpu" in s:
            per_cpu_samples.append(s["percpu"])
            avg_samples.append(s["avg"])

    # compute per-core averages across sample intervals
    per_core_avg = []
    if per_cpu_samples:
        num_cores = len(per_cpu_samples[0])
        for core_idx in range(num_cores):
            vals = [sample[core_idx] for sample in per_cpu_samples]
            per_core_avg.append(sum(vals) / len(vals))

    overall_avg = sum(avg_samples) / len(avg_samples) if avg_samples else 0.0

    # try to get max temperature if available
    max_temp = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            # flatten values and look for 'cpu' or similar entries
            found = []
            for k, vals in temps.items():
                for entry in vals:
                    if getattr(entry, "current", None) is not None:
                        found.append(entry.current)
            if found:
                max_temp = max(found)
    except Exception:
        max_temp = None

    result = {
        "status": "OK",
        "duration": duration,
        "workers": workers,
        "avg_cpu_percent": overall_avg,
        "per_cpu_percent": per_core_avg,
        "samples_count": len(avg_samples),
        "max_temperature": max_temp,
        "samples": samples,
    }

    return result


if __name__ == "__main__":
    # simple CLI runner for manual testing
    import json
    import argparse

    parser = argparse.ArgumentParser(prog="cpu_test")
    parser.add_argument("--duration", type=int, default=10, help="duration seconds to run stress")
    parser.add_argument("--workers", type=int, default=None, help="number of worker processes")
    args = parser.parse_args()
    out = run_cpu_test(duration=args.duration, workers=args.workers)
    print(json.dumps(out, indent=2))
