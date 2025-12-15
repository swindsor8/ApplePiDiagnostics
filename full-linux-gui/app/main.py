#!/usr/bin/env python3
"""
Apple Pi Diagnostics - Full Linux GUI (ASUS MyASus-style Dashboard)
Run: source ../venv/bin/activate && python3 main.py
"""
import sys
import platform
import socket
import threading
import json
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
from diagnostics.sd.sd_test import run_sd_quick_test
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


class StatusCard(QtWidgets.QWidget):
    """Card widget for displaying diagnostic test status (ASUS MyASus style)"""
    
    def __init__(self, title, icon_text="●", parent=None):
        super().__init__(parent)
        self.title = title
        self.icon_text = icon_text
        self.status = "PENDING"
        self.details = ""
        self._build_ui()
        
    def _build_ui(self):
        self.setFixedSize(200, 160)
        self.setStyleSheet("""
            StatusCard {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
            StatusCard:hover {
                border: 2px solid #0078d4;
                background-color: #f8f9fa;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Icon and title
        header = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel(self.icon_text)
        icon_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.addWidget(icon_label)
        
        title_label = QtWidgets.QLabel(self.title)
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #1a1a1a;
        """)
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Status indicator
        self.status_label = QtWidgets.QLabel("Pending")
        self.status_label.setStyleSheet("""
            font-size: 12px;
            color: #666666;
            font-weight: 500;
        """)
        layout.addWidget(self.status_label)
        
        # Details
        self.details_label = QtWidgets.QLabel("")
        self.details_label.setStyleSheet("""
            font-size: 11px;
            color: #888888;
        """)
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


