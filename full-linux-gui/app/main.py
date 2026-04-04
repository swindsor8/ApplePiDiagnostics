#!/usr/bin/env python3
"""
Apple Pi Diagnostics - Full Linux GUI (ASUS MyASus-style Dashboard)
Run: source ../venv/bin/activate && python3 main.py
"""
import sys
import platform
import socket
import threading
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from PyQt5 import QtWidgets, QtCore, QtGui
from exports.export_usb import save_report_to_usb
from exports.export_sd_boot import save_report_to_sdboot
from exports.export_qr import QRExportManager, generate_qr_image
from diagnostics.report_builder import build_report
from diagnostics.cpu.cpu_test import run_cpu_quick_test
from diagnostics.ram.ram_test import run_ram_quick_test
from diagnostics.network.network_test import run_network_quick_test
from diagnostics.storage.storage_test import run_storage_quick_test
from diagnostics.usb.usb_test import run_usb_quick_test
from diagnostics.hdmi.hdmi_test import run_hdmi_quick_test
from diagnostics.gpio.gpio_test import run_gpio_quick_test

# Try to reuse the splash module's logo discovery so the app icon matches the splash
try:
    from gui.splash import LOGO_PATH
except Exception:
    LOGO_PATH = None

APP_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = APP_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# SVG icon helpers
# ---------------------------------------------------------------------------

# Feather-style SVG icons — stroke-based, colour driven by `currentColor`
_SVG_ICONS = {
    "cpu": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="4" y="4" width="16" height="16" rx="2"/>
        <rect x="9" y="9" width="6" height="6"/>
        <line x1="9" y1="1" x2="9" y2="4"/>
        <line x1="15" y1="1" x2="15" y2="4"/>
        <line x1="9" y1="20" x2="9" y2="23"/>
        <line x1="15" y1="20" x2="15" y2="23"/>
        <line x1="20" y1="9" x2="23" y2="9"/>
        <line x1="20" y1="14" x2="23" y2="14"/>
        <line x1="1" y1="9" x2="4" y2="9"/>
        <line x1="1" y1="14" x2="4" y2="14"/>
    </svg>""",

    "ram": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="8" width="20" height="8" rx="2"/>
        <line x1="6" y1="8" x2="6" y2="16"/>
        <line x1="10" y1="8" x2="10" y2="16"/>
        <line x1="14" y1="8" x2="14" y2="16"/>
        <line x1="18" y1="8" x2="18" y2="16"/>
        <line x1="6" y1="5" x2="6" y2="8"/>
        <line x1="10" y1="5" x2="10" y2="8"/>
        <line x1="14" y1="5" x2="14" y2="8"/>
        <line x1="18" y1="5" x2="18" y2="8"/>
    </svg>""",

    "sd": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M3 5v5c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/>
        <path d="M3 10v5c0 1.66 4.03 3 9 3s9-1.34 9-3v-5"/>
        <path d="M3 15v4c0 1.66 4.03 3 9 3s9-1.34 9-3v-4"/>
    </svg>""",

    "network": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10
                 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>""",

    "usb": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2v11"/>
        <polyline points="8 6 12 2 16 6"/>
        <circle cx="8" cy="17" r="2"/>
        <circle cx="16" cy="15" r="2"/>
        <path d="M12 13H8a2 2 0 0 0-2 2v2"/>
        <path d="M12 13h4a2 2 0 0 0 2-2v-2"/>
    </svg>""",

    "hdmi": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="3" width="20" height="13" rx="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="16" x2="12" y2="21"/>
    </svg>""",

    "gpio": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <line x1="12" y1="2" x2="12" y2="9"/>
        <line x1="12" y1="15" x2="12" y2="22"/>
        <line x1="2" y1="12" x2="9" y2="12"/>
        <line x1="15" y1="12" x2="22" y2="12"/>
        <line x1="4.22" y1="4.22" x2="6.34" y2="6.34"/>
        <line x1="17.66" y1="17.66" x2="19.78" y2="19.78"/>
    </svg>""",

    "sun": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/>
        <line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/>
        <line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>""",

    "moon": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>""",

    "refresh": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="23 4 23 10 17 10"/>
        <polyline points="1 20 1 14 7 14"/>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>""",

    "save": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
        <polyline points="17 21 17 13 7 13 7 21"/>
        <polyline points="7 3 7 8 15 8"/>
    </svg>""",

    "folder": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
    </svg>""",
}


def _make_svg_pixmap(icon_key, size=20, color="#888888"):
    """Render a named SVG icon to a QPixmap at the requested size and colour."""
    svg_str = _SVG_ICONS.get(icon_key, "")
    if not svg_str:
        return None
    try:
        from PyQt5 import QtSvg
        colored = svg_str.replace("currentColor", color)
        renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(colored.encode()))
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap
    except Exception:
        return None


