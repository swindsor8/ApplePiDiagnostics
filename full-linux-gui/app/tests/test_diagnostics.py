"""Pytest test suite for Apple Pi Diagnostics — diagnostic modules.

These tests run without real Raspberry Pi hardware. They verify that every
diagnostic module:
  - Returns a dict
  - Contains a "status" key
  - Sets status to one of the accepted values
  - Does not raise an unhandled exception

Tests that require external resources (network, USB, GPIO) gracefully accept
UNSUPPORTED or FAIL as well as OK/WARNING, so CI passes on a plain Linux runner.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the app root is on sys.path regardless of how pytest is invoked
APP_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(APP_ROOT))

import pytest

VALID_STATUSES = {"OK", "WARNING", "FAIL", "UNSUPPORTED"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_valid_result(result: dict, module_name: str) -> None:
    assert isinstance(result, dict), f"{module_name}: result must be a dict, got {type(result)}"
    assert "status" in result, f"{module_name}: result missing 'status' key. Got: {result}"
    assert result["status"] in VALID_STATUSES, (
        f"{module_name}: status '{result['status']}' not in {VALID_STATUSES}"
    )


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

class TestCPU:
    def test_returns_valid_result(self):
        from diagnostics.cpu.cpu_test import run_cpu_quick_test
        result = run_cpu_quick_test()
        _assert_valid_result(result, "cpu")

    def test_contains_expected_keys(self):
        from diagnostics.cpu.cpu_test import run_cpu_quick_test
        result = run_cpu_quick_test()
        if result["status"] == "OK":
            assert "cpu_percent" in result or "model" in result, (
                f"CPU OK result missing expected keys: {result}"
            )


# ---------------------------------------------------------------------------
# RAM
# ---------------------------------------------------------------------------

class TestRAM:
    def test_returns_valid_result(self):
        from diagnostics.ram.ram_test import run_ram_quick_test
        result = run_ram_quick_test()
        _assert_valid_result(result, "ram")

    def test_total_mb_is_positive(self):
        from diagnostics.ram.ram_test import run_ram_quick_test
        result = run_ram_quick_test()
        if "total_mb" in result:
            assert result["total_mb"] > 0, "total_mb should be positive"

    def test_errors_is_list(self):
        from diagnostics.ram.ram_test import run_ram_quick_test
        result = run_ram_quick_test()
        if "errors" in result:
            assert isinstance(result["errors"], list), "errors must be a list"


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

class TestNetwork:
    def test_returns_valid_result(self):
        from diagnostics.network.network_test import run_network_quick_test
        result = run_network_quick_test()
        _assert_valid_result(result, "network")

    def test_ping_is_list(self):
        from diagnostics.network.network_test import run_network_quick_test
        result = run_network_quick_test()
        assert "ping" in result
        assert isinstance(result["ping"], list)

    def test_ping_entries_have_ok_field(self):
        from diagnostics.network.network_test import run_network_quick_test
        result = run_network_quick_test()
        for entry in result.get("ping", []):
            assert "ok" in entry, f"Ping entry missing 'ok': {entry}"
            assert isinstance(entry["ok"], bool)

    def test_custom_targets(self):
        """Passing custom targets should not raise and should return valid result."""
        from diagnostics.network.network_test import run_network_test
        result = run_network_test(targets=["127.0.0.1"], dns_check="localhost")
        _assert_valid_result(result, "network (custom targets)")


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class TestStorage:
    def test_returns_valid_result(self):
        from diagnostics.storage.storage_test import run_storage_quick_test
        result = run_storage_quick_test()
        _assert_valid_result(result, "storage")

    def test_contains_device_list(self):
        from diagnostics.storage.storage_test import run_storage_quick_test
        result = run_storage_quick_test()
        assert "devices" in result, f"Storage result missing 'devices': {result}"
        assert isinstance(result["devices"], list)


# ---------------------------------------------------------------------------
# USB
# ---------------------------------------------------------------------------

class TestUSB:
    def test_returns_valid_result(self):
        from diagnostics.usb.usb_test import run_usb_quick_test
        result = run_usb_quick_test()
        _assert_valid_result(result, "usb")

    def test_speed_test_rejects_bad_path(self):
        """run_usb_speed_test must reject paths outside trusted prefixes."""
        from diagnostics.usb.usb_test import run_usb_speed_test
        result = run_usb_speed_test("/tmp")
        assert result["status"] == "FAIL"
        assert "trusted prefix" in result.get("note", "")

    def test_speed_test_rejects_nonexistent(self):
        from diagnostics.usb.usb_test import run_usb_speed_test
        result = run_usb_speed_test("/nonexistent/path")
        assert result["status"] == "FAIL"


# ---------------------------------------------------------------------------
# HDMI
# ---------------------------------------------------------------------------

class TestHDMI:
    def test_returns_valid_result(self):
        from diagnostics.hdmi.hdmi_test import run_hdmi_quick_test
        result = run_hdmi_quick_test()
        _assert_valid_result(result, "hdmi")


# ---------------------------------------------------------------------------
# GPIO
# ---------------------------------------------------------------------------

class TestGPIO:
    def test_returns_valid_result(self):
        from diagnostics.gpio.gpio_test import run_gpio_quick_test
        result = run_gpio_quick_test()
        _assert_valid_result(result, "gpio")


# ---------------------------------------------------------------------------
# Config module
# ---------------------------------------------------------------------------

class TestConfig:
    def test_constants_are_set(self):
        from config import (
            GATEWAY_PROBE_HOST, GATEWAY_PROBE_PORT,
            NETWORK_PING_TARGETS, NETWORK_DNS_CHECK_HOST,
            QR_HTTP_PORT,
        )
        assert isinstance(GATEWAY_PROBE_HOST, str) and GATEWAY_PROBE_HOST
        assert isinstance(GATEWAY_PROBE_PORT, int) and GATEWAY_PROBE_PORT > 0
        assert isinstance(NETWORK_PING_TARGETS, list) and len(NETWORK_PING_TARGETS) > 0
        assert isinstance(NETWORK_DNS_CHECK_HOST, str) and NETWORK_DNS_CHECK_HOST
        assert isinstance(QR_HTTP_PORT, int) and 1024 <= QR_HTTP_PORT <= 65535


# ---------------------------------------------------------------------------
# Report builder — smoke test (no PDF rendering, just HTML/JSON)
# ---------------------------------------------------------------------------

class TestReportBuilder:
    def test_build_report_smoke(self, tmp_path):
        from diagnostics.report_builder import build_report
        dummy_results = {
            "cpu":     {"status": "OK", "cpu_percent": 5.0},
            "ram":     {"status": "OK", "total_mb": 4096, "errors": []},
            "network": {"status": "OK", "ping": [], "dns": {"ok": True}},
            "storage": {"status": "OK", "devices": []},
            "usb":     {"status": "UNSUPPORTED"},
            "hdmi":    {"status": "OK"},
            "gpio":    {"status": "UNSUPPORTED"},
        }
        # Should not raise; returns list of created file paths
        paths = build_report(dummy_results, str(tmp_path), formats=["html", "json"])
        assert any(str(p).endswith(".html") for p in paths), "Expected HTML report"
        assert any(str(p).endswith(".json") for p in paths), "Expected JSON report"