class MainWindow(QtWidgets.QMainWindow):
    sig_append = QtCore.pyqtSignal(str)
    sig_set_button_enabled = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.latest_report_dir = None
        self.qr_manager = None
        self.test_cards = {}
        self.test_results = {}  # Store all test results
        self.results_lock = threading.Lock()  # Lock for thread-safe results updates
        self.dark_mode = False  # Theme state
        self.sys_info_card = None  # Store reference to system info card
        self.sys_info_labels = []  # Store system info labels for theme updates
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
        
        # Theme toggle button
        self.theme_btn = QtWidgets.QPushButton("🌙 Dark")
        self.theme_btn.setStyleSheet(btn_style)
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)
        
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
            ("CPU", "⚡", "cpu"),
            ("RAM", "💾", "ram"),
            ("Storage", "💿", "sd"),
            ("Network", "🌐", "network"),
            ("USB", "🔌", "usb"),
            ("HDMI", "🖥️", "hdmi"),
            ("GPIO", "📌", "gpio"),
        ]
        
        row, col = 0, 0
        for title, icon, test_id in tests:
            # Create separate cards for overview (read-only status display)
            card = StatusCard(title, icon)
            card.test_btn.hide()
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
        info_label.setStyleSheet("""
            font-size: 14px;
            color: #666666;
            padding: 12px;
            background-color: #e8f4f8;
            border-radius: 8px;
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
            ("CPU", "⚡", "cpu"),
            ("RAM", "💾", "ram"),
            ("Storage", "💿", "sd"),
            ("Network", "🌐", "network"),
            ("USB", "🔌", "usb"),
            ("HDMI", "🖥️", "hdmi"),
            ("GPIO", "📌", "gpio"),
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
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #ffffff; }")
        
        self.results_widget = QtWidgets.QWidget()
        self.results_layout = QtWidgets.QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(12)
        self.results_layout.addStretch()
        
        scroll.setWidget(self.results_widget)
        layout.addWidget(scroll)
        
        return page

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

    def _create_result_card(self, test_id, result):
        """Create a card displaying a test result"""
        card = QtWidgets.QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                padding: 16px;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Header with test name and status
        header = QtWidgets.QHBoxLayout()
        test_name = QtWidgets.QLabel(test_id.upper())
        test_name.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
        """)
        header.addWidget(test_name)
        header.addStretch()
        
        status = result.get("status", "UNKNOWN")
        if status == "OK" or status == "PASS":
            status_color = "#10b981"
            status_text = "✓ PASS"
        elif status == "FAIL" or status == "ERROR":
            status_color = "#ef4444"
            status_text = "✗ FAIL"
        elif status == "UNSUPPORTED":
            status_color = "#f59e0b"
            status_text = "— UNSUPPORTED"
        else:
            status_color = "#6b7280"
            status_text = "○ UNKNOWN"
        
        status_label = QtWidgets.QLabel(status_text)
        status_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {status_color};
        """)
        header.addWidget(status_label)
        layout.addLayout(header)
        
        # Result details
        details_text = QtWidgets.QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(200)
        details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        
        # Format result as JSON
        formatted_result = json.dumps(result, indent=2)
        details_text.setPlainText(formatted_result)
        layout.addWidget(details_text)
        
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
                    result = run_sd_quick_test()
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

    def show_export_menu(self):
        """Show export options menu"""
        menu = QtWidgets.QMenu(self)
        
        usb_action = menu.addAction("📱 Save to USB Drive")
        usb_action.triggered.connect(self.export_usb)
        
        sd_action = menu.addAction("💿 Save to SD Boot")
        sd_action.triggered.connect(self.export_sd)
        
        qr_action = menu.addAction("📱 Generate QR Code")
        qr_action.triggered.connect(self.export_qr)
        
        report_action = menu.addAction("📄 Generate Report")
        report_action.triggered.connect(self.generate_report)
        
        menu.exec_(self.export_btn.mapToGlobal(QtCore.QPoint(0, self.export_btn.height())))

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
        """Update tab styling based on current theme"""
        bg_color = "#1a1a1a" if self.dark_mode else "#f5f5f5"
        tab_bg = "#2d2d2d" if self.dark_mode else "#ffffff"
        tab_text = "#e0e0e0" if self.dark_mode else "#666666"
        selected_bg = "#0078d4"
        hover_bg = "#3d3d3d" if self.dark_mode else "#e8f4f8"
        border_color = "#444444" if self.dark_mode else "#e0e0e0"
        
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {border_color};
                background-color: {bg_color};
            }}
            QTabBar::tab {{
                background-color: {tab_bg};
                color: {tab_text};
                padding: 14px 40px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 15px;
                font-weight: 500;
                min-width: 120px;
            }}
            QTabBar::tab:selected {{
                background-color: {selected_bg};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {hover_bg};
            }}
        """)

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        self.dark_mode = not self.dark_mode
        self._apply_theme()
        self.theme_btn.setText("☀️ Light" if self.dark_mode else "🌙 Dark")

    def _apply_theme(self):
        """Apply the current theme to all UI elements"""
        if self.dark_mode:
            # Dark theme colors
            bg_color = "#1a1a1a"
            card_bg = "#2d2d2d"
            text_color = "#e0e0e0"
            text_secondary = "#b0b0b0"
            border_color = "#444444"
            header_bg = "#2d2d2d"
            info_bg = "#1e3a5f"
        else:
            # Light theme colors
            bg_color = "#f5f5f5"
            card_bg = "#ffffff"
            text_color = "#1a1a1a"
            text_secondary = "#666666"
            border_color = "#e0e0e0"
            header_bg = "#ffffff"
            info_bg = "#e8f4f8"
        
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
                            color: {text_color};
                        }}
                    """)
        
        # Update tabs
        self._update_tab_style()
        
        # Update status cards
        for card in self.test_cards.values():
            card.setStyleSheet(f"""
                StatusCard {{
                    background-color: {card_bg};
                    border-radius: 12px;
                    border: 1px solid {border_color};
                }}
                StatusCard:hover {{
                    border: 2px solid #0078d4;
                    background-color: {'#3d3d3d' if self.dark_mode else '#f8f9fa'};
                }}
                QLabel {{
                    color: {text_color};
                }}
            """)
        
        # Update all QLabel text colors in pages
        for label in self.findChildren(QtWidgets.QLabel):
            current_style = label.styleSheet() or ""
            # Only update if it doesn't have explicit color set
            if "color:" not in current_style.lower():
                label.setStyleSheet(f"{current_style}; color: {text_color};")
        
        # Update info labels
        for label in self.findChildren(QtWidgets.QLabel):
            if "Select individual tests" in label.text() or "No test results" in label.text():
                label.setStyleSheet(f"""
                    font-size: 14px;
                    color: {text_secondary};
                    padding: 12px;
                    background-color: {info_bg};
                    border-radius: 8px;
                """)

    def closeEvent(self, event):
        if self.qr_manager:
            self.qr_manager.stop()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Apply modern color palette
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(245, 245, 245))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(26, 26, 26))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(248, 249, 250))
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
