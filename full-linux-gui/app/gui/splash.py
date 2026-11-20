#!/usr/bin/env python3
"""Modern splash screen with live pre-boot checks for Apple Pi Diagnostics."""
from __future__ import annotations

import socket
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore

try:
    from config import APP_VERSION
except Exception:
    APP_VERSION = "dev"


def _find_logo_filename(name_without_ext="apple_pi_logo"):
    """Search parent folders for an `assets/` dir that contains the logo."""
    exts = ("png", "ppm", "jpg", "jpeg")
    here = Path(__file__).resolve()
    for p in here.parents:
        assets_dir = p / "assets"
        if assets_dir.is_dir():
            for ext in exts:
                candidate = assets_dir / f"{name_without_ext}.{ext}"
                if candidate.exists():
                    return candidate
    return None


LOGO_PATH = _find_logo_filename()

# ---------------------------------------------------------------------------
# Pre-boot checks
# ---------------------------------------------------------------------------

def _check_system_info():
    """Read Pi model and hostname."""
    try:
        hostname = socket.gethostname()
        pi_model = None
        model_path = Path("/proc/device-tree/model")
        if model_path.exists():
            pi_model = model_path.read_text(errors="ignore").strip("\x00\n")
        if pi_model:
            short = pi_model.replace("Raspberry Pi ", "Pi ").split("\x00")[0]
            return True, f"{short} · {hostname}"
        return True, f"Linux · {hostname}"
    except Exception as e:
        return False, f"Could not read system info: {e}"


def _check_storage():
    """Check if a primary storage device is accessible."""
    candidates = ["/dev/mmcblk0", "/dev/nvme0n1", "/dev/sda"]
    for dev in candidates:
        if Path(dev).exists():
            label = "SD card" if "mmcblk" in dev else "NVMe" if "nvme" in dev else "USB/SATA disk"
            return True, f"{label} detected ({dev})"
    return False, "No storage device detected"


def _check_network():
    """Check for any non-loopback network interface that is UP."""
    try:
        import psutil
        stats = psutil.net_if_stats()
        for name, s in stats.items():
            if name == "lo":
                continue
            if s.isup:
                addrs = psutil.net_if_addrs().get(name, [])
                ip = next((a.address for a in addrs if a.family == socket.AF_INET), None)
                detail = f"{name} UP" + (f" · {ip}" if ip else "")
                return True, detail
        return False, "No active network interfaces"
    except Exception:
        sys_net = Path("/sys/class/net")
        if sys_net.exists():
            for iface in sys_net.iterdir():
                if iface.name == "lo":
                    continue
                operstate = iface / "operstate"
                if operstate.exists() and operstate.read_text().strip() == "up":
                    return True, f"{iface.name} UP"
        return False, "No active network interfaces"


def _check_diagnostics():
    """Verify all diagnostic modules can be imported."""
    modules = [
        ("diagnostics.cpu.cpu_test", "run_cpu_quick_test"),
        ("diagnostics.ram.ram_test", "run_ram_quick_test"),
        ("diagnostics.network.network_test", "run_network_quick_test"),
        ("diagnostics.storage.storage_test", "run_storage_quick_test"),
        ("diagnostics.usb.usb_test", "run_usb_quick_test"),
        ("diagnostics.hdmi.hdmi_test", "run_hdmi_quick_test"),
        ("diagnostics.gpio.gpio_test", "run_gpio_quick_test"),
        ("diagnostics.power.power_test", "run_power_quick_test"),
        ("diagnostics.bootloader.bootloader_test", "run_bootloader_quick_test"),
        ("diagnostics.peripherals.peripherals_test", "run_peripherals_quick_test"),
    ]
    for mod, attr in modules:
        try:
            m = __import__(mod, fromlist=[attr])
            if not hasattr(m, attr):
                return False, f"{mod} missing {attr}"
        except Exception:
            return False, f"Import failed: {mod.split('.')[-2]}"
    return True, f"All {len(modules)} modules loaded"


_CHECKS = [
    ("System Info", _check_system_info),
    ("Storage Media", _check_storage),
    ("Network", _check_network),
    ("Diagnostics Ready", _check_diagnostics),
]

