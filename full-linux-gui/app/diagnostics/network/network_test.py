"""Basic network connectivity diagnostics."""
from __future__ import annotations

import re
import socket
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional

# Import constants — fall back gracefully if run standalone outside the app tree
try:
    from config import GATEWAY_PROBE_HOST, GATEWAY_PROBE_PORT, NETWORK_PING_TARGETS, NETWORK_DNS_CHECK_HOST
except ImportError:
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parents[2]))
    from config import GATEWAY_PROBE_HOST, GATEWAY_PROBE_PORT, NETWORK_PING_TARGETS, NETWORK_DNS_CHECK_HOST


def _safe_err(e: Exception) -> str:
    """Return a sanitized error string that strips file paths to avoid info disclosure."""
    return re.sub(r'/\S+', '[path]', str(e))


def _ping_host(host: str, count: int = 2, timeout: int = 2) -> Dict[str, Any]:
    try:
        # use system ping; more portable than raw sockets here
        res = subprocess.run(["ping", "-c", str(count), "-W", str(timeout), host], capture_output=True, text=True)
        ok = res.returncode == 0
        return {"host": host, "ok": ok, "rc": res.returncode, "stdout_first": (res.stdout.splitlines()[0] if res.stdout else "")}
    except FileNotFoundError:
        return {"host": host, "ok": False, "note": "ping not available"}
    except Exception as e:
        return {"host": host, "ok": False, "note": _safe_err(e)}


def run_network_test(targets: Optional[List[str]] = None, dns_check: str = NETWORK_DNS_CHECK_HOST) -> Dict[str, Any]:
    """Run basic network connectivity checks.

    Privacy note: By default this function sends ICMP ping packets to
    8.8.8.8 (Google DNS) and 1.1.1.1 (Cloudflare DNS), and performs a DNS
    lookup for www.google.com.  These requests are visible to those third
    parties and reveal that this device is running connectivity tests.
    Pass custom ``targets`` and ``dns_check`` values to use local
    infrastructure instead.
    """
    if targets is None:
        targets = NETWORK_PING_TARGETS

    out = {"status": "OK", "ping": [], "dns": {}}

    for h in targets:
        out["ping"].append(_ping_host(h))

    # DNS resolution
    try:
        t0 = time.time()
        ip = socket.gethostbyname(dns_check)
        out["dns"] = {"host": dns_check, "ip": ip, "ok": True, "latency_s": time.time() - t0}
    except Exception as e:
        out["dns"] = {"host": dns_check, "ok": False, "note": _safe_err(e)}

    # check interfaces
    try:
        import psutil as _ps
        if_stats = _ps.net_if_stats()
        if_addrs = _ps.net_if_addrs()
        interfaces = []
        for name, st in if_stats.items():
            if name == "lo":
                continue
            up = bool(st.isup)
            addrs = [a.address for a in if_addrs.get(name, []) if getattr(a, 'address', None)]
            interfaces.append({"name": name, "up": up, "addrs": addrs})
        out["interfaces"] = interfaces
    except Exception:
        out["interfaces"] = []

    # attempt to detect default route by opening a UDP socket to a public IP
    gw_ok = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((GATEWAY_PROBE_HOST, GATEWAY_PROBE_PORT))
        local_ip = s.getsockname()[0]
        out["local_ip"] = local_ip
        gw_ok = True
        s.close()
    except Exception:
        out["local_ip"] = None

    any_ok = any(p.get("ok") for p in out["ping"]) or out["dns"].get("ok") or gw_ok
    out["status"] = "OK" if any_ok else "FAIL"
    return out


def run_network_quick_test() -> Dict[str, Any]:
    return run_network_test()


if __name__ == "__main__":
    import json
    print(json.dumps(run_network_quick_test()))
