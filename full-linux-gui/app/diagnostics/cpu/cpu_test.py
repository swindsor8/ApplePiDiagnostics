#!/usr/bin/env python3
"""CPU diagnostic: light stress + measurement utility.

This module provides a small, self-contained implementation used by the
GUI. It spawns worker processes that burn CPU for a short duration while
sampling system CPU usage and (when available) CPU temperature sensors.

The functions support an optional `stop_event` (a multiprocessing.Event)
for cooperative cancellation by the caller (GUI).
"""
from __future__ import annotations

import time
import multiprocessing as mp
from multiprocessing import Event as MPEvent
from typing import Optional, Dict, Any, Callable

import psutil


def _cpu_worker(stop_ts: float, stop_event: Optional[Any] = None) -> None:
    """Busy loop that runs until stop_ts or stop_event is set."""
    x = 0
    while time.time() < stop_ts and (stop_event is None or not stop_event.is_set()):
        # simple integer work that's cheap to run but keeps CPU busy
        x = (x + 1) * 3 % 1000003


def run_cpu_test(
    duration: int = 10,
    workers: Optional[int] = None,
    sample_interval: float = 1.0,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    stop_event: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run a CPU load test and sample CPU usage.

    Returns a dict with summary metrics and raw samples.
    """
    if workers is None:
        workers = psutil.cpu_count(logical=True) or 1

    stop_ts = time.time() + max(1, int(duration))
    stop_event_mp = stop_event if stop_event is not None else mp.Event()

    procs = []
    for _ in range(workers):
        p = mp.Process(target=_cpu_worker, args=(stop_ts, stop_event_mp))
        p.daemon = True
        p.start()
        procs.append(p)

    samples: list[Dict[str, Any]] = []
    try:
        while time.time() < stop_ts and (stop_event is None or not stop_event.is_set()):
            perc = psutil.cpu_percent(interval=sample_interval, percpu=True)
            avg = sum(perc) / len(perc) if perc else 0.0
            # sample current temperatures (if available) and include in sample
            temp_sample: dict[str, list[float]] = {}
            temp_max_sample: Optional[float] = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    found: list[float] = []
                    for name, entries in temps.items():
                        vals: list[float] = []
                        for e in entries:
                            cur = getattr(e, "current", None)
                            if cur is not None:
                                vals.append(float(cur))
                                found.append(float(cur))
                        if vals:
                            temp_sample[name] = vals
                    if found:
                        temp_max_sample = max(found)
            except Exception:
                temp_sample = {}
                temp_max_sample = None

            s = {"percpu": perc, "avg": avg, "ts": time.time(), "temps": temp_sample, "max_temp": temp_max_sample}
            samples.append(s)
            if progress_callback:
                try:
                    progress_callback(s)
                except Exception:
                    # progress callback should never break the test
                    pass
    except Exception as e:  # pragma: no cover - defensive
        samples.append({"error": str(e), "ts": time.time()})

    # request workers stop if we created a local event
    try:
        stop_event_mp.set()
    except Exception:
        pass

    # join/terminate workers cleanly
    for p in procs:
        try:
            if p.is_alive():
                p.join(timeout=1)
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=1)
        except Exception:
            pass

    per_cpu = [x["percpu"] for x in samples if "percpu" in x]
    avg_samples = [x["avg"] for x in samples if "avg" in x]

    per_core_avg: list[float] = []
    if per_cpu:
        cores = len(per_cpu[0])
        for i in range(cores):
            vals = [s[i] for s in per_cpu]
            per_core_avg.append(sum(vals) / len(vals))

    overall_avg = sum(avg_samples) / len(avg_samples) if avg_samples else 0.0

    max_temp: Optional[float] = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            found: list[float] = []
            for vals in temps.values():
                for e in vals:
                    if getattr(e, "current", None) is not None:
                        found.append(e.current)
            if found:
                max_temp = max(found)
    except Exception:
        max_temp = None

    return {
        "status": "OK",
        "duration": duration,
        "workers": workers,
        "avg_cpu_percent": overall_avg,
        "per_cpu_percent": per_core_avg,
        "samples_count": len(avg_samples),
        "max_temperature": max_temp,
        "samples": samples,
    }


def run_cpu_quick_test(
    duration: int = 5,
    workers: Optional[int] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    stop_event: Optional[Any] = None,
) -> Dict[str, Any]:
    """Convenience quick test (short duration)."""
    return run_cpu_test(duration=duration, workers=workers, sample_interval=1.0, progress_callback=progress_callback, stop_event=stop_event)


def run_cpu_stress_ng(duration: int = 60, workers: Optional[int] = None) -> Dict[str, Any]:
    """Stress function removed: return UNSUPPORTED result.

    The GUI previously called this to invoke `stress-ng`. To avoid
    platform-specific dependencies we remove the external stress path and
    return an explicit unsupported response. Use `run_cpu_quick_test` or
    `run_cpu_test` for internal testing instead.
    """
    return {
        "status": "UNSUPPORTED",
        "note": "stress-ng based CPU stress test removed; use run_cpu_quick_test or run_cpu_test instead",
    }


if __name__ == "__main__":
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser()
    p.add_argument("--duration", type=int, default=10)
    p.add_argument("--workers", type=int, default=None)
    args = p.parse_args()
    sys.stdout.write(json.dumps(run_cpu_test(duration=args.duration, workers=args.workers), indent=2))