# ---------------------------------------------------------------------------
# Splash screen (opaque sleek card — renders cleanly even without X11 compositor)
# ---------------------------------------------------------------------------

class SplashScreen(QtWidgets.QDialog):
    def __init__(self, parent=None, duration_ms=1800):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self._results = []
        self._check_labels = []
        self._check_index = 0
        self._checks_done = False
        self._close_pending = False

        self.setWindowFlags(
            QtCore.Qt.Dialog
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setStyleSheet("""
            QDialog {
                background-color: #11161f;
                border: 1px solid #293241;
                border-radius: 14px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(10)

        # Logo
        logo_label = QtWidgets.QLabel()
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        if LOGO_PATH and LOGO_PATH.exists():
            pix = QtGui.QPixmap(str(LOGO_PATH)).scaled(
                96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("APD")
            logo_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #0a84ff;")
        layout.addWidget(logo_label, alignment=QtCore.Qt.AlignCenter)

        # Title + version pill
        title = QtWidgets.QLabel("Apple Pi Diagnostics")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #f0f6fc;")
        layout.addWidget(title)

        ver_lbl = QtWidgets.QLabel(f"Hardware Diagnostic Suite  ·  {APP_VERSION}")
        ver_lbl.setAlignment(QtCore.Qt.AlignCenter)
        ver_lbl.setStyleSheet("font-size: 12px; color: #9da7b3;")
        layout.addWidget(ver_lbl)

        # Progress bar
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, len(_CHECKS))
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet("""
            QProgressBar { background-color: #242c38; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #0a84ff; border-radius: 3px; }
        """)
        layout.addWidget(self._progress)

        # Checks container
        checks_box = QtWidgets.QFrame()
        checks_box.setStyleSheet(
            "QFrame { background-color: #161b22; border: 1px solid #293241; border-radius: 10px; }"
        )
        checks_layout = QtWidgets.QVBoxLayout(checks_box)
        checks_layout.setContentsMargins(14, 10, 14, 10)
        checks_layout.setSpacing(6)

        for name, _ in _CHECKS:
            lbl = QtWidgets.QLabel(f"○  Checking {name}…")
            lbl.setStyleSheet("font-size: 12px; color: #6e7681; background: transparent;")
            checks_layout.addWidget(lbl)
            self._check_labels.append(lbl)

        layout.addWidget(checks_box)

        screen = QtWidgets.QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = min(480, max(360, geo.width() - 80))
            h = min(380, max(320, geo.height() - 80))
            self.setFixedSize(w, h)
            self.move(geo.x() + (geo.width() - w) // 2, geo.y() + (geo.height() - h) // 2)
        else:
            self.setFixedSize(460, 360)

    def _run_next_check(self):
        idx = self._check_index
        if idx >= len(_CHECKS):
            self._checks_done = True
            if self._close_pending:
                self.accept()
            return

        name, fn = _CHECKS[idx]
        lbl = self._check_labels[idx]
        lbl.setStyleSheet("font-size: 12px; color: #409cff; background: transparent;")
        lbl.setText(f"⟳  Checking {name}…")
        QtWidgets.QApplication.processEvents()

        try:
            passed, detail = fn()
        except Exception as e:
            passed, detail = False, str(e)

        self._results.append({"name": name, "passed": passed, "detail": detail})
        self._progress.setValue(idx + 1)

        if passed:
            lbl.setStyleSheet("font-size: 12px; color: #30d158; font-weight: 600; background: transparent;")
            lbl.setText(f"✓  {name}: {detail}")
        else:
            lbl.setStyleSheet("font-size: 12px; color: #ff9f0a; font-weight: 600; background: transparent;")
            lbl.setText(f"⚠  {name}: {detail}")

        self._check_index += 1
        QtCore.QTimer.singleShot(140, self._run_next_check)

    def _on_min_time_elapsed(self):
        self._close_pending = True
        if self._checks_done:
            self.accept()

    def exec_and_wait(self):
        """Show splash, run pre-boot checks, wait for minimum duration, return results."""
        self.show()
        QtCore.QTimer.singleShot(100, self._run_next_check)
        QtCore.QTimer.singleShot(self.duration_ms, self._on_min_time_elapsed)
        self.exec_()
        return self._results
