"""Central configuration constants and version discovery for Apple Pi Diagnostics.

All hardcoded network addresses, ports, and timeouts live here so they can be
changed in one place and are easy to find during security audits.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

# ---------------------------------------------------------------------------
# Application version
# ---------------------------------------------------------------------------
def get_app_version() -> str:
    """Resolve the application version string.

    Lookup order:
      1. ``APD_VERSION`` environment variable
      2. ``VERSION`` file in this directory or any parent up to the repo root
      3. ``git describe --tags --always`` (dev checkout fallback)
      4. ``"dev"``
    """
    env_ver = os.environ.get("APD_VERSION", "").strip()
    if env_ver:
        return env_ver

    here = Path(__file__).resolve()
    for parent in here.parents:
        version_file = parent / "VERSION"
        if version_file.is_file():
            try:
                text = version_file.read_text(encoding="utf-8").strip()
                if text:
                    return text
            except OSError:
                pass

    try:
        out = subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            cwd=str(here.parent),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        if out:
            return out
    except Exception:
        pass

    return "dev"


APP_VERSION: str = get_app_version()

# ---------------------------------------------------------------------------
# Network — connectivity probe targets
# ---------------------------------------------------------------------------
# Used to detect whether the device has a working default route / internet.
# These addresses are contacted at runtime; change to local infrastructure
# if external connectivity is not desired.
GATEWAY_PROBE_HOST: str = "8.8.8.8"
GATEWAY_PROBE_PORT: int = 53

# Targets used by the network diagnostic ping test
NETWORK_PING_TARGETS: list[str] = ["8.8.8.8", "1.1.1.1"]

# Hostname used for DNS resolution latency check
NETWORK_DNS_CHECK_HOST: str = "www.google.com"

# ---------------------------------------------------------------------------
# QR / HTTP report server
# ---------------------------------------------------------------------------
# Port the local HTTP server binds to when serving reports via QR code.
QR_HTTP_PORT: int = 8888
