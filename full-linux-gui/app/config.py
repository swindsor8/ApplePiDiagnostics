"""Central configuration constants for Apple Pi Diagnostics.

All hardcoded network addresses, ports, and timeouts live here so they can be
changed in one place and are easy to find during security audits.
"""
from __future__ import annotations

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
