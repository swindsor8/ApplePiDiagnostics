#!/usr/bin/env python3
"""
Apple Pi Diagnostics - Full Linux GUI (minimal skeleton)
Run: source ../venv/bin/activate && python3 main.py
"""
import sys
import os
import threading
import http.server
import socketserver
import socket
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui
from exports.export_qr import QRExportManager
from exports.export_usb import save_report_to_usb
from exports.export_sd_boot import save_report_to_sdboot
from diagnostics.report_builder import build_sample_report
# Try to reuse the splash module's logo discovery so the app icon matches the splash
try:
    from gui.splash import LOGO_PATH
except Exception:
    LOGO_PATH = None

APP_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = APP_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apple Pi Diagnostics")
        self.setMinimumSize(900, 600)
        self._build_ui()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Header with optional logo at left and title centered
        header = QtWidgets.QHBoxLayout()
        header.setAlignment(QtCore.Qt.AlignLeft)
        if LOGO_PATH and LOGO_PATH.exists():
            logo_pix = QtGui.QPixmap(str(LOGO_PATH)).scaled(36, 36, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            logo_lbl = QtWidgets.QLabel()
            logo_lbl.setPixmap(logo_pix)
            logo_lbl.setFixedSize(40, 40)
            header.addWidget(logo_lbl)
        title = QtWidgets.QLabel("Apple Pi Diagnostics")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:24px; font-weight:600;")
        header.addWidget(title)
        layout.addLayout(header)

        # Buttons row
        btn_row = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_row)

        self.full_btn = QtWidgets.QPushButton("Run Complete System Diagnostic")
        self.full_btn.clicked.connect(self.run_full_system_check)
        btn_row.addWidget(self.full_btn)

        self.individual_btn = QtWidgets.QPushButton("Run Individual Tests")
        self.individual_btn.clicked.connect(self.open_individual_tests)
        btn_row.addWidget(self.individual_btn)

        # Placeholder area for results
        self.results_box = QtWidgets.QTextEdit()
        self.results_box.setReadOnly(True)
        layout.addWidget(self.results_box, stretch=1)

        # Export buttons
        export_row = QtWidgets.QHBoxLayout()
        layout.addLayout(export_row)
        self.usb_btn = QtWidgets.QPushButton("Save to USB Drive")
        self.usb_btn.clicked.connect(self.export_usb)
        export_row.addWidget(self.usb_btn)

        self.sd_btn = QtWidgets.QPushButton("Save to SD Boot Partition")
        self.sd_btn.clicked.connect(self.export_sd)
        export_row.addWidget(self.sd_btn)

        self.view_btn = QtWidgets.QPushButton("View On Screen")
        self.view_btn.clicked.connect(self.view_onscreen)
        export_row.addWidget(self.view_btn)

        self.qr_btn = QtWidgets.QPushButton("Show QR Code")
        self.qr_btn.clicked.connect(self.show_qr)
        export_row.addWidget(self.qr_btn)

        # Status bar
        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)

    def append_result(self, text):
        self.results_box.append(text)
        self.status.showMessage(text, 5000)

    def run_full_system_check(self):
        self.append_result("Starting Full System Diagnostic...")
        thread = threading.Thread(target=self._full_system_worker, daemon=True)
        thread.start()

    def _full_system_worker(self):
        # For now, create a sample report and print status messages
        self.append_result("Running CPU test...")
        QtCore.QMetaObject.invokeMethod(self, "append_result", QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(str, "CPU test complete: OK"))
        self.append_result("Running RAM test...")
        QtCore.QMetaObject.invokeMethod(self, "append_result", QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(str, "RAM test complete: OK"))
        # Build a sample report (placeholder)
        report_path = build_sample_report(REPORT_DIR)
        QtCore.QMetaObject.invokeMethod(self, "append_result", QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(str, f"Full diagnostic complete. Report: {report_path}"))

    def open_individual_tests(self):
        dlg = IndividualTestsDialog(self)
        dlg.exec_()

    def export_usb(self):
        # Attempt to save to USB (scans /media/*)
        path = save_report_to_usb(REPORT_DIR)
        if path:
            self.append_result(f"Saved report to USB: {path}")
        else:
            self.append_result("No USB drive detected or save failed.")

    def export_sd(self):
        path = save_report_to_sdboot(REPORT_DIR)
        if path:
            self.append_result(f"Saved report to SD boot: {path}")
        else:
            self.append_result("Failed to save to SD boot partition.")

    def view_onscreen(self):
        # Open the latest report in the default browser (simple approach)
        latest = max(REPORT_DIR.glob('*'), key=lambda p: p.stat().st_mtime, default=None)
        if latest and latest.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(latest)))
            self.append_result(f"Opened report: {latest.name}")
        else:
            self.append_result("No report available to view.")

    def show_qr(self):
        # Start a simple HTTP server to serve report directory and show QR
        qm = QRExportManager(str(REPORT_DIR), port=8888)
        url = qm.start()
        if url:
            dialog = QRDisplayDialog(url, parent=self)
            dialog.exec_()
        else:
            self.append_result("Failed to start QR export server.")

class IndividualTestsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Individual Tests")
        self.setMinimumSize(600, 400)
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel("Select tests to run:")
        layout.addWidget(note)

        self.check_cpu = QtWidgets.QCheckBox("CPU Test")
        self.check_ram = QtWidgets.QCheckBox("RAM Test")
        self.check_sd = QtWidgets.QCheckBox("SD Card Test")
        self.check_cpu.setChecked(True)
        layout.addWidget(self.check_cpu)
        layout.addWidget(self.check_ram)
        layout.addWidget(self.check_sd)

        run_btn = QtWidgets.QPushButton("Run Selected")
        run_btn.clicked.connect(self.run_selected)
        layout.addWidget(run_btn)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def run_selected(self):
        self.log.append("Running selected tests...")
        if self.check_cpu.isChecked():
            self.log.append("CPU test placeholder: OK")
        if self.check_ram.isChecked():
            self.log.append("RAM test placeholder: OK")
        if self.check_sd.isChecked():
            self.log.append("SD card test placeholder: OK")

class QRDisplayDialog(QtWidgets.QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QR Code - Scan to View Report")
        self.setMinimumSize(420, 480)
        layout = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel("Scan this QR code with your phone to open the report:")
        layout.addWidget(lbl)
        pix = QtGui.QPixmap(str(Path(__file__).parent / "qr_placeholder.png"))
        self.qr_label = QtWidgets.QLabel()
        self.qr_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.qr_label, stretch=1)
        # generate QR image via export_qr (already created)
        from exports.export_qr import generate_qr_image
        img_path = generate_qr_image(url, Path("/tmp/applepi_qr.png"))
        pix = QtGui.QPixmap(str(img_path))
        self.qr_label.setPixmap(pix.scaled(360, 360, QtCore.Qt.KeepAspectRatio))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # Set the application icon (taskbar/titlebar) to the apple logo if available
    if LOGO_PATH and LOGO_PATH.exists():
        app.setWindowIcon(QtGui.QIcon(str(LOGO_PATH)))
    # Show splash screen (Option B) before main window
    try:
        from gui.splash import SplashScreen
        splash = SplashScreen(duration_ms=2200)
        splash.exec_and_wait()
    except Exception as e:
        # If splash fails, continue to main window
        print("Splash failed to show:", e)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
