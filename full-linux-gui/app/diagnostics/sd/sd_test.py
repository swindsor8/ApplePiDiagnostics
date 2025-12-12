"""Simple SD speed & health test.

This test writes a temporary file in `target_dir` and measures write/read
bandwidth in MB/s. It is conservative by default to avoid filling media.
"""
from __future__ import annotations

import os
import time
import tempfile
from typing import Callable, Dict, Any, Optional


def run_sd_speed_test(target_dir: str = "/tmp", file_size_mb: int = 16, chunk_kb: int = 1024, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """Run a simple sequential write/read speed test.

    Returns a dict with status, write_mb_s, read_mb_s, tested_mb.
    """
    tested_mb = float(file_size_mb)
    fname = None
    try:
        os.makedirs(target_dir, exist_ok=True)
        tf = tempfile.NamedTemporaryFile(delete=False, dir=target_dir)
        fname = tf.name
        tf.close()

        chunk = b"\xAA" * (chunk_kb * 1024)
        chunks = (file_size_mb * 1024) // chunk_kb

        # write
        t0 = time.time()
        with open(fname, "wb") as f:
            for i in range(int(chunks)):
                f.write(chunk)
                if progress_callback:
                    progress_callback({"phase": "write", "written_chunks": i + 1, "total_chunks": int(chunks)})
        t1 = time.time()
        write_mb_s = tested_mb / max(1e-6, (t1 - t0))

        # read
        t0 = time.time()
        with open(fname, "rb") as f:
            total = 0
            while True:
                data = f.read(1024 * chunk_kb)
                if not data:
                    break
                total += len(data)
                if progress_callback:
                    progress_callback({"phase": "read", "read_bytes": total})
        t1 = time.time()
        read_mb_s = tested_mb / max(1e-6, (t1 - t0))

        return {"status": "OK", "tested_mb": tested_mb, "write_mb_s": write_mb_s, "read_mb_s": read_mb_s}
    except Exception as e:
        return {"status": "FAIL", "note": str(e), "tested_mb": tested_mb}
    finally:
        try:
            if fname and os.path.exists(fname):
                os.remove(fname)
        except Exception:
            pass


def run_sd_quick_test(target_dir: str = "/tmp", progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    return run_sd_speed_test(target_dir=target_dir, file_size_mb=4, chunk_kb=1024, progress_callback=progress_callback)


def run_sd_random_test(target_dir: str = "/tmp", file_size_mb: int = 8, io_ops: int = 128, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """Perform small random writes and reads inside a temporary file to measure random IO speed.

    `file_size_mb` is the backing file size; `io_ops` is the number of random operations.
    """
    import random

    tested_mb = float(file_size_mb)
    fname = None
    try:
        os.makedirs(target_dir, exist_ok=True)
        tf = tempfile.NamedTemporaryFile(delete=False, dir=target_dir)
        fname = tf.name
        tf.close()

        # create backing file of given size
        block = b"\x55" * 4096
        blocks = (file_size_mb * 1024 * 1024) // len(block)
        with open(fname, "wb") as f:
            for _ in range(int(blocks)):
                f.write(block)

        # random IO
        t0 = time.time()
        with open(fname, "r+b") as f:
            for i in range(int(io_ops)):
                off_block = random.randrange(0, max(1, int(blocks)))
                f.seek(off_block * len(block))
                f.write(os.urandom(len(block)))
                f.flush()
                os.fsync(f.fileno())
                if progress_callback:
                    progress_callback({"phase": "random", "op": i + 1, "total_ops": io_ops})
        t1 = time.time()
        rand_iops = io_ops / max(1e-6, (t1 - t0))

        return {"status": "OK", "tested_mb": tested_mb, "random_iops": rand_iops}
    except Exception as e:
        return {"status": "FAIL", "note": str(e), "tested_mb": tested_mb}
    finally:
        try:
            if fname and os.path.exists(fname):
                os.remove(fname)
        except Exception:
            pass


def run_sd_full_test(target_dir: str = "/tmp", seq_mb: int = 16, rand_mb: int = 8) -> Dict[str, Any]:
    seq = run_sd_speed_test(target_dir=target_dir, file_size_mb=seq_mb)
    rand = run_sd_random_test(target_dir=target_dir, file_size_mb=rand_mb)
    return {"sequential": seq, "random": rand}


if __name__ == "__main__":
    import argparse
    import json

    p = argparse.ArgumentParser()
    p.add_argument("--target-dir", default="/tmp")
    p.add_argument("--size-mb", type=int, default=4)
    args = p.parse_args()
    res = run_sd_speed_test(target_dir=args.target_dir, file_size_mb=args.size_mb)
    print(json.dumps(res))
