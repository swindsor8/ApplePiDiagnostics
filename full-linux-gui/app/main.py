#!/usr/bin/env python3
"""Apple Pi Diagnostics — Modern Hardware Diagnostic Suite (PyQt5)."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List

from PyQt5 import QtCore, QtGui, QtWidgets

from config import APP_VERSION, GATEWAY_PROBE_HOST, GATEWAY_PROBE_PORT, NETWORK_DNS_CHECK_HOST
from diagnostics.bootloader.bootloader_test import run_bootloader_quick_test
from diagnostics.cpu.cpu_test import run_cpu_quick_test
from diagnostics.gpio.gpio_test import run_gpio_quick_test
from diagnostics.hdmi.hdmi_test import run_hdmi_quick_test
from diagnostics.network.network_test import run_network_quick_test
from diagnostics.peripherals.peripherals_test import run_peripherals_quick_test
from diagnostics.power.power_test import run_power_quick_test
from diagnostics.ram.ram_test import run_ram_quick_test
from diagnostics.report_builder import build_report
from diagnostics.storage.storage_test import run_storage_quick_test
from diagnostics.usb.usb_test import run_usb_quick_test
from exports.export_qr import QRExportManager, generate_qr_image
from exports.export_sd_boot import save_report_to_sdboot
from exports.export_usb import save_report_to_usb
from gui.theme import THEMES, build_stylesheet, make_svg_icon
from gui.tools_dialogs import (
    GpioPinoutDialog,
    HdmiPatternDialog,
    QrPreviewDialog,
    WifiConnectDialog,
)
from gui.widgets import DiagnosticCard, HealthRingWidget, TelemetryTile, ToolActionCard

try:
    from gui.splash import LOGO_PATH
except Exception:
    LOGO_PATH = None

APP_DIR = Path(__file__).resolve().parents[1]


def _get_report_dir() -> Path:
    report_dir = Path(
        os.environ.get("APD_REPORT_DIR") or APP_DIR / "reports"
    ).expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


REPORT_DIR = _get_report_dir()

# Diagnostic module catalogue: (id, title, subtitle, icon_key, category)
_DIAGNOSTIC_SPECS = [
    ("cpu", "CPU", "Multi-core load & temp", "cpu", "Core"),
    ("ram", "RAM", "Pattern write & verify", "ram", "Core"),
    ("sd", "Storage", "Speed, CID & SMART", "sd", "Core"),
    ("power", "Power & Thermal", "Voltage & throttling", "power", "Core"),
    ("network", "Network", "Interfaces, ping & DNS", "network", "I/O & Display"),
    ("usb", "USB", "Bus & device scan", "usb", "I/O & Display"),
    ("hdmi", "HDMI", "Display & KMS check", "hdmi", "I/O & Display"),
    ("gpio", "GPIO", "Header driver probe", "gpio", "I/O & Display"),
    ("bootloader", "Bootloader", "EEPROM & /boot health", "bootloader", "System"),
    ("peripherals", "Peripherals", "I2C, SPI, BT, Audio, Cam", "peripherals", "System"),
]

_TEST_LABELS = {spec[0]: spec[1] for spec in _DIAGNOSTIC_SPECS}

_PAGE_META = [
    ("Dashboard", "Live hardware telemetry, board identity, and overall health"),
    ("Diagnostics", "Run individual hardware modules or execute the full verification suite"),
    ("Hardware Tools", "Interactive display patterns, 40-pin GPIO viewer, and Wi-Fi setup"),
    ("Results & Export", "Review plain-English findings and export PDF, USB, SD, or QR reports"),
    ("Settings", "Appearance, network diagnostics, report location, and device power"),
]


class MainWindow(QtWidgets.QMainWindow):
    """Modern sidebar-driven dashboard for Apple Pi Diagnostics."""

    sig_test_finished = QtCore.pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        self.theme_name = "dark"
        self.latest_report_dir = None
        self.qr_manager = None
        self.test_cards: Dict[str, DiagnosticCard] = {}
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.results_lock = threading.Lock()
        self._running_tests: set[str] = set()
        self._startup_results: List[Dict[str, Any]] = []
        self._active_category = "All"

        self.setWindowTitle(f"Apple Pi Diagnostics ({APP_VERSION})")
        self.setMinimumSize(1024, 680)
        if LOGO_PATH and Path(LOGO_PATH).exists():
            self.setWindowIcon(QtGui.QIcon(str(LOGO_PATH)))

        self.sig_test_finished.connect(self._on_test_finished)

        self._build_ui()
        self._apply_theme(self.theme_name)
        self._update_system_info()
        self._refresh_network_info()

        # Live telemetry every 2 seconds
        self._telemetry_timer = QtCore.QTimer(self)
        self._telemetry_timer.timeout.connect(self._update_live_telemetry)
        self._update_live_telemetry()
        self._telemetry_timer.start(2000)

    # -----------------------------------------------------------------------
    # Shell Construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        root = QtWidgets.QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)

        outer = QtWidgets.QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Left navigation sidebar
        outer.addWidget(self._create_sidebar())

        # Right main column: top bar + progress strip + stacked pages
        right_col = QtWidgets.QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        right_col.addWidget(self._create_top_bar())

        self._suite_progress = QtWidgets.QProgressBar()
        self._suite_progress.setFixedHeight(3)
        self._suite_progress.setTextVisible(False)
        self._suite_progress.setRange(0, len(_DIAGNOSTIC_SPECS))
        self._suite_progress.setValue(0)
        self._suite_progress.setVisible(False)
        right_col.addWidget(self._suite_progress)

        self.pages = QtWidgets.QStackedWidget()
        self.pages.addWidget(self._create_dashboard_page())
        self.pages.addWidget(self._create_diagnostics_page())
        self.pages.addWidget(self._create_tools_page())
        self.pages.addWidget(self._create_results_page())
        self.pages.addWidget(self._create_settings_page())
        right_col.addWidget(self.pages, stretch=1)

        outer.addLayout(right_col, stretch=1)

        self._switch_page(0)
        self.statusBar().showMessage(f"Ready  ·  Apple Pi Diagnostics {APP_VERSION}")

    def _create_sidebar(self) -> QtWidgets.QWidget:
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(226)

        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 16)
        layout.setSpacing(6)

        # Brand block
        brand_row = QtWidgets.QHBoxLayout()
        brand_row.setSpacing(10)
        logo_lbl = QtWidgets.QLabel()
        logo_lbl.setFixedSize(36, 36)
        logo_lbl.setAlignment(QtCore.Qt.AlignCenter)
        if LOGO_PATH and Path(LOGO_PATH).exists():
            pix = QtGui.QPixmap(str(LOGO_PATH)).scaled(
                34, 34, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("Pi")
            logo_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #0a84ff;")
        brand_row.addWidget(logo_lbl)

        brand_text = QtWidgets.QVBoxLayout()
        brand_text.setSpacing(1)
        b_title = QtWidgets.QLabel("Apple Pi")
        b_title.setStyleSheet("font-size: 15px; font-weight: 800;")
        b_sub = QtWidgets.QLabel("Diagnostics")
        b_sub.setObjectName("MutedLabel")
        brand_text.addWidget(b_title)
        brand_text.addWidget(b_sub)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        ver_row = QtWidgets.QHBoxLayout()
        ver_pill = QtWidgets.QLabel(APP_VERSION)
        ver_pill.setObjectName("VersionPill")
        ver_row.addWidget(ver_pill)
        ver_row.addStretch()
        layout.addLayout(ver_row)

        layout.addSpacing(14)

        # Navigation buttons
        self._nav_buttons: List[tuple[QtWidgets.QPushButton, str]] = []
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Diagnostics", "diagnostics"),
            ("Hardware Tools", "tools"),
            ("Results & Export", "results"),
            ("Settings", "settings"),
        ]
        for idx, (label, icon_key) in enumerate(nav_items):
            btn = QtWidgets.QPushButton(f"  {label}")
            btn.setObjectName("NavButton")
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            btn.setIconSize(QtCore.QSize(17, 17))
            btn.clicked.connect(lambda _checked=False, i=idx: self._switch_page(i))
            layout.addWidget(btn)
            self._nav_buttons.append((btn, icon_key))

        layout.addStretch()

        # Theme toggle
        self._theme_btn = QtWidgets.QPushButton("  Light Mode")
        self._theme_btn.setObjectName("SecondaryButton")
        self._theme_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self._theme_btn)

        layout.addSpacing(4)

        # Compact device power row
        pwr_row = QtWidgets.QHBoxLayout()
        pwr_row.setSpacing(6)
        self._sidebar_reboot_btn = QtWidgets.QPushButton("Reboot")
        self._sidebar_reboot_btn.setObjectName("SecondaryButton")
        self._sidebar_reboot_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._sidebar_reboot_btn.clicked.connect(lambda: self._confirm_system_power("reboot"))
        pwr_row.addWidget(self._sidebar_reboot_btn)

        self._sidebar_shutdown_btn = QtWidgets.QPushButton("Power Off")
        self._sidebar_shutdown_btn.setObjectName("DangerButton")
        self._sidebar_shutdown_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._sidebar_shutdown_btn.clicked.connect(lambda: self._confirm_system_power("poweroff"))
        pwr_row.addWidget(self._sidebar_shutdown_btn)
        layout.addLayout(pwr_row)

        return sidebar

    def _create_top_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(68)

        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(10)

        title_col = QtWidgets.QVBoxLayout()
        title_col.setSpacing(1)
        self._top_title = QtWidgets.QLabel("Dashboard")
        self._top_title.setObjectName("PageTitle")
        self._top_subtitle = QtWidgets.QLabel("")
        self._top_subtitle.setObjectName("PageSubtitle")
        title_col.addWidget(self._top_title)
        title_col.addWidget(self._top_subtitle)
        layout.addLayout(title_col)

        layout.addStretch()

        self.run_all_btn = QtWidgets.QPushButton("  Run All Tests")
        self.run_all_btn.setObjectName("PrimaryButton")
        self.run_all_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.run_all_btn.clicked.connect(self.run_all_tests)
        layout.addWidget(self.run_all_btn)

        self.export_btn = QtWidgets.QPushButton("PDF Report")
        self.export_btn.setObjectName("SecondaryButton")
        self.export_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.export_btn.clicked.connect(self.generate_and_preview_pdf)
        layout.addWidget(self.export_btn)

        self.qr_btn = QtWidgets.QPushButton("QR Share")
        self.qr_btn.setObjectName("SecondaryButton")
        self.qr_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.qr_btn.clicked.connect(self.export_qr)
        layout.addWidget(self.qr_btn)

        return bar

    # -----------------------------------------------------------------------
    # Page 0: Dashboard
    # -----------------------------------------------------------------------

    def _create_dashboard_page(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(18)

        # Hero health summary card
        hero = QtWidgets.QFrame()
        hero.setObjectName("HeroCard")
        hero_lay = QtWidgets.QHBoxLayout(hero)
        hero_lay.setContentsMargins(22, 18, 22, 18)
        hero_lay.setSpacing(22)

        self.health_ring = HealthRingWidget()
        hero_lay.addWidget(self.health_ring)

        hero_text = QtWidgets.QVBoxLayout()
        hero_text.setSpacing(6)
        self._hero_heading = QtWidgets.QLabel("System Ready for Diagnostics")
        self._hero_heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        self._hero_detail = QtWidgets.QLabel(
            "Run the full 10-module hardware verification suite or pick individual checks in Diagnostics."
        )
        self._hero_detail.setObjectName("PageSubtitle")
        self._hero_detail.setWordWrap(True)
        hero_text.addWidget(self._hero_heading)
        hero_text.addWidget(self._hero_detail)

        hero_btns = QtWidgets.QHBoxLayout()
        hero_btns.setSpacing(10)
        hero_run = QtWidgets.QPushButton("Start Full Verification")
        hero_run.setObjectName("PrimaryButton")
        hero_run.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        hero_run.clicked.connect(self.run_all_tests)
        hero_btns.addWidget(hero_run)

        hero_diag = QtWidgets.QPushButton("Browse 10 Modules")
        hero_diag.setObjectName("SecondaryButton")
        hero_diag.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        hero_diag.clicked.connect(lambda: self._switch_page(1))
        hero_btns.addWidget(hero_diag)

        hero_tools = QtWidgets.QPushButton("Open Hardware Tools")
        hero_tools.setObjectName("SecondaryButton")
        hero_tools.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        hero_tools.clicked.connect(lambda: self._switch_page(2))
        hero_btns.addWidget(hero_tools)
        hero_btns.addStretch()
        hero_text.addSpacing(4)
        hero_text.addLayout(hero_btns)
        hero_lay.addLayout(hero_text, stretch=1)
        layout.addWidget(hero)

        # Live Telemetry row (4 tiles)
        telem_row = QtWidgets.QHBoxLayout()
        telem_row.setSpacing(14)
        self._telemetry_tiles: Dict[str, TelemetryTile] = {
            "cpu": TelemetryTile("CPU Load", "cpu"),
            "ram": TelemetryTile("Memory Usage", "ram"),
            "temp": TelemetryTile("SoC Temperature", "power"),
            "power": TelemetryTile("Power & Throttle", "bootloader"),
        }
        for tile in self._telemetry_tiles.values():
            telem_row.addWidget(tile)
        layout.addLayout(telem_row)

        # Bottom split: Device Identity (left) + Pre-Boot Checks (right)
        split = QtWidgets.QHBoxLayout()
        split.setSpacing(16)

        sys_card = QtWidgets.QFrame()
        sys_card.setObjectName("Card")
        sys_lay = QtWidgets.QVBoxLayout(sys_card)
        sys_lay.setContentsMargins(20, 18, 20, 18)
        sys_lay.setSpacing(12)
        sys_title = QtWidgets.QLabel("Board & System Identity")
        sys_title.setObjectName("SectionHeading")
        sys_lay.addWidget(sys_title)
        self.sys_info_layout = QtWidgets.QGridLayout()
        self.sys_info_layout.setVerticalSpacing(8)
        self.sys_info_layout.setHorizontalSpacing(16)
        sys_lay.addLayout(self.sys_info_layout)
        sys_lay.addStretch()
        split.addWidget(sys_card, stretch=1)

        checks_card = QtWidgets.QFrame()
        checks_card.setObjectName("Card")
        checks_lay = QtWidgets.QVBoxLayout(checks_card)
        checks_lay.setContentsMargins(20, 18, 20, 18)
        checks_lay.setSpacing(10)
        checks_title = QtWidgets.QLabel("Pre-Boot Health Checks")
        checks_title.setObjectName("SectionHeading")
        checks_lay.addWidget(checks_title)

        self._overview_checks_layout = QtWidgets.QVBoxLayout()
        self._overview_checks_layout.setSpacing(8)
        waiting = QtWidgets.QLabel("No pre-boot check summary recorded.")
        waiting.setObjectName("MutedLabel")
        self._overview_checks_layout.addWidget(waiting)
        checks_lay.addLayout(self._overview_checks_layout)
        checks_lay.addStretch()
        split.addWidget(checks_card, stretch=1)

        layout.addLayout(split)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # -----------------------------------------------------------------------
    # Page 1: Diagnostics (10 Filterable Cards)
    # -----------------------------------------------------------------------

    def _create_diagnostics_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(14)

        # Category filter bar
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.setSpacing(8)
        self._filter_buttons: Dict[str, QtWidgets.QPushButton] = {}
        for cat in ("All", "Core", "I/O & Display", "System"):
            btn = QtWidgets.QPushButton(cat)
            btn.setObjectName("FilterPill")
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            btn.clicked.connect(lambda _checked=False, c=cat: self._set_category_filter(c))
            filter_row.addWidget(btn)
            self._filter_buttons[cat] = btn
        filter_row.addStretch()

        clear_inline = QtWidgets.QPushButton("Reset Cards")
        clear_inline.setObjectName("SecondaryButton")
        clear_inline.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        clear_inline.clicked.connect(self.clear_results)
        filter_row.addWidget(clear_inline)
        layout.addLayout(filter_row)

        # Scrollable grid
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self._diag_grid_widget = QtWidgets.QWidget()
        self._diag_grid = QtWidgets.QGridLayout(self._diag_grid_widget)
        self._diag_grid.setContentsMargins(0, 0, 0, 0)
        self._diag_grid.setSpacing(14)

        for test_id, title, subtitle, icon_key, category in _DIAGNOSTIC_SPECS:
            card = DiagnosticCard(title, subtitle, icon_key, category=category)
            card.test_btn.clicked.connect(lambda _checked=False, tid=test_id: self.run_test(tid))
            self.test_cards[test_id] = card

        scroll.setWidget(self._diag_grid_widget)
        layout.addWidget(scroll, stretch=1)

        self._set_category_filter("All")
        return page

    def _set_category_filter(self, category: str):
        self._active_category = category
        for cat, btn in self._filter_buttons.items():
            btn.setProperty("active", cat == category)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Clear grid without deleting card widgets
        while self._diag_grid.count():
            self._diag_grid.takeAt(0)

        cols = 4
        idx = 0
        for test_id, *_rest in _DIAGNOSTIC_SPECS:
            card = self.test_cards[test_id]
            visible = category == "All" or card.category == category
            card.setVisible(visible)
            if visible:
                self._diag_grid.addWidget(card, idx // cols, idx % cols)
                idx += 1

        # Pad trailing columns so cards keep uniform width
        for c in range(cols):
            self._diag_grid.setColumnStretch(c, 1)
        self._diag_grid.setRowStretch((idx // cols) + 1, 1)

    # -----------------------------------------------------------------------
    # Page 2: Interactive Hardware Tools
    # -----------------------------------------------------------------------

    def _create_tools_page(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(18)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(16)

        self._tool_cards: List[ToolActionCard] = []

        hdmi_card = ToolActionCard(
            "HDMI Pattern & Audio Test",
            "Launch a fullscreen visual test cycling through SMPTE color bars, solid Red/Green/Blue/White/Black dead-pixel screens, checkerboard geometry, and an optional audio tone.",
            "Launch Display Test",
            "hdmi",
        )
        hdmi_card.action_btn.clicked.connect(self.open_hdmi_pattern)
        grid.addWidget(hdmi_card, 0, 0)
        self._tool_cards.append(hdmi_card)

        gpio_card = ToolActionCard(
            "GPIO 40-Pin Header Viewer",
            "Inspect the Raspberry Pi 40-pin header pinout with color-coded power/ground rails and live read-only HIGH/LOW pin polling (safe — never drives pins).",
            "Open Pinout Viewer",
            "gpio",
        )
        gpio_card.action_btn.clicked.connect(self.open_gpio_viewer)
        grid.addWidget(gpio_card, 0, 1)
        self._tool_cards.append(gpio_card)

        wifi_card = ToolActionCard(
            "Wi-Fi Network Setup",
            "Scan nearby wireless networks and connect directly from kiosk mode using NetworkManager so network tests and phone QR sharing work without Ethernet.",
            "Configure Wi-Fi",
            "wifi",
        )
        wifi_card.action_btn.clicked.connect(self.open_wifi_dialog)
        grid.addWidget(wifi_card, 0, 2)
        self._tool_cards.append(wifi_card)

        for c in range(3):
            grid.setColumnStretch(c, 1)

        layout.addLayout(grid)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # -----------------------------------------------------------------------
    # Page 3: Results & Export
    # -----------------------------------------------------------------------

    def _create_results_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(14)

        # KPI + Export action bar
        top_card = QtWidgets.QFrame()
        top_card.setObjectName("Card")
        top_lay = QtWidgets.QHBoxLayout(top_card)
        top_lay.setContentsMargins(18, 14, 18, 14)
        top_lay.setSpacing(16)

        self._kpi_labels: Dict[str, QtWidgets.QLabel] = {}
        for key, label in (("passed", "Passed"), ("warn", "Warnings"), ("failed", "Failed"), ("total", "Completed")):
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(0)
            val = QtWidgets.QLabel("0")
            val.setStyleSheet("font-size: 18px; font-weight: 800;")
            lbl = QtWidgets.QLabel(label)
            lbl.setObjectName("MutedLabel")
            col.addWidget(val)
            col.addWidget(lbl)
            top_lay.addLayout(col)
            self._kpi_labels[key] = val

        top_lay.addStretch()

        for text, slot, obj_name in (
            ("Preview PDF", self.generate_and_preview_pdf, "PrimaryButton"),
            ("Save to USB", self.export_usb, "SecondaryButton"),
            ("Save to SD Boot", self.export_sd, "SecondaryButton"),
            ("Share QR", self.export_qr, "SecondaryButton"),
            ("Clear", self.clear_results, "DangerButton"),
        ):
            btn = QtWidgets.QPushButton(text)
            btn.setObjectName(obj_name)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            btn.clicked.connect(slot)
            top_lay.addWidget(btn)

        layout.addWidget(top_card)

        # Scrollable results list
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.results_widget = QtWidgets.QWidget()
        self.results_layout = QtWidgets.QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(12)
        scroll.setWidget(self.results_widget)
        layout.addWidget(scroll, stretch=1)

        self._update_results_display()
        return page

    # -----------------------------------------------------------------------
    # Page 4: Settings
    # -----------------------------------------------------------------------

    def _create_settings_page(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(16)

        # Appearance card
        appear = QtWidgets.QFrame()
        appear.setObjectName("Card")
        ap_lay = QtWidgets.QHBoxLayout(appear)
        ap_lay.setContentsMargins(20, 16, 20, 16)
        ap_txt = QtWidgets.QVBoxLayout()
        ap_title = QtWidgets.QLabel("Appearance")
        ap_title.setObjectName("SectionHeading")
        ap_desc = QtWidgets.QLabel("Switch between Dark hardware-lab mode and Light mode.")
        ap_desc.setObjectName("MutedLabel")
        ap_txt.addWidget(ap_title)
        ap_txt.addWidget(ap_desc)
        ap_lay.addLayout(ap_txt)
        ap_lay.addStretch()

        self._dark_btn = QtWidgets.QPushButton("Dark Mode")
        self._dark_btn.setObjectName("FilterPill")
        self._dark_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._dark_btn.clicked.connect(lambda: self._apply_theme("dark"))
        ap_lay.addWidget(self._dark_btn)

        self._light_btn = QtWidgets.QPushButton("Light Mode")
        self._light_btn.setObjectName("FilterPill")
        self._light_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._light_btn.clicked.connect(lambda: self._apply_theme("light"))
        ap_lay.addWidget(self._light_btn)
        layout.addWidget(appear)

        # Network card
        net_card = QtWidgets.QFrame()
        net_card.setObjectName("Card")
        net_lay = QtWidgets.QVBoxLayout(net_card)
        net_lay.setContentsMargins(20, 18, 20, 18)
        net_lay.setSpacing(10)

        net_hdr = QtWidgets.QHBoxLayout()
        net_t = QtWidgets.QLabel("Network & Wi-Fi")
        net_t.setObjectName("SectionHeading")
        net_hdr.addWidget(net_t)
        net_hdr.addStretch()

        ref_btn = QtWidgets.QPushButton("Refresh")
        ref_btn.setObjectName("SecondaryButton")
        ref_btn.clicked.connect(self._refresh_network_info)
        net_hdr.addWidget(ref_btn)

        wifi_btn = QtWidgets.QPushButton("Connect to Wi-Fi…")
        wifi_btn.setObjectName("PrimaryButton")
        wifi_btn.clicked.connect(self.open_wifi_dialog)
        net_hdr.addWidget(wifi_btn)
        net_lay.addLayout(net_hdr)

        self.network_info_text = QtWidgets.QTextEdit()
        self.network_info_text.setReadOnly(True)
        self.network_info_text.setMinimumHeight(170)
        self.network_info_text.setMaximumHeight(220)
        self.network_info_text.setStyleSheet("font-family: monospace; font-size: 12px;")
        net_lay.addWidget(self.network_info_text)
        layout.addWidget(net_card)

        # System & Power card
        sys_card = QtWidgets.QFrame()
        sys_card.setObjectName("Card")
        sys_lay = QtWidgets.QVBoxLayout(sys_card)
        sys_lay.setContentsMargins(20, 18, 20, 18)
        sys_lay.setSpacing(10)
        st = QtWidgets.QLabel("System, Reports & Power")
        st.setObjectName("SectionHeading")
        sd = QtWidgets.QLabel(f"Apple Pi Diagnostics {APP_VERSION}  ·  Reports folder: {REPORT_DIR}")
        sd.setObjectName("MutedLabel")
        sys_lay.addWidget(st)
        sys_lay.addWidget(sd)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)
        open_dir_btn = QtWidgets.QPushButton("Open Reports Folder")
        open_dir_btn.setObjectName("SecondaryButton")
        open_dir_btn.clicked.connect(lambda: self._open_file_location(REPORT_DIR / "report.pdf"))
        btn_row.addWidget(open_dir_btn)

        rb = QtWidgets.QPushButton("Reboot Device")
        rb.setObjectName("SecondaryButton")
        rb.clicked.connect(lambda: self._confirm_system_power("reboot"))
        btn_row.addWidget(rb)

        sd_btn = QtWidgets.QPushButton("Shut Down Device")
        sd_btn.setObjectName("DangerButton")
        sd_btn.clicked.connect(lambda: self._confirm_system_power("poweroff"))
        btn_row.addWidget(sd_btn)
        btn_row.addStretch()
        sys_lay.addLayout(btn_row)
        layout.addWidget(sys_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # -----------------------------------------------------------------------
    # Navigation & Theming
    # -----------------------------------------------------------------------

    def _switch_page(self, index: int):
        self.pages.setCurrentIndex(index)
        title, subtitle = _PAGE_META[index]
        self._top_title.setText(title)
        self._top_subtitle.setText(subtitle)
        t = THEMES[self.theme_name]
        for idx, (btn, icon_key) in enumerate(self._nav_buttons):
            active = idx == index
            btn.setProperty("active", active)
            btn.setIcon(make_svg_icon(icon_key, 17, t["accent"] if active else t["text_secondary"]))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def toggle_theme(self):
        self._apply_theme("light" if self.theme_name == "dark" else "dark")

    def _apply_theme(self, theme_name: str = "dark"):
        self.theme_name = theme_name if theme_name in THEMES else "dark"
        t = THEMES[self.theme_name]
        self.setStyleSheet(build_stylesheet(self.theme_name))

        # Update top-bar & sidebar icons
        self.run_all_btn.setIcon(make_svg_icon("play", 14, "#ffffff"))
        self.qr_btn.setIcon(make_svg_icon("qr", 15, t["text"]))
        self._sidebar_reboot_btn.setIcon(make_svg_icon("reboot", 14, t["text"]))
        self._sidebar_shutdown_btn.setIcon(make_svg_icon("shutdown", 14, t["danger"]))

        if self.theme_name == "dark":
            self._theme_btn.setText("  Light Mode")
            self._theme_btn.setIcon(make_svg_icon("sun", 15, t["warning"]))
        else:
            self._theme_btn.setText("  Dark Mode")
            self._theme_btn.setIcon(make_svg_icon("moon", 15, t["accent"]))

        self._dark_btn.setProperty("active", self.theme_name == "dark")
        self._light_btn.setProperty("active", self.theme_name == "light")
        for b in (self._dark_btn, self._light_btn):
            b.style().unpolish(b)
            b.style().polish(b)

        # Refresh nav icons
        self._switch_page(self.pages.currentIndex())

        # Refresh custom painted widgets
        self.health_ring.set_theme(self.theme_name)
        for tile in self._telemetry_tiles.values():
            tile.set_theme(self.theme_name)
        for card in self.test_cards.values():
            card.set_theme(self.theme_name)
        for card in self._tool_cards:
            card.set_theme(self.theme_name)
        self._update_results_display()
        if self._startup_results:
            self.show_startup_banner(self._startup_results)

    # -----------------------------------------------------------------------
    # System Info, Live Telemetry & Startup Checks
    # -----------------------------------------------------------------------

    def _update_system_info(self):
        try:
            hostname = socket.gethostname()
            pi_model = "Generic Linux Host"
            model_path = Path("/proc/device-tree/model")
            if model_path.is_file():
                pi_model = model_path.read_text(errors="ignore").strip("\x00\n") or pi_model

            os_pretty = f"{platform.system()} {platform.release()}"
            os_rel = Path("/etc/os-release")
            if os_rel.is_file():
                for ln in os_rel.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if ln.startswith("PRETTY_NAME="):
                        os_pretty = ln.split("=", 1)[1].strip().strip('"')
                        break

            items = [
                ("App Version", APP_VERSION),
                ("Device", pi_model),
                ("Hostname", hostname),
                ("Operating System", os_pretty),
                ("Architecture", platform.machine()),
                ("Python", platform.python_version()),
            ]

            while self.sys_info_layout.count():
                item = self.sys_info_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            for r, (k, v) in enumerate(items):
                k_lbl = QtWidgets.QLabel(k)
                k_lbl.setObjectName("KeyLabel")
                v_lbl = QtWidgets.QLabel(v)
                v_lbl.setObjectName("ValueLabel")
                v_lbl.setWordWrap(True)
                self.sys_info_layout.addWidget(k_lbl, r, 0)
                self.sys_info_layout.addWidget(v_lbl, r, 1)
            self.sys_info_layout.setColumnStretch(1, 1)
        except Exception as e:
            self.statusBar().showMessage(f"Error loading system info: {e}")

    def _update_live_telemetry(self):
        if not hasattr(self, "_telemetry_tiles"):
            return
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=None)
            cpu_tone = "danger" if cpu_pct >= 85 else "warning" if cpu_pct >= 65 else "accent"
            cores = psutil.cpu_count(logical=True) or 1
            self._telemetry_tiles["cpu"].update_metric(
                f"{cpu_pct:.0f}%", f"{cores} logical cores", int(cpu_pct), cpu_tone
            )

            mem = psutil.virtual_memory()
            mem_tone = "danger" if mem.percent >= 88 else "warning" if mem.percent >= 72 else "success"
            self._telemetry_tiles["ram"].update_metric(
                f"{mem.percent:.0f}%",
                f"{mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB used",
                int(mem.percent),
                mem_tone,
            )

            tz = Path("/sys/class/thermal/thermal_zone0/temp")
            if tz.is_file():
                try:
                    t_c = int(tz.read_text(encoding="utf-8").strip()) / 1000.0
                    t_tone = "danger" if t_c >= 80 else "warning" if t_c >= 70 else "success"
                    self._telemetry_tiles["temp"].update_metric(
                        f"{t_c:.1f} °C",
                        "Hot — check cooling" if t_c >= 75 else "Normal thermal range",
                        int(min(100, t_c)),
                        t_tone,
                    )
                except Exception:
                    self._telemetry_tiles["temp"].update_metric("N/A", "Sensor unreadable", 0, "accent")
            else:
                self._telemetry_tiles["temp"].update_metric("N/A", "No thermal zone", 0, "accent")

            t_path = Path("/sys/devices/platform/soc/soc:firmware/get_throttled")
            if t_path.is_file():
                try:
                    raw = int(t_path.read_text(encoding="utf-8").strip(), 16)
                    if raw == 0:
                        self._telemetry_tiles["power"].update_metric("Healthy", "No throttling (0x0)", 100, "success")
                    elif raw & 0xF:
                        self._telemetry_tiles["power"].update_metric(
                            "Throttled", f"Active issue ({hex(raw)})", 100, "danger"
                        )
                    else:
                        self._telemetry_tiles["power"].update_metric(
                            "Warning", f"Past event ({hex(raw)})", 70, "warning"
                        )
                except Exception:
                    self._telemetry_tiles["power"].update_metric("N/A", "Firmware flag unreadable", 0, "accent")
            else:
                self._telemetry_tiles["power"].update_metric("Non-Pi", "Firmware telemetry N/A", 0, "accent")
        except Exception:
            pass

    def show_startup_banner(self, results: List[Dict[str, Any]]):
        """Render pre-boot check results inside the Dashboard Pre-Boot card."""
        if not results or not hasattr(self, "_overview_checks_layout"):
            return
        self._startup_results = results
        t = THEMES[self.theme_name]

        while self._overview_checks_layout.count():
            item = self._overview_checks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        passed = sum(1 for r in results if r.get("passed"))
        total = len(results)
        all_ok = passed == total

        pill = QtWidgets.QLabel(
            f"{'✓' if all_ok else '⚠'}  {passed} of {total} pre-boot checks passed"
        )
        pill_fg = t["success"] if all_ok else t["warning"]
        pill_bg = t["success_soft"] if all_ok else t["warning_soft"]
        pill.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {pill_fg}; "
            f"background-color: {pill_bg}; border-radius: 8px; padding: 6px 12px;"
        )
        self._overview_checks_layout.addWidget(pill)

        for r in results:
            ok = bool(r.get("passed"))
            row = QtWidgets.QWidget()
            r_lay = QtWidgets.QHBoxLayout(row)
            r_lay.setContentsMargins(4, 2, 4, 2)
            r_lay.setSpacing(8)
            ic = QtWidgets.QLabel("✓" if ok else "⚠")
            ic.setStyleSheet(f"color: {t['success'] if ok else t['warning']}; font-weight: 700;")
            ic.setFixedWidth(16)
            nm = QtWidgets.QLabel(r.get("name", ""))
            nm.setStyleSheet("font-size: 12px; font-weight: 600;")
            dt = QtWidgets.QLabel(r.get("detail", ""))
            dt.setObjectName("MutedLabel")
            dt.setWordWrap(True)
            r_lay.addWidget(ic)
            r_lay.addWidget(nm)
            r_lay.addWidget(dt, stretch=1)
            self._overview_checks_layout.addWidget(row)

    # -----------------------------------------------------------------------
    # Diagnostics Execution
    # -----------------------------------------------------------------------

    def run_test(self, test_id: str):
        """Run a single diagnostic module off the Qt event loop."""
        card = self.test_cards.get(test_id)
        if not card or test_id in self._running_tests:
            return

        self._running_tests.add(test_id)
        card.test_btn.setEnabled(False)
        card.set_status("RUNNING", "Running diagnostic…")
        self._update_health_summary()
        self.statusBar().showMessage(f"Running {_TEST_LABELS.get(test_id, test_id)} test…")

        def _worker():
            try:
                runners = {
                    "cpu": lambda: run_cpu_quick_test(duration=5, workers=None),
                    "ram": lambda: run_ram_quick_test(total_mb=64, chunk_mb=16, passes=1),
                    "sd": run_storage_quick_test,
                    "power": run_power_quick_test,
                    "network": run_network_quick_test,
                    "usb": run_usb_quick_test,
                    "hdmi": run_hdmi_quick_test,
                    "gpio": run_gpio_quick_test,
                    "bootloader": run_bootloader_quick_test,
                    "peripherals": run_peripherals_quick_test,
                }
                fn = runners.get(test_id)
                result = fn() if fn else {"status": "UNSUPPORTED", "note": "Unknown test"}
            except Exception as e:
                result = {"status": "FAIL", "error": str(e), "note": str(e)}

            result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sig_test_finished.emit(test_id, result)

        threading.Thread(target=_worker, daemon=True).start()

    @QtCore.pyqtSlot(str, dict)
    def _on_test_finished(self, test_id: str, result: Dict[str, Any]):
        self._running_tests.discard(test_id)
        with self.results_lock:
            self.test_results[test_id] = result

        card = self.test_cards.get(test_id)
        if card:
            status = result.get("status", "UNKNOWN")
            details = self._short_card_detail(result)
            card.set_status(status, details)
            card.test_btn.setEnabled(True)

        self._update_health_summary()
        self._update_results_display()
        self.statusBar().showMessage(
            f"{_TEST_LABELS.get(test_id, test_id)} completed ({result.get('status', '?')})",
            4000,
        )

    def _short_card_detail(self, result: Dict[str, Any]) -> str:
        if result.get("note"):
            return str(result["note"])
        if "avg_cpu_percent" in result:
            temp = result.get("max_temperature")
            t_str = f" · {temp:.0f}°C" if temp is not None else ""
            return f"Avg load {result['avg_cpu_percent']:.1f}%{t_str}"
        if "tested_mb" in result:
            tp = result.get("throughput_mb_s")
            return f"{result['tested_mb']:.0f} MB verified" + (f" · {tp:.0f} MB/s" if tp else "")
        if "total_devices" in result:
            return f"{result.get('tested_devices', 0)}/{result.get('total_devices', 0)} devices tested"
        if "local_ip" in result:
            return f"IP: {result.get('local_ip') or 'Offline'}"
        if "count" in result:
            return f"{result['count']} detected"
        return result.get("error", "")

    def run_all_tests(self):
        """Stagger-launch all 10 diagnostics without blocking the Qt UI thread."""
        self._switch_page(1)
        self._suite_progress.setValue(0)
        self._suite_progress.setVisible(True)
        self.statusBar().showMessage("Running full hardware diagnostic suite…")
        for idx, (test_id, *_rest) in enumerate(_DIAGNOSTIC_SPECS):
            QtCore.QTimer.singleShot(idx * 150, lambda tid=test_id: self.run_test(tid))

    def _update_health_summary(self):
        with self.results_lock:
            snap = dict(self.test_results)

        total = len(_DIAGNOSTIC_SPECS)
        passed = sum(1 for r in snap.values() if r.get("status", "").upper() in ("OK", "PASS"))
        failed = sum(1 for r in snap.values() if r.get("status", "").upper() in ("FAIL", "ERROR"))
        warnings = sum(1 for r in snap.values() if r.get("status", "").upper() in ("WARNING", "UNSUPPORTED"))
        completed = len(snap)

        self.health_ring.set_counts(passed, warnings, failed, total)

        if self._running_tests:
            self._suite_progress.setVisible(True)
            self._suite_progress.setValue(completed)
            self._hero_heading.setText(f"Running Diagnostics ({completed}/{total})…")
            self._hero_detail.setText(
                f"Active: {', '.join(_TEST_LABELS.get(x, x) for x in sorted(self._running_tests))}"
            )
        else:
            self._suite_progress.setVisible(False)
            if completed == 0:
                self._hero_heading.setText("System Ready for Diagnostics")
                self._hero_detail.setText(
                    "Run the full 10-module hardware verification suite or pick individual checks in Diagnostics."
                )
            elif failed > 0:
                self._hero_heading.setText(f"{failed} Hardware Issue{'s' if failed != 1 else ''} Detected")
                self._hero_detail.setText(
                    f"{passed} passed, {warnings} warnings/unsupported, {failed} failed across {completed} completed tests."
                )
            elif warnings > 0:
                self._hero_heading.setText(f"Completed with {warnings} Note{'s' if warnings != 1 else ''}")
                self._hero_detail.setText(
                    f"{passed} passed and {warnings} warning/unsupported items. Open Results & Export for details."
                )
            else:
                self._hero_heading.setText("All Executed Checks Healthy")
                self._hero_detail.setText(
                    f"{passed} of {completed} completed hardware checks passed with zero issues."
                )

        if hasattr(self, "_kpi_labels"):
            t = THEMES[self.theme_name]
            self._kpi_labels["passed"].setText(str(passed))
            self._kpi_labels["passed"].setStyleSheet(f"font-size: 18px; font-weight: 800; color: {t['success']};")
            self._kpi_labels["warn"].setText(str(warnings))
            self._kpi_labels["warn"].setStyleSheet(f"font-size: 18px; font-weight: 800; color: {t['warning']};")
            self._kpi_labels["failed"].setText(str(failed))
            self._kpi_labels["failed"].setStyleSheet(f"font-size: 18px; font-weight: 800; color: {t['danger']};")
            self._kpi_labels["total"].setText(f"{completed}/{total}")

    def clear_results(self):
        with self.results_lock:
            self.test_results.clear()
        for card in self.test_cards.values():
            card.set_status("PENDING", "")
        self._update_health_summary()
        self._update_results_display()
        self.statusBar().showMessage("Results cleared", 3000)

    # -----------------------------------------------------------------------
    # Results Rendering
    # -----------------------------------------------------------------------

    def _summarize_result(self, test_id: str, result: Dict[str, Any]) -> List[str]:
        from diagnostics.report_builder import _summarize_test
        return _summarize_test(test_id, result)

    def _update_results_display(self):
        if not hasattr(self, "results_layout"):
            return
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        with self.results_lock:
            results_copy = deepcopy(self.test_results)

        if not results_copy:
            empty = QtWidgets.QFrame()
            empty.setObjectName("Card")
            e_lay = QtWidgets.QVBoxLayout(empty)
            e_lay.setContentsMargins(32, 48, 32, 48)
            e_lbl = QtWidgets.QLabel("No test results yet")
            e_lbl.setAlignment(QtCore.Qt.AlignCenter)
            e_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
            e_sub = QtWidgets.QLabel("Run individual modules or click 'Run All Tests' to generate results and PDF/QR reports.")
            e_sub.setAlignment(QtCore.Qt.AlignCenter)
            e_sub.setObjectName("MutedLabel")
            e_lay.addWidget(e_lbl)
            e_lay.addWidget(e_sub)
            self.results_layout.addWidget(empty)
        else:
            t = THEMES[self.theme_name]
            for test_id, result in results_copy.items():
                card = QtWidgets.QFrame()
                card.setObjectName("Card")
                c_lay = QtWidgets.QVBoxLayout(card)
                c_lay.setContentsMargins(18, 14, 18, 14)
                c_lay.setSpacing(8)

                hdr = QtWidgets.QHBoxLayout()
                title = QtWidgets.QLabel(_TEST_LABELS.get(test_id, test_id.upper()))
                title.setStyleSheet("font-size: 15px; font-weight: 700;")
                hdr.addWidget(title)
                hdr.addStretch()

                status = result.get("status", "UNKNOWN").upper()
                if status in ("OK", "PASS"):
                    fg, bg, badge_txt = t["success"], t["success_soft"], "✓ Passed"
                elif status in ("FAIL", "ERROR"):
                    fg, bg, badge_txt = t["danger"], t["danger_soft"], "✗ Failed"
                elif status == "WARNING":
                    fg, bg, badge_txt = t["warning"], t["warning_soft"], "⚠ Warning"
                elif status == "UNSUPPORTED":
                    fg, bg, badge_txt = t["warning"], t["warning_soft"], "— Unsupported"
                else:
                    fg, bg, badge_txt = t["text_secondary"], t["neutral_soft"], "○ Unknown"

                pill = QtWidgets.QLabel(badge_txt)
                pill.setStyleSheet(
                    f"font-size: 11px; font-weight: 700; color: {fg}; "
                    f"background-color: {bg}; border-radius: 10px; padding: 3px 10px;"
                )
                hdr.addWidget(pill)
                c_lay.addLayout(hdr)

                body = QtWidgets.QLabel("\n".join(self._summarize_result(test_id, result)))
                body.setWordWrap(True)
                body.setObjectName("ValueLabel")
                c_lay.addWidget(body)

                ts = QtWidgets.QLabel(f"Tested: {result.get('timestamp', '')}")
                ts.setObjectName("MutedLabel")
                c_lay.addWidget(ts)
                self.results_layout.addWidget(card)

        self.results_layout.addStretch()

    # -----------------------------------------------------------------------
    # Reports & Exports
    # -----------------------------------------------------------------------

    def _build_report_payload(self) -> Dict[str, Any]:
        with self.results_lock:
            results_copy = deepcopy(self.test_results)
        summary = {}
        for test_id, result in results_copy.items():
            summary[test_id] = {
                "status": result.get("status", "UNKNOWN"),
                "message": result.get("note", result.get("error", "")),
                "metrics": {
                    k: v for k, v in result.items() if k not in ("status", "note", "error", "timestamp")
                },
            }
        return {
            "title": "Apple Pi Diagnostics Report",
            "summary": summary,
            "details": results_copy,
        }

    def generate_and_preview_pdf(self):
        if not self.test_results:
            self.statusBar().showMessage("No test results to report. Run tests first.", 3000)
            return
        self.statusBar().showMessage("Generating PDF report…")
        try:
            paths = build_report(self._build_report_payload(), REPORT_DIR, formats=("pdf", "html", "json"))
            self.latest_report_dir = REPORT_DIR
            pdf_path = paths.get("pdf")
            if pdf_path:
                self._show_pdf_preview(pdf_path)
            else:
                self.statusBar().showMessage("Failed to generate PDF", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error generating report: {e}", 4000)

    def _show_pdf_preview(self, pdf_path: Path):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"Report Preview — Apple Pi Diagnostics {APP_VERSION}")
        dialog.setMinimumSize(820, 620)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setSpacing(12)

        preview = QtWidgets.QTextBrowser()
        preview.setReadOnly(True)
        html_path = pdf_path.with_suffix(".html")
        if html_path.is_file():
            preview.setHtml(html_path.read_text(encoding="utf-8"))
        else:
            preview.setPlainText(f"PDF generated at: {pdf_path}")
        layout.addWidget(preview)

        btn_row = QtWidgets.QHBoxLayout()
        for label, handler, style_id in (
            ("Save to USB Drive", lambda: self._save_pdf_to_usb(pdf_path, dialog), "PrimaryButton"),
            ("Save to SD Boot", self.export_sd, "SecondaryButton"),
            ("Share via QR", self.export_qr, "SecondaryButton"),
            ("Open Folder", lambda: self._open_file_location(pdf_path), "SecondaryButton"),
        ):
            b = QtWidgets.QPushButton(label)
            b.setObjectName(style_id)
            b.clicked.connect(handler)
            btn_row.addWidget(b)
        btn_row.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec_()

    def _save_pdf_to_usb(self, pdf_path: Path, dialog: QtWidgets.QDialog):
        dialog.setEnabled(False)
        temp_dir = None
        try:
            temp_dir = Path(tempfile.mkdtemp())
            shutil.copy2(pdf_path, temp_dir / pdf_path.name)
            result = save_report_to_usb(temp_dir)
            if result:
                QtWidgets.QMessageBox.information(dialog, "Saved to USB", f"Report saved to:\n{result}")
                dialog.accept()
            else:
                QtWidgets.QMessageBox.warning(
                    dialog, "No USB Drive", "No writable USB drive detected. Insert a USB drive and try again."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(dialog, "Export Error", f"Failed to save to USB: {e}")
        finally:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            dialog.setEnabled(True)

    def generate_report(self):
        if not self.test_results:
            self.statusBar().showMessage("No test results to report. Run tests first.", 3000)
            return
        try:
            paths = build_report(self._build_report_payload(), REPORT_DIR, formats=("pdf", "html", "json", "qr"))
            self.latest_report_dir = REPORT_DIR
            self.statusBar().showMessage(f"Report generated ({len(paths)} files)", 4000)
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}", 4000)

    def export_usb(self):
        if not self.latest_report_dir and self.test_results:
            self.generate_report()
        res = save_report_to_usb(self.latest_report_dir or REPORT_DIR)
        if res:
            QtWidgets.QMessageBox.information(self, "Saved to USB", f"Reports saved to:\n{res}")
            self.statusBar().showMessage(f"Saved to USB: {res}", 5000)
        else:
            QtWidgets.QMessageBox.warning(
                self, "No USB Drive", "No mounted or automountable USB flash drive detected."
            )

    def export_sd(self):
        if not self.latest_report_dir and self.test_results:
            self.generate_report()
        res = save_report_to_sdboot(self.latest_report_dir or REPORT_DIR)
        if res:
            QtWidgets.QMessageBox.information(self, "Saved to SD Boot", f"Reports saved to:\n{res}")
            self.statusBar().showMessage(f"Saved to SD boot: {res}", 5000)
        else:
            QtWidgets.QMessageBox.warning(
                self, "SD Boot Unavailable", "Could not write to /boot/firmware or /boot."
            )

    def export_qr(self):
        if not self.latest_report_dir and self.test_results:
            self.generate_report()
        try:
            if self.qr_manager:
                self.qr_manager.stop()
            self.qr_manager = QRExportManager(self.latest_report_dir or REPORT_DIR)
            url = self.qr_manager.start()
            qr_path = REPORT_DIR / "qrs" / "report_qr.png"
            generate_qr_image(url, qr_path)
            self.statusBar().showMessage(f"Serving reports at {url}", 5000)
            QrPreviewDialog(url, qr_path, self).exec_()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "QR Export Error", str(e))

    # -----------------------------------------------------------------------
    # Network Info, Interactive Tools & Device Power
    # -----------------------------------------------------------------------

    def _refresh_network_info(self):
        if not hasattr(self, "network_info_text"):
            return
        try:
            import psutil
            if_stats = psutil.net_if_stats()
            if_addrs = psutil.net_if_addrs()
            lines = ["Interfaces:"]
            for name, st in if_stats.items():
                if name == "lo":
                    continue
                lines.append(f"  {name}: {'UP' if st.isup else 'DOWN'}")
                for addr in if_addrs.get(name, []):
                    if getattr(addr, "address", None):
                        fam = "IPv4" if addr.family == socket.AF_INET else "IPv6" if addr.family == socket.AF_INET6 else "MAC"
                        lines.append(f"    {fam}: {addr.address}")

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect((GATEWAY_PROBE_HOST, GATEWAY_PROBE_PORT))
                local_ip = s.getsockname()[0]
                s.close()
                lines.append(f"\nDefault Route IP: {local_ip}")
            except Exception:
                lines.append("\nDefault Route IP: Offline / LAN only")

            try:
                t0 = time.time()
                socket.gethostbyname(NETWORK_DNS_CHECK_HOST)
                lines.append(f"DNS ({NETWORK_DNS_CHECK_HOST}): OK ({(time.time() - t0) * 1000:.0f} ms)")
            except Exception as e:
                lines.append(f"DNS ({NETWORK_DNS_CHECK_HOST}): Failed ({e})")

            self.network_info_text.setPlainText("\n".join(lines))
        except Exception as e:
            self.network_info_text.setPlainText(f"Error loading network info: {e}")

    def open_hdmi_pattern(self):
        HdmiPatternDialog(self).exec_()

    def open_gpio_viewer(self):
        GpioPinoutDialog(self).exec_()

    def open_wifi_dialog(self):
        WifiConnectDialog(self).exec_()
        self._refresh_network_info()

    def _open_file_location(self, file_path: Path):
        try:
            if platform.system() == "Linux":
                subprocess.Popen(["xdg-open", str(file_path.parent)])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(file_path.parent)])
            elif platform.system() == "Windows":
                subprocess.Popen(["explorer", "/select,", str(file_path)])
        except Exception:
            pass

    def _confirm_system_power(self, action: str):
        label = "Reboot" if action == "reboot" else "Shut Down"
        reply = QtWidgets.QMessageBox.question(
            self,
            f"Confirm {label}",
            f"Are you sure you want to {label.lower()} this device?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        try:
            subprocess.Popen(["systemctl", action])
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, f"{label} Failed", str(e))

    def closeEvent(self, event):
        if hasattr(self, "_telemetry_timer") and self._telemetry_timer:
            self._telemetry_timer.stop()
        if self.qr_manager:
            self.qr_manager.stop()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    startup_check_results = []
    try:
        from gui.splash import SplashScreen
        splash = SplashScreen()
        startup_check_results = splash.exec_and_wait() or []
    except Exception:
        pass

    window = MainWindow()
    if os.environ.get("APD_KIOSK") == "1":
        window.showMaximized()
    else:
        window.show()
    if startup_check_results:
        window.show_startup_banner(startup_check_results)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
