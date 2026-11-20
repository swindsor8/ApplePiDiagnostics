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
            assert "avg_cpu_percent" in result or "per_cpu_percent" in result, (
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

    def test_base_block_device_parsing(self):
        from diagnostics.storage.storage_test import _base_block_device
        assert _base_block_device("/dev/mmcblk0p2") == "/dev/mmcblk0"
        assert _base_block_device("/dev/mmcblk0") == "/dev/mmcblk0"
        assert _base_block_device("/dev/nvme0n1p1") == "/dev/nvme0n1"
        assert _base_block_device("/dev/sda1") == "/dev/sda"
        assert _base_block_device("/dev/sdb") == "/dev/sdb"


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
        result = run_usb_speed_test("/tmp")  # nosec B108 — intentional: verifying /tmp is rejected
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

    def test_vcgencmd_fallback_never_powers_off_display(self, monkeypatch):
        import subprocess
        from diagnostics.hdmi import hdmi_test

        called = []

        def fake_which(cmd):
            return "/usr/bin/vcgencmd" if cmd == "vcgencmd" else None

        def fake_check_output(cmd, **kwargs):
            called.append(cmd)
            return "display_power=1\n"

        monkeypatch.setattr(hdmi_test.shutil, "which", fake_which)
        monkeypatch.setattr(hdmi_test, "_detect_via_drm_sysfs", lambda: [])
        monkeypatch.setattr(subprocess, "check_output", fake_check_output)

        result = hdmi_test.run_hdmi_detect()
        assert result["status"] == "OK"
        assert called == [["vcgencmd", "display_power", "-1"]]


# ---------------------------------------------------------------------------
# GPIO
# ---------------------------------------------------------------------------

class TestGPIO:
    def test_returns_valid_result(self):
        from diagnostics.gpio.gpio_test import run_gpio_quick_test
        result = run_gpio_quick_test()
        _assert_valid_result(result, "gpio")


# ---------------------------------------------------------------------------
# Power & Thermal
# ---------------------------------------------------------------------------

class TestPower:
    def test_returns_valid_result(self):
        from diagnostics.power.power_test import run_power_quick_test
        result = run_power_quick_test()
        _assert_valid_result(result, "power")

    def test_decode_throttled_flags(self):
        from diagnostics.power.power_test import decode_throttled_flags
        clean = decode_throttled_flags(0x0)
        assert clean["active_issues"] == []
        assert clean["historical_issues"] == []

        uv_now = decode_throttled_flags(0x50005)
        assert len(uv_now["active_issues"]) == 2
        assert len(uv_now["historical_issues"]) == 2


# ---------------------------------------------------------------------------
# Bootloader & Board Info
# ---------------------------------------------------------------------------

class TestBootloader:
    def test_returns_valid_result(self):
        from diagnostics.bootloader.bootloader_test import run_bootloader_quick_test
        result = run_bootloader_quick_test()
        _assert_valid_result(result, "bootloader")


# ---------------------------------------------------------------------------
# Peripherals (I2C, SPI, BT, Audio, Camera)
# ---------------------------------------------------------------------------

class TestPeripherals:
    def test_returns_valid_result(self):
        from diagnostics.peripherals.peripherals_test import run_peripherals_quick_test
        result = run_peripherals_quick_test()
        _assert_valid_result(result, "peripherals")
        assert "i2c_buses" in result and isinstance(result["i2c_buses"], list)


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

    def test_report_dir_uses_configured_writable_path(self, tmp_path, monkeypatch):
        from main import _get_report_dir

        report_dir = tmp_path / "nested" / "reports"
        monkeypatch.setenv("APD_REPORT_DIR", str(report_dir))

        assert _get_report_dir() == report_dir
        assert report_dir.is_dir()

    def test_app_version_discovery(self, monkeypatch):
        from config import APP_VERSION, get_app_version

        assert isinstance(APP_VERSION, str) and len(APP_VERSION) > 0
        monkeypatch.setenv("APD_VERSION", "v9.9.9-test")
        assert get_app_version() == "v9.9.9-test"


# ---------------------------------------------------------------------------
# Report builder — smoke test (no PDF rendering, just HTML/JSON)
# ---------------------------------------------------------------------------

class TestReportBuilder:
    def test_build_report_smoke(self, tmp_path):
        from diagnostics.report_builder import build_report
        dummy_results = {
            "cpu":         {"status": "OK", "cpu_percent": 5.0},
            "ram":         {"status": "OK", "total_mb": 4096, "errors": []},
            "network":     {"status": "OK", "ping": [], "dns": {"ok": True}},
            "sd":          {"status": "OK", "devices": []},
            "power":       {"status": "OK", "temperature_c": 48.2, "note": "Healthy"},
            "bootloader":  {"status": "UNSUPPORTED", "note": "Non-Pi"},
            "peripherals": {"status": "OK", "i2c_buses": ["i2c-1"], "note": "I2C: 1"},
            "usb":         {"status": "UNSUPPORTED"},
            "hdmi":        {"status": "OK"},
            "gpio":        {"status": "UNSUPPORTED"},
        }
        paths = build_report(dummy_results, str(tmp_path), formats=["html", "json", "pdf"])
        assert "html" in paths and str(paths["html"]).endswith(".html"), "Expected HTML report"
        assert "json" in paths and str(paths["json"]).endswith(".json"), "Expected JSON report"
        assert "pdf" in paths and str(paths["pdf"]).endswith(".pdf"), "Expected PDF report"
        assert "Version:" in paths["html"].read_text(encoding="utf-8")