class StatusCard(QtWidgets.QWidget):
    """Card widget for displaying diagnostic test status (ASUS MyASus style)"""
    
    def __init__(self, title, icon_key="cpu", parent=None):
        super().__init__(parent)
        self.title = title
        self.icon_key = icon_key
        self.status = "PENDING"
        self.details = ""
        self._build_ui()

    def _build_ui(self):
        self.setFixedSize(200, 160)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Icon and title
        header = QtWidgets.QHBoxLayout()
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(22, 22)
        self.set_icon_color("#888888")
        header.addWidget(self.icon_label)
        
        title_label = QtWidgets.QLabel(self.title)
        title_label.setObjectName("card_title")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Status indicator
        self.status_label = QtWidgets.QLabel("Pending")
        self.status_label.setObjectName("card_status")
        layout.addWidget(self.status_label)
        
        # Details
        self.details_label = QtWidgets.QLabel("")
        self.details_label.setObjectName("card_details")
        self.details_label.setWordWrap(True)
        layout.addWidget(self.details_label)
        
        layout.addStretch()
        
        # Test button
        self.test_btn = QtWidgets.QPushButton("Test")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.test_btn)
        
    @QtCore.pyqtSlot(str, str)
    def set_status(self, status, details=""):
        """Update status with color coding"""
        self.status = status
        self.details = details
        
        if status == "OK" or status == "PASS":
            color = "#10b981"  # Green
            text = "✓ Normal"
        elif status == "FAIL" or status == "ERROR":
            color = "#ef4444"  # Red
            text = "✗ Failed"
        elif status == "UNSUPPORTED":
            color = "#f59e0b"  # Orange
            text = "— Unsupported"
        elif status == "RUNNING":
            color = "#3b82f6"  # Blue
            text = "⟳ Running..."
        else:
            color = "#6b7280"  # Gray
            text = "○ Pending"
            
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {color};
            font-weight: 600;
        """)
        
        if details:
            self.details_label.setText(details[:50] + "..." if len(details) > 50 else details)
        else:
            self.details_label.setText("")

    def set_icon_color(self, color):
        """Re-render the card icon in the given colour."""
        pixmap = _make_svg_pixmap(self.icon_key, size=22, color=color)
        if pixmap:
            self.icon_label.setPixmap(pixmap)


class MainWindow(QtWidgets.QMainWindow):
    sig_append = QtCore.pyqtSignal(str)
    sig_set_button_enabled = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.latest_report_dir = None
        self.qr_manager = None
        self.test_cards = {}
        self.overview_cards = {}
        self.test_results = {}
        self.results_lock = threading.Lock()
        self.sys_info_card = None
        self.sys_info_labels = []
        self.setWindowTitle("Apple Pi Diagnostics")
        self.setMinimumSize(1000, 700)
        self._build_ui()
        if LOGO_PATH and Path(LOGO_PATH).exists():
            self.setWindowIcon(QtGui.QIcon(str(LOGO_PATH)))
        
        # Load system info
        self._update_system_info()

    def _build_ui(self):
        # Central widget with main layout
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header bar (ASUS MyASus style)
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Create tab widget for pages
        self.tabs = QtWidgets.QTabWidget()
        self._update_tab_style()
        
        # Overview page
        overview_page = self._create_overview_page()
        self.tabs.addTab(overview_page, "Overview")
        
        # Testing page
        testing_page = self._create_testing_page()
        self.tabs.addTab(testing_page, "Testing")
        
        # Results page
        results_page = self._create_results_page()
        self.tabs.addTab(results_page, "Results")
        
        # Settings page
        settings_page = self._create_settings_page()
        self.tabs.addTab(settings_page, "Settings")
        
        main_layout.addWidget(self.tabs)
        
        # Apply initial theme
        self._apply_theme()
        
        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_header(self):
        """Create ASUS MyASus-style header bar"""
        header = QtWidgets.QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        
        # Logo/Title
        title_label = QtWidgets.QLabel("Apple Pi Diagnostics")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
        """)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Action buttons
        btn_style = """
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
                margin-left: 8px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """
        
        self.run_all_btn = QtWidgets.QPushButton("Run All Tests")
        self.run_all_btn.setStyleSheet(btn_style)
        self.run_all_btn.clicked.connect(self.run_all_tests)
        layout.addWidget(self.run_all_btn)
        
        self.export_btn = QtWidgets.QPushButton("Generate PDF")
        self.export_btn.setStyleSheet(btn_style)
        self.export_btn.clicked.connect(self.generate_and_preview_pdf)
        layout.addWidget(self.export_btn)
        
        return header

    def _create_overview_page(self):
        """Create Overview page with system information"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # System information card
        self.sys_info_card = self._create_system_info_card()
        layout.addWidget(self.sys_info_card)
        
        # Quick stats
        stats_label = QtWidgets.QLabel("Quick Status")
        stats_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            padding: 8px 0;
        """)
        layout.addWidget(stats_label)
        
        # Test summary cards
        summary_grid = QtWidgets.QGridLayout()
        summary_grid.setSpacing(16)
        
        tests = [
            ("CPU", "cpu", "cpu"),
            ("RAM", "ram", "ram"),
            ("Storage", "sd", "sd"),
            ("Network", "network", "network"),
            ("USB", "usb", "usb"),
            ("HDMI", "hdmi", "hdmi"),
            ("GPIO", "gpio", "gpio"),
        ]
        
        row, col = 0, 0
        for title, icon, test_id in tests:
            # Create separate cards for overview (read-only status display)
            card = StatusCard(title, icon)
            card.test_btn.hide()
            self.overview_cards[test_id] = card
            # Update status from test results if available
            if test_id in self.test_results:
                with self.results_lock:
                    result = self.test_results.get(test_id, {})
                status = result.get("status", "PENDING")
                details = result.get("note", "")
                if not details:
                    if "avg_cpu_percent" in result:
                        details = f"CPU: {result['avg_cpu_percent']:.1f}%"
                    elif "tested_mb" in result:
                        details = f"Tested: {result['tested_mb']:.0f} MB"
                    elif "count" in result:
                        details = f"Found: {result['count']} items"
                card.set_status(status, details)
            summary_grid.addWidget(card, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        layout.addLayout(summary_grid)
        layout.addStretch()
        
        return page

    def _create_testing_page(self):
        """Create Testing page with test controls"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Instructions
        info_label = QtWidgets.QLabel("Select individual tests to run, or use 'Run All Tests' to test everything.")
        info_label.setObjectName("info_label")
        info_label.setStyleSheet("""
            font-size: 14px;
            color: #444444;
            padding: 4px 0 8px 0;
        """)
        layout.addWidget(info_label)
        
        # Test cards grid
        tests_label = QtWidgets.QLabel("Hardware Diagnostics")
        tests_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            padding: 8px 0;
        """)
        layout.addWidget(tests_label)
        
        tests_grid = QtWidgets.QGridLayout()
        tests_grid.setSpacing(16)
        
        # Create test cards (reuse from overview but with test buttons)
        tests = [
            ("CPU", "cpu", "cpu"),
            ("RAM", "ram", "ram"),
            ("Storage", "sd", "sd"),
            ("Network", "network", "network"),
            ("USB", "usb", "usb"),
            ("HDMI", "hdmi", "hdmi"),
            ("GPIO", "gpio", "gpio"),
        ]
        
        row, col = 0, 0
        for title, icon, test_id in tests:
            # Create or get card for testing page
            if test_id not in self.test_cards:
                card = StatusCard(title, icon)
                # Use a closure to properly capture test_id
                def make_test_handler(tid):
                    return lambda checked: self.run_test(tid)
                card.test_btn.clicked.connect(make_test_handler(test_id))
                self.test_cards[test_id] = card
            else:
                card = self.test_cards[test_id]
                card.test_btn.show()
            tests_grid.addWidget(card, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        layout.addLayout(tests_grid)
        layout.addStretch()
        
        return page

    def _create_results_page(self):
        """Create Results page showing test results"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Results header
        header = QtWidgets.QHBoxLayout()
        results_label = QtWidgets.QLabel("Test Results")
        results_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
        """)
        header.addWidget(results_label)
        header.addStretch()
        
        clear_btn = QtWidgets.QPushButton("Clear Results")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        clear_btn.clicked.connect(self.clear_results)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # Results display area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.results_widget = QtWidgets.QWidget()
        self.results_layout = QtWidgets.QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(12)
        self.results_layout.addStretch()
        
        scroll.setWidget(self.results_widget)
        layout.addWidget(scroll)
        
        return page

    def _create_settings_page(self):
        """Create Settings page with theme, font size, and network options"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # Settings title
        title = QtWidgets.QLabel("Settings")
        title.setObjectName("settings_title")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: 600;
            color: #1a1a1a;
            padding-bottom: 8px;
        """)
        layout.addWidget(title)
        
        # Network Settings Card
        network_card = self._create_setting_card("Network", "Network configuration and status")
        network_layout = QtWidgets.QVBoxLayout()
        network_layout.setSpacing(12)
        
        # Network status
        status_label = QtWidgets.QLabel("Network Status:")
        status_label.setObjectName("setting_label")
        network_layout.addWidget(status_label)
        
        # Refresh network info button
        refresh_btn = QtWidgets.QPushButton("Refresh Network Info")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_network_info)
        network_layout.addWidget(refresh_btn)
        
        # Network info display
        self.network_info_text = QtWidgets.QTextEdit()
        self.network_info_text.setReadOnly(True)
        self.network_info_text.setMaximumHeight(200)
        self.network_info_text.setObjectName("network_info")
        self.network_info_text.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: 1px solid #d8d8d8;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        network_layout.addWidget(self.network_info_text)
        
        # Load initial network info
        self._refresh_network_info()
        
        network_card.layout().addLayout(network_layout)
        layout.addWidget(network_card)
        
        layout.addStretch()
        
        return page
    
    def _create_setting_card(self, title, description):
        """Create a settings card container"""
        card = QtWidgets.QWidget()
        card.setObjectName("setting_card")
        card.setStyleSheet("""
            QWidget#setting_card {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)
        
        card_title = QtWidgets.QLabel(title)
        card_title.setObjectName("section_card_title")
        card_title.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
        """)
        card_layout.addWidget(card_title)

        card_desc = QtWidgets.QLabel(description)
        card_desc.setObjectName("card_desc")
        card_desc.setStyleSheet("""
            font-size: 13px;
            color: #666666;
            padding-bottom: 8px;
        """)
        card_layout.addWidget(card_desc)
        
        return card
    
    def _refresh_network_info(self):
        """Refresh and display network information"""
        try:
            import psutil
            import json
            
            # Get network interfaces
            if_stats = psutil.net_if_stats()
            if_addrs = psutil.net_if_addrs()
            
            info_lines = []
            info_lines.append("Network Interfaces:\n")
            info_lines.append("-" * 50)
            
            for name, stats in if_stats.items():
                if name == "lo":
                    continue
                up_status = "UP" if stats.isup else "DOWN"
                info_lines.append(f"\n{name}: {up_status}")
                
                # Get addresses
                addrs = if_addrs.get(name, [])
                for addr in addrs:
                    if hasattr(addr, 'address'):
                        addr_family = "IPv4" if addr.family == socket.AF_INET else "IPv6" if addr.family == socket.AF_INET6 else "MAC"
                        info_lines.append(f"  {addr_family}: {addr.address}")
            
            # Get default gateway and local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                local_ip = s.getsockname()[0]
                s.close()
                info_lines.append(f"\n\nLocal IP: {local_ip}")
            except Exception:
                info_lines.append("\n\nLocal IP: Not available")
            
            # DNS test
            try:
                import time
                t0 = time.time()
                socket.gethostbyname("www.google.com")
                dns_time = (time.time() - t0) * 1000
                info_lines.append(f"DNS Resolution: OK ({dns_time:.0f}ms)")
            except Exception as e:
                info_lines.append(f"DNS Resolution: Failed ({str(e)})")
            
            self.network_info_text.setPlainText("\n".join(info_lines))
        except Exception as e:
            self.network_info_text.setPlainText(f"Error loading network info: {e}")

    def _create_system_info_card(self):
        """Create system information card"""
        card = QtWidgets.QWidget()
        card.setObjectName("sys_info_card")
        
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        title = QtWidgets.QLabel("System Information")
        title.setObjectName("sys_info_title")
        layout.addWidget(title)
        
        self.sys_info_layout = QtWidgets.QGridLayout()
        self.sys_info_layout.setSpacing(12)
        layout.addLayout(self.sys_info_layout)
        
        return card

    def _update_system_info(self):
        """Update system information display"""
        try:
            hostname = socket.gethostname()
            system = platform.system()
            machine = platform.machine()
            processor = platform.processor()
            
            # Try to get Pi model
            pi_model = "Unknown"
            try:
                if Path("/proc/device-tree/model").exists():
                    pi_model = Path("/proc/device-tree/model").read_text(errors="ignore").strip('\x00\n')
            except Exception:
                pass
            
            info_items = [
                ("Hostname", hostname),
                ("System", f"{system} {machine}"),
                ("Processor", processor or "Unknown"),
                ("Device", pi_model),
            ]
            
            # Clear existing
            while self.sys_info_layout.count():
                item = self.sys_info_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Add info items
            self.sys_info_labels.clear()
            row = 0
            for label, value in info_items:
                label_widget = QtWidgets.QLabel(f"{label}:")
                label_widget.setObjectName("sys_info_label")
                value_widget = QtWidgets.QLabel(value)
                value_widget.setObjectName("sys_info_value")
                self.sys_info_labels.extend([label_widget, value_widget])
                
                self.sys_info_layout.addWidget(label_widget, row, 0)
                self.sys_info_layout.addWidget(value_widget, row, 1)
                row += 1
        except Exception as e:
            self.statusBar().showMessage(f"Error loading system info: {e}")

    @QtCore.pyqtSlot()
    def _update_results_display(self):
        """Update the results page with current test results"""
        # Clear existing results
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Thread-safe copy of results
        with self.results_lock:
            results_copy = deepcopy(self.test_results)
        
        if not results_copy:
            no_results = QtWidgets.QLabel("No test results yet. Run tests from the Testing page.")
            no_results.setStyleSheet("""
                font-size: 14px;
                color: #888888;
                padding: 40px;
            """)
            no_results.setAlignment(QtCore.Qt.AlignCenter)
            self.results_layout.addWidget(no_results)
        else:
            for test_id, result in results_copy.items():
                result_card = self._create_result_card(test_id, result)
                self.results_layout.addWidget(result_card)
        
        self.results_layout.addStretch()

    def _summarize_result(self, test_id, result):
        """Return a list of plain-English summary lines for a test result."""
        status = result.get("status", "UNKNOWN")
        lines = []

        if test_id == "cpu":
            avg = result.get("avg_cpu_percent")
            if avg is not None:
                lines.append(f"CPU averaged {avg:.1f}% load during the test.")
            workers = result.get("workers")
            if workers:
                lines.append(f"Used {workers} worker thread{'s' if workers != 1 else ''}.")
            temp = result.get("max_temperature")
            if temp is not None:
                lines.append(f"Peak temperature: {temp:.0f} °C.")
            per_cpu = result.get("per_cpu_percent", [])
            if per_cpu:
                lines.append(f"Individual cores: {', '.join(f'{v:.0f}%' for v in per_cpu)}.")

        elif test_id == "ram":
            tested = result.get("tested_mb")
            if tested is not None:
                lines.append(f"Tested {tested:.0f} MB of RAM.")
            errors = result.get("errors", [])
            if errors:
                lines.append(f"Errors found: {'; '.join(str(e) for e in errors[:3])}.")
            else:
                lines.append("No memory errors detected.")
            tp = result.get("throughput_mb_s")
            if tp is not None:
                lines.append(f"Throughput: {tp:.0f} MB/s.")

        elif test_id == "sd":
            total = result.get("total_devices", 0)
            tested_d = result.get("tested_devices", 0)
            lines.append(f"Found {total} storage device{'s' if total != 1 else ''}; tested {tested_d}.")
            for dev in result.get("devices", []):
                name = dev.get("device", "?")
                size = dev.get("size_gb")
                fs = dev.get("fstype", "unknown fs")
                dev_status = dev.get("status", "?")
                w = dev.get("write_mb_s")
                r = dev.get("read_mb_s")
                note = dev.get("note", "")
                size_str = f"{size:.0f} GB, " if size else ""
                speed_str = ""
                if w is not None and r is not None:
                    speed_str = f" — {w:.0f} MB/s write, {r:.0f} MB/s read"
                elif note:
                    speed_str = f" — {note}"
                lines.append(f"{name} ({size_str}{fs}): {dev_status}{speed_str}.")

        elif test_id == "network":
            local_ip = result.get("local_ip")
            if local_ip:
                lines.append(f"Local IP address: {local_ip}.")
            ifaces = result.get("interfaces", [])
            up_ifaces = [i["name"] for i in ifaces if i.get("up")]
            if up_ifaces:
                lines.append(f"Active interfaces: {', '.join(up_ifaces)}.")
            dns = result.get("dns", {})
            if dns.get("ok"):
                lat = dns.get("latency_s")
                lat_str = f" ({lat*1000:.0f} ms)" if lat is not None else ""
                lines.append(f"DNS resolution OK{lat_str}.")
            elif dns:
                lines.append(f"DNS resolution failed: {dns.get('note', '')}.")
            pings = result.get("ping", [])
            ok_pings = [p["host"] for p in pings if p.get("ok")]
            fail_pings = [p["host"] for p in pings if not p.get("ok")]
            if ok_pings:
                lines.append(f"Ping OK to: {', '.join(ok_pings)}.")
            if fail_pings:
                lines.append(f"Ping failed to: {', '.join(fail_pings)}.")

        elif test_id == "usb":
            count = result.get("count")
            if count is not None:
                lines.append(f"Found {count} USB device{'s' if count != 1 else ''}.")
            devices = result.get("devices", [])
            for d in devices[:5]:
                lines.append(f"  • {d}")
            if len(devices) > 5:
                lines.append(f"  … and {len(devices) - 5} more.")
            note = result.get("note", "")
            if note and status != "OK":
                lines.append(note)
            w = result.get("write_mb_s")
            r = result.get("read_mb_s")
            if w is not None and r is not None:
                lines.append(f"Speed test: {w:.0f} MB/s write, {r:.0f} MB/s read.")

        elif test_id == "hdmi":
            count = result.get("count")
            if count is not None:
                lines.append(f"{count} display{'s' if count != 1 else ''} connected.")
            for d in result.get("displays", []):
                name = d.get("name", "Unknown")
                res = d.get("resolution", "")
                lines.append(f"  • {name}{': ' + res if res else ''}.")
            note = result.get("note", "")
            if note:
                lines.append(note)

        elif test_id == "gpio":
            note = result.get("note", "")
            driver = result.get("driver", "")
            if driver:
                lines.append(f"GPIO driver: {driver}.")
            if note:
                lines.append(note)
            gpio_results = result.get("results", [])
            if gpio_results:
                passed = sum(1 for r in gpio_results if r)
                lines.append(f"Loopback: {passed}/{len(gpio_results)} pulses verified.")

        else:
            note = result.get("note", result.get("error", ""))
            if note:
                lines.append(note)

        if not lines:
            lines.append("No details available.")

        return lines

    def _create_result_card(self, test_id, result):
        """Create a card displaying a test result"""
        card_bg = "#ffffff"
        border_color = "#d8d8d8"
        text_color = "#111111"
        summary_color = "#333333"

        card = QtWidgets.QWidget()
        card.setObjectName("result_card")
        card.setStyleSheet(f"""
            QWidget#result_card {{
                background-color: {card_bg};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header: test name + pass/fail badge
        header = QtWidgets.QHBoxLayout()
        test_labels = {
            "cpu": "CPU", "ram": "RAM", "sd": "Storage",
            "network": "Network", "usb": "USB", "hdmi": "HDMI", "gpio": "GPIO",
        }
        test_name = QtWidgets.QLabel(test_labels.get(test_id, test_id.upper()))
        test_name.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {text_color};")
        header.addWidget(test_name)
        header.addStretch()

        status = result.get("status", "UNKNOWN")
        if status in ("OK", "PASS"):
            status_color, status_text = "#10b981", "✓ Passed"
        elif status in ("FAIL", "ERROR"):
            status_color, status_text = "#ef4444", "✗ Failed"
        elif status == "UNSUPPORTED":
            status_color, status_text = "#f59e0b", "— Not supported"
        else:
            status_color, status_text = "#6b7280", "○ Unknown"

        status_label = QtWidgets.QLabel(status_text)
        status_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {status_color};")
        header.addWidget(status_label)
        layout.addLayout(header)

        # Divider
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setStyleSheet(f"color: {border_color};")
        layout.addWidget(divider)

        # Plain-English summary
        summary_lines = self._summarize_result(test_id, result)
        summary_text = "\n".join(summary_lines)
        summary_label = QtWidgets.QLabel(summary_text)
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet(f"font-size: 13px; color: {summary_color}; padding: 2px 0;")
        layout.addWidget(summary_label)

        # Timestamp
        timestamp = result.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        time_label = QtWidgets.QLabel(f"Tested: {timestamp}")
        time_label.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(time_label)

        return card

    def run_test(self, test_id):
        """Run a specific diagnostic test"""
        card = self.test_cards.get(test_id)
        if not card:
            return
            
        card.test_btn.setEnabled(False)
        card.set_status("RUNNING", "Testing...")
        self.statusBar().showMessage(f"Running {test_id.upper()} test...")
        
        def run_in_thread():
            try:
                if test_id == "cpu":
                    result = run_cpu_quick_test(duration=5, workers=None)
                elif test_id == "ram":
                    result = run_ram_quick_test(total_mb=64, chunk_mb=16, passes=1)
                elif test_id == "sd":
                    result = run_storage_quick_test()
                elif test_id == "network":
                    result = run_network_quick_test()
                elif test_id == "usb":
                    result = run_usb_quick_test()
                elif test_id == "hdmi":
                    result = run_hdmi_quick_test()
                elif test_id == "gpio":
                    result = run_gpio_quick_test()
                else:
                    result = {"status": "UNSUPPORTED", "note": "Unknown test"}
                
                # Add timestamp
                result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Store result (thread-safe)
                with self.results_lock:
                    self.test_results[test_id] = result
                
                # Update UI
                status = result.get("status", "UNKNOWN")
                details = result.get("note", "")
                if not details:
                    if "avg_cpu_percent" in result:
                        details = f"CPU: {result['avg_cpu_percent']:.1f}%"
                    elif "tested_mb" in result:
                        details = f"Tested: {result['tested_mb']:.0f} MB"
                    elif "total_devices" in result:
                        # Storage test result
                        total = result.get("total_devices", 0)
                        tested = result.get("tested_devices", 0)
                        details = f"{tested}/{total} devices tested"
                    elif "count" in result:
                        details = f"Found: {result['count']} items"
                    elif "local_ip" in result:
                        details = f"IP: {result.get('local_ip', 'N/A')}"
                
                QtCore.QMetaObject.invokeMethod(
                    card, "set_status", QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(str, status),
                    QtCore.Q_ARG(str, details)
                )
                QtCore.QMetaObject.invokeMethod(
                    card.test_btn, "setEnabled", QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(bool, True)
                )
                QtCore.QMetaObject.invokeMethod(
                    self, "_update_results_display", QtCore.Qt.QueuedConnection
                )
                QtCore.QMetaObject.invokeMethod(
                    self.statusBar(), "showMessage", QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(str, f"{test_id.upper()} test completed")
                )
            except Exception as e:
                error_result = {"status": "FAIL", "error": str(e), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                with self.results_lock:
                    self.test_results[test_id] = error_result
                QtCore.QMetaObject.invokeMethod(
                    card, "set_status", QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(str, "FAIL"),
                    QtCore.Q_ARG(str, str(e))
                )
                QtCore.QMetaObject.invokeMethod(
                    card.test_btn, "setEnabled", QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(bool, True)
                )
                QtCore.QMetaObject.invokeMethod(
                    self, "_update_results_display", QtCore.Qt.QueuedConnection
                )
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

    def run_all_tests(self):
        """Run all diagnostic tests"""
        self.statusBar().showMessage("Running all tests...")
        # Add small delay between starting tests to avoid overwhelming the system
        import time
        for i, test_id in enumerate(self.test_cards.keys()):
            if i > 0:
                time.sleep(0.2)  # Small delay between test starts
            self.run_test(test_id)

    def clear_results(self):
        """Clear all test results"""
        with self.results_lock:
            self.test_results.clear()
        self._update_results_display()
        # Reset all cards to pending
        for card in self.test_cards.values():
            card.set_status("PENDING", "")
        self.statusBar().showMessage("Results cleared")

    def generate_and_preview_pdf(self):
        """Generate PDF and show preview dialog with USB save option"""
        # Generate report first
        if not self.test_results:
            self.statusBar().showMessage("No test results to report. Run tests first.", 3000)
            return
        
        self.statusBar().showMessage("Generating PDF...")
        try:
            # Build report data from test results
            with self.results_lock:
                results_copy = deepcopy(self.test_results)
            
            summary = {}
            details = {}
            
            for test_id, result in results_copy.items():
                status = result.get("status", "UNKNOWN")
                summary[test_id] = {
                    "status": status,
                    "message": result.get("note", result.get("error", "")),
                    "metrics": {k: v for k, v in result.items() if k not in ("status", "note", "error", "timestamp")}
                }
                details[test_id] = result
            
            report_data = {
                "title": "Apple Pi Diagnostics Report",
                "summary": summary,
                "details": details
            }
            
            results = build_report(report_data, REPORT_DIR, formats=("pdf", "html"))
            self.latest_report_dir = REPORT_DIR

            if "pdf" in results and results["pdf"]:
                pdf_path = results["pdf"]
                self._show_pdf_preview(pdf_path)
            else:
                self.statusBar().showMessage("Failed to generate PDF", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}", 3000)
    
    def _show_pdf_preview(self, pdf_path):
        """Show PDF preview dialog with save to USB option"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("PDF Preview - Apple Pi Diagnostics")
        dialog.setMinimumSize(800, 600)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # PDF preview area (using QTextBrowser to show HTML version if available)
        preview = QtWidgets.QTextBrowser()
        preview.setReadOnly(True)
        
        # Try to show HTML version if available
        html_path = pdf_path.with_suffix(".html")
        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                preview.setHtml(f.read())
        else:
            preview.setPlainText(f"PDF generated: {pdf_path}\n\nUse an external PDF viewer to preview.")
        
        layout.addWidget(preview)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        save_usb_btn = QtWidgets.QPushButton("Save to USB Drive")
        save_usb_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        save_usb_btn.clicked.connect(lambda: self._save_pdf_to_usb(pdf_path, dialog))
        button_layout.addWidget(save_usb_btn)
        
        button_layout.addStretch()
        
        open_btn = QtWidgets.QPushButton("Open File Location")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #777777;
            }
        """)
        open_btn.clicked.connect(lambda: self._open_file_location(pdf_path))
        button_layout.addWidget(open_btn)
        
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #cccccc;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #bbbbbb;
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def _save_pdf_to_usb(self, pdf_path, dialog):
        """Save PDF to USB drive"""
        dialog.setEnabled(False)
        try:
            # Create a temporary report directory with just the PDF
            import tempfile
            import shutil
            temp_dir = Path(tempfile.mkdtemp())
            shutil.copy2(pdf_path, temp_dir / pdf_path.name)
            
            result = save_report_to_usb(temp_dir)
            if result:
                QtWidgets.QMessageBox.information(
                    dialog, "Success", 
                    f"PDF saved to USB drive:\n{result}"
                )
                dialog.accept()
            else:
                QtWidgets.QMessageBox.warning(
                    dialog, "No USB Drive", 
                    "No USB drive found. Please insert a USB drive and try again."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                dialog, "Error", 
                f"Failed to save to USB: {e}"
            )
        finally:
            dialog.setEnabled(True)
    
    def _open_file_location(self, file_path):
        """Open file location in system file manager"""
        import subprocess
        import platform as plat
        try:
            if plat.system() == "Linux":
                subprocess.Popen(["xdg-open", str(file_path.parent)])
            elif plat.system() == "Darwin":
                subprocess.Popen(["open", str(file_path.parent)])
            elif plat.system() == "Windows":
                subprocess.Popen(["explorer", "/select,", str(file_path)])
        except Exception:
            pass

    def generate_report(self):
        """Generate a comprehensive report from all test results"""
        # Thread-safe copy of results
        with self.results_lock:
            if not self.test_results:
                self.statusBar().showMessage("No test results to report. Run tests first.", 3000)
                return
            results_copy = deepcopy(self.test_results)
            
        self.statusBar().showMessage("Generating report...")
        try:
            # Build report data from test results
            summary = {}
            details = {}
            
            for test_id, result in results_copy.items():
                status = result.get("status", "UNKNOWN")
                summary[test_id] = {
                    "status": status,
                    "message": result.get("note", result.get("error", "")),
                    "metrics": {k: v for k, v in result.items() if k not in ("status", "note", "error", "timestamp")}
                }
                details[test_id] = result
            
            report_data = {
                "title": "Apple Pi Diagnostics Report",
                "summary": summary,
                "details": details
            }
            
            results = build_report(report_data, REPORT_DIR, formats=("pdf", "html", "json", "qr"))
            self.latest_report_dir = REPORT_DIR
            self.statusBar().showMessage(f"Report generated: {len(results)} files", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}", 3000)

    def export_usb(self):
        if not self.latest_report_dir:
            self.generate_report()
        self.statusBar().showMessage("Saving to USB drive...")
        try:
            result = save_report_to_usb(self.latest_report_dir or REPORT_DIR)
            if result:
                self.statusBar().showMessage(f"Saved to USB: {result}", 5000)
            else:
                self.statusBar().showMessage("No USB drive found", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}", 3000)

    def export_sd(self):
        if not self.latest_report_dir:
            self.generate_report()
        self.statusBar().showMessage("Saving to SD boot partition...")
        try:
            result = save_report_to_sdboot(self.latest_report_dir or REPORT_DIR)
            if result:
                self.statusBar().showMessage(f"Saved to SD boot: {result}", 5000)
            else:
                self.statusBar().showMessage("SD boot partition not found", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}", 3000)

    def export_qr(self):
        if not self.latest_report_dir:
            self.generate_report()
        self.statusBar().showMessage("Generating QR code...")
        try:
            if self.qr_manager:
                self.qr_manager.stop()
            self.qr_manager = QRExportManager(self.latest_report_dir or REPORT_DIR)
            url = self.qr_manager.start()
            qr_path = REPORT_DIR / "qrs" / "report_qr.png"
            generate_qr_image(url, qr_path)
            self.statusBar().showMessage(f"QR code generated: {qr_path}", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}", 3000)

    def _update_tab_style(self):
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d8d8d8;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #ffffff;
                color: #555555;
                padding: 14px 40px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 15px;
                font-weight: 500;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #f0f6ff;
            }
        """)

    def _apply_theme(self):
        """Apply the light theme to all UI elements."""
        bg_color = "#ffffff"
        card_bg = "#ffffff"
        text_color = "#111111"
        text_secondary = "#444444"
        text_tertiary = "#666666"
        border_color = "#d8d8d8"
        header_bg = "#ffffff"
        
        # Update main window and central widget
        self.centralWidget().setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
            }}
        """)
        
        # Update header
        for widget in self.findChildren(QtWidgets.QWidget):
            if widget.objectName() == "" and widget.parent() == self.centralWidget():
                # Likely the header widget
                if widget.height() == 60:  # Header height
                    widget.setStyleSheet(f"""
                        QWidget {{
                            background-color: {header_bg};
                            border-bottom: 1px solid {border_color};
                        }}
                        QLabel {{
                            color: {text_color} !important;
                        }}
                    """)
        
        # Update tabs
        self._update_tab_style()
        
        # Update system info card
        if self.sys_info_card:
            self.sys_info_card.setStyleSheet(f"""
                QWidget#sys_info_card {{
                    background-color: {card_bg};
                    border-radius: 12px;
                    border: 1px solid {border_color};
                }}
                QLabel#sys_info_title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: {text_color} !important;
                }}
                QLabel#sys_info_label {{
                    font-size: 13px;
                    color: {text_secondary} !important;
                    font-weight: 500;
                }}
                QLabel#sys_info_value {{
                    font-size: 13px;
                    color: {text_color} !important;
                }}
            """)
        
        # Update status cards (testing page + overview page)
        all_cards = list(self.test_cards.values()) + list(self.overview_cards.values())
        for card in all_cards:
            card.set_icon_color("#555555")
            card.setStyleSheet(f"""
                StatusCard {{
                    background-color: {card_bg};
                    border-radius: 12px;
                    border: 1px solid {border_color};
                }}
                StatusCard:hover {{
                    border: 2px solid #0078d4;
                    background-color: #f0f6ff;
                }}
                QLabel#card_title {{
                    font-size: 14px;
                    font-weight: 600;
                    color: {text_color} !important;
                }}
                QLabel#card_details {{
                    font-size: 11px;
                    color: {text_tertiary} !important;
                }}
            """)
            # Update status label (preserve its dynamic color)
            status_label = card.findChild(QtWidgets.QLabel, "card_status")
            if status_label:
                current_style = status_label.styleSheet() or ""
                # Only update if it's the default pending state
                if "#666666" in current_style or "color: #666666" in current_style:
                    status_label.setStyleSheet(f"""
                        font-size: 12px;
                        color: {text_secondary} !important;
                        font-weight: 500;
                    """)
                # Otherwise keep the status-specific color (green/red/orange)
        
        # Update all other labels
        for label in self.findChildren(QtWidgets.QLabel):
            current_style = label.styleSheet() or ""
            current_text = label.text()
            
            # Skip status labels (they have their own colors)
            if "✓" in current_text or "✗" in current_text or "—" in current_text or "⟳" in current_text:
                continue
            
            # Update based on object name or text content
            if label.objectName() in ("sys_info_title", "sys_info_label", "sys_info_value"):
                continue  # Already handled
            
            if "font-size: 20px" in current_style or "font-weight: 600" in current_style:
                # Section headers
                label.setStyleSheet(f"""
                    font-size: 20px;
                    font-weight: 600;
                    color: {text_color} !important;
                    padding: 8px 0;
                """)
            elif label.objectName() == "info_label" or "No test results" in current_text:
                label.setStyleSheet(f"""
                    font-size: 14px;
                    color: {text_secondary} !important;
                    padding: 4px 0 8px 0;
                """)
            elif "font-size: 14px" in current_style and "color: #666666" in current_style:
                # Secondary text
                label.setStyleSheet(f"""
                    font-size: 14px;
                    color: {text_secondary} !important;
                """)
            elif "color:" not in current_style.lower() or "#1a1a1a" in current_style or "#666666" in current_style:
                # Default text - update to theme color
                if "#1a1a1a" in current_style:
                    new_style = current_style.replace("#1a1a1a", text_color)
                elif "#666666" in current_style:
                    new_style = current_style.replace("#666666", text_secondary)
                else:
                    new_style = f"{current_style}; color: {text_color} !important;"
                label.setStyleSheet(new_style)
        
        # Update scroll areas
        for scroll in self.findChildren(QtWidgets.QScrollArea):
            scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        # Result cards are rebuilt by _update_results_display() called below
        
        # Update settings page elements
        for widget in self.findChildren(QtWidgets.QWidget):
            if widget.objectName() == "setting_card":
                widget.setStyleSheet(f"""
                    QWidget#setting_card {{
                        background-color: {card_bg};
                        border-radius: 12px;
                        border: 1px solid {border_color};
                        padding: 20px;
                    }}
                """)
        
        # Update settings labels
        for label in self.findChildren(QtWidgets.QLabel):
            if label.objectName() == "settings_title":
                label.setStyleSheet(f"""
                    font-size: 24px;
                    font-weight: 600;
                    color: {text_color} !important;
                    padding-bottom: 8px;
                """)
            elif label.objectName() == "section_card_title":
                label.setStyleSheet(f"""
                    font-size: 18px;
                    font-weight: 600;
                    color: {text_color} !important;
                """)
            elif label.objectName() == "card_desc":
                label.setStyleSheet(f"""
                    font-size: 13px;
                    color: {text_secondary} !important;
                    padding-bottom: 8px;
                """)
            elif label.objectName() == "setting_label":
                label.setStyleSheet(f"""
                    font-size: 14px;
                    font-weight: 500;
                    color: {text_color} !important;
                """)
            elif label.objectName() == "setting_value":
                label.setStyleSheet(f"""
                    font-size: 13px;
                    color: {text_secondary} !important;
                """)
        
        # Update network info text
        if hasattr(self, 'network_info_text'):
            self.network_info_text.setStyleSheet(f"""
                QTextEdit#network_info {{
                    background-color: transparent;
                    border: 1px solid {border_color};
                    border-radius: 6px;
                    padding: 8px;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    color: {text_color};
                }}
            """)


    def closeEvent(self, event):
        if self.qr_manager:
            self.qr_manager.stop()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(17, 17, 17))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(248, 249, 250))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(17, 17, 17))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(17, 17, 17))
    app.setPalette(palette)
    
    # Show splash screen
    try:
        from gui.splash import SplashScreen
        splash = SplashScreen()
        splash.exec_and_wait()
    except Exception:
        pass
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
