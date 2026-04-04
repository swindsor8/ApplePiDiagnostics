#!/usr/bin/env python3
# Splash screen module for Apple Pi Diagnostics

import socket
import os
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore


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
    candidates = ["/dev/mmcblk0", "/dev/sda", "/dev/nvme0n1"]
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
                ip = next(
                    (a.address for a in addrs if a.family == 2),  # AF_INET
                    None,
                )
                detail = f"{name} UP" + (f" · {ip}" if ip else "")
                return True, detail
        return False, "No active network interfaces"
    except Exception:
        # psutil not available — fall back to /sys
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
    ]
    for mod, attr in modules:
        try:
            m = __import__(mod, fromlist=[attr])
            if not hasattr(m, attr):
                return False, f"{mod} missing {attr}"
        except Exception as e:
            return False, f"Import failed: {mod.split('.')[-2]}"
    return True, "All modules loaded"


_CHECKS = [
    ("System Info",      _check_system_info),
    ("Storage Media",    _check_storage),
    ("Network",          _check_network),
    ("Diagnostics Ready",_check_diagnostics),
]

# ---------------------------------------------------------------------------
# Splash screen
# ---------------------------------------------------------------------------

class SplashScreen(QtWidgets.QDialog):
    def __init__(self, parent=None, duration_ms=2500):
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
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(10)

        # Logo
        logo_label = QtWidgets.QLabel()
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        if LOGO_PATH and LOGO_PATH.exists():
            pix = QtGui.QPixmap(str(LOGO_PATH))
            pix = pix.scaledToWidth(280, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("[Apple Pi Diagnostics]")
            logo_label.setStyleSheet("font-size:20px; font-weight:600; color:#ffffff;")
        layout.addWidget(logo_label, alignment=QtCore.Qt.AlignCenter)

        # Title
        title = QtWidgets.QLabel("Apple Pi Diagnostics")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("""
            font-family: system-ui, 'Noto Sans', 'Inter', Arial, sans-serif;
            font-size: 26px;
            font-weight: 600;
            color: #ffffff;
        """)
        layout.addWidget(title, alignment=QtCore.Qt.AlignCenter)

        # Divider
        div = QtWidgets.QFrame()
        div.setFrameShape(QtWidgets.QFrame.HLine)
        div.setStyleSheet("color: rgba(255,255,255,0.25);")
        layout.addWidget(div)

        # Check items container
        checks_container = QtWidgets.QWidget()
        checks_layout = QtWidgets.QVBoxLayout(checks_container)
        checks_layout.setContentsMargins(8, 4, 8, 4)
        checks_layout.setSpacing(6)

        for name, _ in _CHECKS:
            lbl = QtWidgets.QLabel(f"○  Checking {name}…")
            lbl.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.5);")
            checks_layout.addWidget(lbl)
            self._check_labels.append(lbl)

        layout.addWidget(checks_container)

        # Size
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        w = min(520, screen.width() - 200)
        h = min(400, screen.height() - 200)
        self.setFixedSize(w, h)
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _run_next_check(self):
        idx = self._check_index
        if idx >= len(_CHECKS):
            self._checks_done = True
            if self._close_pending:
                self.accept()
            return

        name, fn = _CHECKS[idx]
        lbl = self._check_labels[idx]

        # Mark as running
        lbl.setStyleSheet("font-size: 12px; color: #93c5fd;")
        lbl.setText(f"⟳  Checking {name}…")
        QtWidgets.QApplication.processEvents()

        try:
            passed, detail = fn()
        except Exception as e:
            passed, detail = False, str(e)

        self._results.append({"name": name, "passed": passed, "detail": detail})

        if passed:
            lbl.setStyleSheet("font-size: 12px; color: #10b981; font-weight: 500;")
            lbl.setText(f"✓  {name}: {detail}")
        else:
            lbl.setStyleSheet("font-size: 12px; color: #f59e0b; font-weight: 500;")
            lbl.setText(f"⚠  {name}: {detail}")

        self._check_index += 1
        # Run next check after a short pause so the UI updates visibly
        QtCore.QTimer.singleShot(200, self._run_next_check)

    def _on_min_time_elapsed(self):
        self._close_pending = True
        if self._checks_done:
            self.accept()

    def exec_and_wait(self):
        """Show splash, run pre-boot checks, wait for minimum duration, return results."""
        self.show()
        # Start checks after a brief delay so the window renders first
        QtCore.QTimer.singleShot(150, self._run_next_check)
        # Minimum display time
        QtCore.QTimer.singleShot(self.duration_ms, self._on_min_time_elapsed)
        self.exec_()
        return self._results
