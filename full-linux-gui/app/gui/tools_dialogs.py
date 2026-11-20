#!/usr/bin/env python3
"""Interactive hardware and kiosk dialogs for Apple Pi Diagnostics.

Provides:
  - HdmiPatternDialog: fullscreen color bars / dead-pixel / checkerboard test
  - GpioPinoutDialog: 40-pin Raspberry Pi header viewer with read-only live state
  - WifiConnectDialog: nmcli-backed Wi-Fi scanner and connector for kiosk mode
  - QrPreviewDialog: on-screen QR code viewer for local report sharing
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import threading
from typing import Dict, List, Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets


# ---------------------------------------------------------------------------
# 1. HDMI Pattern & Dead-Pixel Test Dialog
# ---------------------------------------------------------------------------

_HDMI_MODES = [
    "Color Bars",
    "Solid Red",
    "Solid Green",
    "Solid Blue",
    "Solid White",
    "Solid Black",
    "Checkerboard",
]


class HdmiPatternDialog(QtWidgets.QDialog):
    """Fullscreen display test pattern cycler (click/Space to cycle, Esc to exit)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HDMI Display Pattern Test")
        self.mode_index = 0
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setWindowState(QtCore.Qt.WindowFullScreen)

    def _next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(_HDMI_MODES)
        self.update()

    def _prev_mode(self):
        self.mode_index = (self.mode_index - 1) % len(_HDMI_MODES)
        self.update()

    def _play_test_beep(self):
        """Play a short non-blocking audio tone if speaker-test or Qt beep is available."""
        QtWidgets.QApplication.beep()
        if shutil.which("speaker-test"):
            def _beep():
                try:
                    subprocess.run(
                        ["speaker-test", "-t", "sine", "-f", "880", "-l", "1"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=3,
                    )
                except Exception:
                    pass
            threading.Thread(target=_beep, daemon=True).start()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.accept()
        else:
            self._next_mode()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (QtCore.Qt.Key_Escape, QtCore.Qt.Key_Q):
            self.accept()
        elif key in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Right, QtCore.Qt.Key_Return):
            self._next_mode()
        elif key == QtCore.Qt.Key_Left:
            self._prev_mode()
        elif key == QtCore.Qt.Key_A:
            self._play_test_beep()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        mode = _HDMI_MODES[self.mode_index]

        if mode == "Color Bars":
            bars = [
                "#c0c0c0", "#c0c000", "#00c0c0", "#00c000",
                "#c000c0", "#c00000", "#0000c0", "#101010",
            ]
            bar_w = max(1, w // len(bars))
            for idx, col in enumerate(bars):
                x = idx * bar_w
                cw = w - x if idx == len(bars) - 1 else bar_w
                painter.fillRect(x, 0, cw, h, QtGui.QColor(col))
        elif mode == "Solid Red":
            painter.fillRect(0, 0, w, h, QtGui.QColor("#ff0000"))
        elif mode == "Solid Green":
            painter.fillRect(0, 0, w, h, QtGui.QColor("#00ff00"))
        elif mode == "Solid Blue":
            painter.fillRect(0, 0, w, h, QtGui.QColor("#0000ff"))
        elif mode == "Solid White":
            painter.fillRect(0, 0, w, h, QtGui.QColor("#ffffff"))
        elif mode == "Solid Black":
            painter.fillRect(0, 0, w, h, QtGui.QColor("#000000"))
        elif mode == "Checkerboard":
            cell = 40
            for y in range(0, h, cell):
                for x in range(0, w, cell):
                    is_white = ((x // cell) + (y // cell)) % 2 == 0
                    painter.fillRect(
                        x, y, cell, cell,
                        QtGui.QColor("#ffffff" if is_white else "#111111"),
                    )

        # Overlay HUD banner at top center
        hud_text = (
            f"{mode} ({self.mode_index + 1}/{len(_HDMI_MODES)})  —  "
            "Click / Space: Next  |  A: Audio Beep  |  Esc / Right-Click: Exit"
        )
        font = QtGui.QFont("Sans", 12, QtGui.QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(hud_text) + 32
        th = fm.height() + 18
        rect = QtCore.QRect((w - tw) // 2, 20, tw, th)
        painter.fillRect(rect, QtGui.QColor(0, 0, 0, 185))
        painter.setPen(QtGui.QColor("#ffffff"))
        painter.drawText(rect, QtCore.Qt.AlignCenter, hud_text)
        painter.end()


# ---------------------------------------------------------------------------
# 2. 40-Pin Raspberry Pi GPIO Header Viewer (read-only)
# ---------------------------------------------------------------------------

# (physical_pin, label, kind, bcm_num_or_none)
_PI_40_PINS: List[Tuple[int, str, str, Optional[int]]] = [
    (1, "3.3V", "3v3", None),         (2, "5V", "5v", None),
    (3, "GPIO2 (SDA1)", "gpio", 2),   (4, "5V", "5v", None),
    (5, "GPIO3 (SCL1)", "gpio", 3),   (6, "GND", "gnd", None),
    (7, "GPIO4", "gpio", 4),          (8, "GPIO14 (TXD)", "gpio", 14),
    (9, "GND", "gnd", None),          (10, "GPIO15 (RXD)", "gpio", 15),
    (11, "GPIO17", "gpio", 17),       (12, "GPIO18 (PWM0)", "gpio", 18),
    (13, "GPIO27", "gpio", 27),       (14, "GND", "gnd", None),
    (15, "GPIO22", "gpio", 22),       (16, "GPIO23", "gpio", 23),
    (17, "3.3V", "3v3", None),        (18, "GPIO24", "gpio", 24),
    (19, "GPIO10 (MOSI)", "gpio", 10),(20, "GND", "gnd", None),
    (21, "GPIO9 (MISO)", "gpio", 9),  (22, "GPIO25", "gpio", 25),
    (23, "GPIO11 (SCLK)", "gpio", 11),(24, "GPIO8 (CE0)", "gpio", 8),
    (25, "GND", "gnd", None),         (26, "GPIO7 (CE1)", "gpio", 7),
    (27, "ID_SD", "id", None),        (28, "ID_SC", "id", None),
    (29, "GPIO5", "gpio", 5),         (30, "GND", "gnd", None),
    (31, "GPIO6", "gpio", 6),         (32, "GPIO12", "gpio", 12),
    (33, "GPIO13", "gpio", 13),       (34, "GND", "gnd", None),
    (35, "GPIO19", "gpio", 19),       (36, "GPIO16", "gpio", 16),
    (37, "GPIO26", "gpio", 26),       (38, "GPIO20", "gpio", 20),
    (39, "GND", "gnd", None),         (40, "GPIO21", "gpio", 21),
]


def _read_gpio_states_readonly() -> Tuple[Optional[str], Dict[int, str]]:
    """Best-effort read-only GPIO level snapshot via pinctrl/raspi-gpio."""
    if shutil.which("pinctrl"):
        try:
            out = subprocess.check_output(
                ["pinctrl", "get"], text=True, stderr=subprocess.DEVNULL, timeout=3
            )
            states: Dict[int, str] = {}
            for ln in out.splitlines():
                parts = ln.split(":")
                if len(parts) < 2:
                    continue
                head = parts[0].strip()
                if head.isdigit():
                    bcm = int(head)
                    body = parts[1].lower()
                    if " hi " in f" {body} " or "| hi" in body:
                        states[bcm] = "HIGH"
                    elif " lo " in f" {body} " or "| lo" in body:
                        states[bcm] = "LOW"
            if states:
                return "pinctrl", states
        except Exception:
            pass

    if shutil.which("raspi-gpio"):
        try:
            out = subprocess.check_output(
                ["raspi-gpio", "get"], text=True, stderr=subprocess.DEVNULL, timeout=3
            )
            states = {}
            for ln in out.splitlines():
                if not ln.startswith("GPIO "):
                    continue
                head, _, rest = ln.partition(":")
                num_str = head.replace("GPIO ", "").strip()
                if num_str.isdigit():
                    bcm = int(num_str)
                    if "level=1" in rest:
                        states[bcm] = "HIGH"
                    elif "level=0" in rest:
                        states[bcm] = "LOW"
            if states:
                return "raspi-gpio", states
        except Exception:
            pass

    return None, {}


class GpioPinoutDialog(QtWidgets.QDialog):
    """Read-only interactive 40-pin Raspberry Pi header diagram."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Raspberry Pi 40-Pin GPIO Viewer (Read-Only)")
        self.setMinimumSize(680, 620)
        self._state_labels: Dict[int, QtWidgets.QLabel] = {}
        self._build_ui()

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._refresh_states)
        self._refresh_states()
        self._timer.start(1500)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        self._status_lbl = QtWidgets.QLabel("Reading GPIO header state (read-only — no pins toggled)…")
        self._status_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #1a1a1a;")
        layout.addWidget(self._status_lbl)

        legend = QtWidgets.QLabel(
            "Legend:  [5V = Red]  [3.3V = Amber]  [GND = Gray]  [GPIO HIGH = Green]  [GPIO LOW = Blue]"
        )
        legend.setStyleSheet("font-size: 11px; color: #555555;")
        layout.addWidget(legend)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        grid_widget = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_widget)
        grid.setSpacing(4)

        kind_colors = {
            "5v": ("#ef4444", "#ffffff"),
            "3v3": ("#f59e0b", "#111111"),
            "gnd": ("#374151", "#ffffff"),
            "id": ("#6b7280", "#ffffff"),
            "gpio": ("#2563eb", "#ffffff"),
        }

        for row_idx in range(20):
            left_pin = _PI_40_PINS[row_idx * 2]
            right_pin = _PI_40_PINS[row_idx * 2 + 1]

            for side, pin_tuple in ((0, left_pin), (1, right_pin)):
                pnum, plabel, pkind, bcm = pin_tuple
                bg, fg = kind_colors.get(pkind, ("#6b7280", "#ffffff"))

                num_lbl = QtWidgets.QLabel(f"{pnum:02d}")
                num_lbl.setAlignment(QtCore.Qt.AlignCenter)
                num_lbl.setFixedSize(30, 24)
                num_lbl.setStyleSheet(
                    f"background-color: {bg}; color: {fg}; border-radius: 12px; font-size: 11px; font-weight: 700;"
                )

                name_lbl = QtWidgets.QLabel(plabel)
                name_lbl.setStyleSheet("font-size: 12px; color: #1a1a1a; padding: 0 6px;")

                state_lbl = QtWidgets.QLabel("—" if bcm is not None else "")
                state_lbl.setFixedWidth(48)
                state_lbl.setAlignment(QtCore.Qt.AlignCenter)
                state_lbl.setStyleSheet("font-size: 11px; color: #666666; font-weight: 600;")
                if bcm is not None:
                    self._state_labels[bcm] = state_lbl

                if side == 0:
                    name_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    grid.addWidget(state_lbl, row_idx, 0)
                    grid.addWidget(name_lbl, row_idx, 1)
                    grid.addWidget(num_lbl, row_idx, 2)
                else:
                    name_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                    grid.addWidget(num_lbl, row_idx, 3)
                    grid.addWidget(name_lbl, row_idx, 4)
                    grid.addWidget(state_lbl, row_idx, 5)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _refresh_states(self):
        driver, states = _read_gpio_states_readonly()
        if driver:
            self._status_lbl.setText(
                f"Live GPIO states via {driver} ({len(states)} pins read, read-only)"
            )
            for bcm, lbl in self._state_labels.items():
                val = states.get(bcm)
                if val == "HIGH":
                    lbl.setText("HIGH")
                    lbl.setStyleSheet(
                        "font-size: 11px; font-weight: 700; color: #ffffff; background-color: #10b981; border-radius: 4px;"
                    )
                elif val == "LOW":
                    lbl.setText("LOW")
                    lbl.setStyleSheet(
                        "font-size: 11px; font-weight: 700; color: #ffffff; background-color: #2563eb; border-radius: 4px;"
                    )
                else:
                    lbl.setText("—")
        else:
            self._status_lbl.setText(
                "Reference 40-pin layout (live pin polling requires Raspberry Pi pinctrl / raspi-gpio)"
            )

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# 3. Kiosk Wi-Fi Setup Dialog (nmcli)
# ---------------------------------------------------------------------------

class WifiConnectDialog(QtWidgets.QDialog):
    """Scan and connect to Wi-Fi networks using NetworkManager (nmcli)."""

    sig_scan_done = QtCore.pyqtSignal(list, str)
    sig_connect_done = QtCore.pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wi-Fi Setup")
        self.setMinimumSize(480, 420)
        self.sig_scan_done.connect(self._on_scan_done)
        self.sig_connect_done.connect(self._on_connect_done)
        self._build_ui()
        self._scan_networks()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        self._status = QtWidgets.QLabel("Scanning for Wi-Fi networks…")
        self._status.setStyleSheet("font-size: 13px; color: #333333;")
        top.addWidget(self._status)
        top.addStretch()
        self._scan_btn = QtWidgets.QPushButton("Rescan")
        self._scan_btn.clicked.connect(self._scan_networks)
        top.addWidget(self._scan_btn)
        layout.addLayout(top)

        self._list = QtWidgets.QListWidget()
        self._list.itemSelectionChanged.connect(self._on_select_network)
        layout.addWidget(self._list)

        form = QtWidgets.QFormLayout()
        self._ssid_edit = QtWidgets.QLineEdit()
        self._ssid_edit.setPlaceholderText("Select a network above or enter SSID")
        self._pass_edit = QtWidgets.QLineEdit()
        self._pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self._pass_edit.setPlaceholderText("Leave blank for open networks")
        form.addRow("Network (SSID):", self._ssid_edit)
        form.addRow("Password:", self._pass_edit)
        layout.addLayout(form)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch()
        self._connect_btn = QtWidgets.QPushButton("Connect")
        self._connect_btn.setStyleSheet(
            "background-color: #0078d4; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: 600;"
        )
        self._connect_btn.clicked.connect(self._connect)
        btns.addWidget(self._connect_btn)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _on_select_network(self):
        items = self._list.selectedItems()
        if items:
            ssid = items[0].data(QtCore.Qt.UserRole)
            if ssid:
                self._ssid_edit.setText(ssid)

    def _scan_networks(self):
        if not shutil.which("nmcli"):
            self._status.setText("NetworkManager (nmcli) is not available on this host.")
            self._connect_btn.setEnabled(False)
            return
        self._scan_btn.setEnabled(False)
        self._status.setText("Scanning for Wi-Fi networks…")

        def _worker():
            try:
                proc = subprocess.run(
                    ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if proc.returncode != 0:
                    self.sig_scan_done.emit([], (proc.stderr or proc.stdout or "Scan failed").strip())
                    return
                seen = set()
                networks = []
                for ln in proc.stdout.splitlines():
                    parts = ln.split(":")
                    if not parts or not parts[0].strip():
                        continue
                    ssid = parts[0].strip()
                    if ssid in seen:
                        continue
                    seen.add(ssid)
                    sig = parts[1].strip() if len(parts) > 1 else "?"
                    sec = parts[2].strip() if len(parts) > 2 else "Open"
                    networks.append((ssid, sig, sec or "Open"))
                self.sig_scan_done.emit(networks, "")
            except Exception as e:
                self.sig_scan_done.emit([], str(e))

        threading.Thread(target=_worker, daemon=True).start()

    @QtCore.pyqtSlot(list, str)
    def _on_scan_done(self, networks, err):
        self._scan_btn.setEnabled(True)
        self._list.clear()
        if err:
            self._status.setText(f"Scan error: {err}")
            return
        for ssid, sig, sec in networks:
            item = QtWidgets.QListWidgetItem(f"{ssid}   ({sig}%  ·  {sec})")
            item.setData(QtCore.Qt.UserRole, ssid)
            self._list.addItem(item)
        self._status.setText(f"Found {len(networks)} Wi-Fi network(s).")

    def _connect(self):
        ssid = self._ssid_edit.text().strip()
        password = self._pass_edit.text()
        if not ssid:
            self._status.setText("Please select or enter a network SSID.")
            return
        self._connect_btn.setEnabled(False)
        self._status.setText(f"Connecting to {ssid}…")

        def _worker():
            try:
                cmd = ["nmcli", "dev", "wifi", "connect", ssid]
                if password:
                    cmd.extend(["password", password])
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
                if proc.returncode == 0:
                    self.sig_connect_done.emit(True, f"Connected to {ssid}!")
                else:
                    msg = (proc.stderr or proc.stdout or "Connection failed").strip()
                    self.sig_connect_done.emit(False, msg)
            except Exception as e:
                self.sig_connect_done.emit(False, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    @QtCore.pyqtSlot(bool, str)
    def _on_connect_done(self, ok, message):
        self._connect_btn.setEnabled(True)
        self._status.setText(message)
        if ok:
            QtWidgets.QMessageBox.information(self, "Wi-Fi Connected", message)


# ---------------------------------------------------------------------------
# 4. QR Code Preview Dialog
# ---------------------------------------------------------------------------

class QrPreviewDialog(QtWidgets.QDialog):
    """Display generated QR code and local URL while the HTTP report server runs."""

    def __init__(self, url: str, qr_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share Report via QR Code")
        self.setMinimumSize(420, 460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        heading = QtWidgets.QLabel("Scan with your phone on the same Wi-Fi / LAN")
        heading.setAlignment(QtCore.Qt.AlignCenter)
        heading.setStyleSheet("font-size: 14px; font-weight: 600; color: #1a1a1a;")
        layout.addWidget(heading)

        img_lbl = QtWidgets.QLabel()
        img_lbl.setAlignment(QtCore.Qt.AlignCenter)
        if qr_path and Path(qr_path).is_file():
            pix = QtGui.QPixmap(str(qr_path)).scaled(
                280, 280, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            img_lbl.setPixmap(pix)
        else:
            img_lbl.setText("QR image unavailable")
        layout.addWidget(img_lbl)

        url_lbl = QtWidgets.QLabel(url)
        url_lbl.setAlignment(QtCore.Qt.AlignCenter)
        url_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        url_lbl.setStyleSheet(
            "font-family: monospace; font-size: 13px; color: #0078d4; padding: 4px;"
        )
        layout.addWidget(url_lbl)

        if "127.0.0.1" in url:
            warn = QtWidgets.QLabel(
                "No LAN IP detected — connect Ethernet or Wi-Fi so your phone can reach this device."
            )
            warn.setWordWrap(True)
            warn.setAlignment(QtCore.Qt.AlignCenter)
            warn.setStyleSheet("font-size: 12px; color: #b45309;")
            layout.addWidget(warn)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=QtCore.Qt.AlignCenter)
