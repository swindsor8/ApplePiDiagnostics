#!/usr/bin/env python3
"""CPU diagnostic: light stress + measurement utility.

This module exposes `run_cpu_test()` which will spawn worker processes
that burn CPU for a short duration while sampling system CPU usage and
(when available) CPU temperature sensors. The function returns a dict
containing measured metrics which can later be used to determine pass/fail.

The implementation supports an optional `stop_event` (multiprocessing.Event)
which allows callers (GUI) to request early cancellation.

def _cpu_worker(stop_ts: float, stop_event: Optional[mp.synchronize.Event] = None) -> None:
    """Busy loop that runs until stop_ts or stop_event is set."""
    x = 0
    while time.time() < stop_ts and (stop_event is None or not stop_event.is_set()):
        x = (x + 1) * 3 % 1000003


def run_cpu_test(
    duration: int = 10,
    workers: Optional[int] = None,
    sample_interval: float = 1.0,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    stop_event: Optional[mp.Event] = None,
) -> Dict[str, Any]:
    """Run a CPU stress/measurement test.

    Args:
        duration: seconds to run the stress workers.
        workers: number of worker processes to spawn. Defaults to logical CPU count.
        sample_interval: seconds between CPU usage samples.
        progress_callback: optional callable(sample_dict) called on each sample.
        stop_event: optional multiprocessing.Event to request early cancellation.

    Returns:
        A dict with aggregated metrics and raw samples.
    """
    #!/usr/bin/env python3
    """CPU diagnostic: light stress + measurement utility.

    This module exposes `run_cpu_test()` which will spawn worker processes
    that burn CPU for a short duration while sampling system CPU usage and
    (when available) CPU temperature sensors. The function returns a dict
    containing measured metrics which can later be used to determine pass/fail.

    The implementation supports an optional `stop_event` (multiprocessing.Event)
    which allows callers (GUI) to request early cancellation.
    """
    from __future__ import annotations

    import time
    import multiprocessing as mp
    from typing import Optional, Dict, Any, Callable

    import psutil


    def _cpu_worker(stop_ts: float, stop_event: Optional[mp.synchronize.Event] = None) -> None:
        """Busy loop that runs until stop_ts or stop_event is set."""
        x = 0
        while time.time() < stop_ts and (stop_event is None or not stop_event.is_set()):
            x = (x + 1) * 3 % 1000003


    def run_cpu_test(
        duration: int = 10,
        workers: Optional[int] = None,
        sample_interval: float = 1.0,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        stop_event: Optional[mp.Event] = None,
    ) -> Dict[str, Any]:
        """Run a CPU stress/measurement test.

        Args:
            duration: seconds to run the stress workers.
            workers: number of worker processes to spawn. Defaults to logical CPU count.
            sample_interval: seconds between CPU usage samples.
            progress_callback: optional callable(sample_dict) called on each sample.
            stop_event: optional multiprocessing.Event to request early cancellation.

        Returns:
            A dict with aggregated metrics and raw samples.
        """
        if workers is None:
            workers = psutil.cpu_count(logical=True) or 1

        stop_ts = time.time() + max(1, int(duration))

        # use a multiprocessing.Event for signaling children
        if stop_event is None:
            stop_event_mp = mp.Event()
        else:
            stop_event_mp = stop_event

        processes = []
        for _ in range(workers):
            p = mp.Process(target=_cpu_worker, args=(stop_ts, stop_event_mp))
            p.daemon = True
            p.start()
            processes.append(p)

        samples = []
        try:
            while time.time() < stop_ts and (stop_event is None or not stop_event.is_set()):
                percents = psutil.cpu_percent(interval=sample_interval, percpu=True)
                avg = sum(percents) / len(percents) if percents else 0.0
                sample = {"percpu": percents, "avg": avg, "ts": time.time()}
                samples.append(sample)
                if progress_callback:
                    try:
                        progress_callback(sample)
                    except Exception:
                        pass
        except Exception as e:
            samples.append({"error": str(e), "ts": time.time()})

        # signal children to stop and join/terminate
        try:
            stop_event_mp.set()
        except Exception:
            pass

        for p in processes:
            try:
                if p.is_alive():
                    p.join(timeout=1)
                    if p.is_alive():
                        p.terminate()
                        p.join(timeout=1)
            except Exception:
                pass

        # aggregate
        per_cpu_samples = [s["percpu"] for s in samples if "percpu" in s]
        avg_samples = [s["avg"] for s in samples if "avg" in s]

        per_core_avg = []
        if per_cpu_samples:
            num_cores = len(per_cpu_samples[0])
            for core_idx in range(num_cores):
                vals = [sample[core_idx] for sample in per_cpu_samples]
                per_core_avg.append(sum(vals) / len(vals))

        overall_avg = sum(avg_samples) / len(avg_samples) if avg_samples else 0.0

        max_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                found = []
                for vals in temps.values():
                    for entry in vals:
                        if getattr(entry, "current", None) is not None:
                            found.append(entry.current)
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


    def run_cpu_quick_test(duration: int = 5, workers: Optional[int] = None, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None, stop_event: Optional[mp.Event] = None) -> Dict[str, Any]:
        return run_cpu_test(duration=duration, workers=workers, sample_interval=1.0, progress_callback=progress_callback, stop_event=stop_event)


    def run_cpu_stress_ng(duration: int = 60, workers: Optional[int] = None) -> Dict[str, Any]:
        """Run stress-ng if available; otherwise fall back to internal test."""
        import shutil
        import subprocess

        cpu_count = psutil.cpu_count(logical=True) or 1
        if workers is None or workers <= 0:
            workers = cpu_count

        if shutil.which("stress-ng"):
            cmd = ["stress-ng", "--cpu", str(workers), "--timeout", f"{int(duration)}s", "--metrics-brief"]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True)
                status = "OK" if proc.returncode == 0 else "FAIL"
                return {"status": status, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
            except Exception as e:
                return {"status": "ERROR", "error": str(e)}

        res = run_cpu_test(duration=duration, workers=workers)
        res.update({"note": "stress-ng not installed; used internal stress fallback"})
        return res


    if __name__ == "__main__":
        import json
        import argparse

        parser = argparse.ArgumentParser(prog="cpu_test")
        parser.add_argument("--duration", type=int, default=10)
        parser.add_argument("--workers", type=int, default=None)
        args = parser.parse_args()
        out = run_cpu_test(duration=args.duration, workers=args.workers)
        print(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))

