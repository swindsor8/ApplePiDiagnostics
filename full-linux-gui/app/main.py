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
    sig_append = QtCore.pyqtSignal(str)
    sig_set_button_enabled = QtCore.pyqtSignal(bool)
    sig_progress_live = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apple Pi Diagnostics")
        self.setMinimumSize(900, 600)
        self._build_ui()
        # connect thread-safe signals
        try:
            self.sig_append.connect(self.append_result)
            self.sig_set_button_enabled.connect(self.full_btn.setEnabled)
        except Exception:
            pass

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

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
        main_layout.addLayout(header)

        # Navigation bar
        nav = QtWidgets.QHBoxLayout()
        self.home_btn = QtWidgets.QPushButton("Home")
        self.home_btn.setToolTip("Open the dashboard with a quick summary and live progress")
        self.home_btn.clicked.connect(self.show_dashboard)
        nav.addWidget(self.home_btn)

        self.tests_btn = QtWidgets.QPushButton("Tests")
        self.tests_btn.setToolTip("Open individual tests panel")
        self.tests_btn.clicked.connect(self.open_individual_tests)
        nav.addWidget(self.tests_btn)

        self.results_btn = QtWidgets.QPushButton("Results")
        self.results_btn.setToolTip("View detailed test results")
        self.results_btn.clicked.connect(self.show_results)
        nav.addWidget(self.results_btn)

        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.setToolTip("Open application settings (theme, font, network)")
        self.settings_btn.clicked.connect(self.open_settings)
        nav.addWidget(self.settings_btn)

        main_layout.addLayout(nav)

        # Dashboard area (stacked widget used to switch views)
        self._stack = QtWidgets.QStackedWidget()
        main_layout.addWidget(self._stack, stretch=1)

        # Dashboard widget
        self._dashboard = QtWidgets.QWidget()
        dash_layout = QtWidgets.QVBoxLayout(self._dashboard)
        self.dashboard_status = QtWidgets.QLabel("No diagnostics run yet")
        dash_layout.addWidget(self.dashboard_status)
        self.dashboard_progress = QtWidgets.QProgressBar()
        self.dashboard_progress.setRange(0, 100)
        self.dashboard_progress.setValue(0)
        dash_layout.addWidget(self.dashboard_progress)
        self._stack.addWidget(self._dashboard)

        # Results view (text)
        results_widget = QtWidgets.QWidget()
        results_layout = QtWidgets.QVBoxLayout(results_widget)
        self.results_box = QtWidgets.QTextEdit()
        self.results_box.setReadOnly(True)
        results_layout.addWidget(self.results_box)
        self._stack.addWidget(results_widget)

        # Default to dashboard
        self._stack.setCurrentWidget(self._dashboard)

        # Export & action row
        export_row = QtWidgets.QHBoxLayout()
        main_layout.addLayout(export_row)
        self.full_btn = QtWidgets.QPushButton("Run Complete System Diagnostic")
        self.full_btn.clicked.connect(self.run_full_system_check)
        self.full_btn.setToolTip("Run all available diagnostics and generate a report")
        export_row.addWidget(self.full_btn)

        self.usb_btn = QtWidgets.QPushButton("Save to USB Drive")
        self.usb_btn.clicked.connect(self.export_usb)
        self.usb_btn.setToolTip("Save the most recent report to any attached USB drive")
        export_row.addWidget(self.usb_btn)

        self.sd_btn = QtWidgets.QPushButton("Save to SD Boot Partition")
        self.sd_btn.clicked.connect(self.export_sd)
        self.sd_btn.setToolTip("Save the most recent report to the SD boot partition")
        export_row.addWidget(self.sd_btn)

        self.view_btn = QtWidgets.QPushButton("View On Screen")
        self.view_btn.clicked.connect(self.view_onscreen)
        self.view_btn.setToolTip("Open the latest report in the system browser")
        export_row.addWidget(self.view_btn)

        self.qr_btn = QtWidgets.QPushButton("Show QR Code")
        self.qr_btn.clicked.connect(self.show_qr)
        self.qr_btn.setToolTip("Show a QR code for the latest report for mobile scanning")
        export_row.addWidget(self.qr_btn)

        # Status bar
        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)

        # wire live progress
        try:
            self.sig_progress_live.connect(self.dashboard_progress.setValue)
        except Exception:
            pass

    def append_result(self, text):
        self.results_box.append(text)
        self.status.showMessage(text, 5000)

    def run_full_system_check(self):
        self.append_result("Starting Full System Diagnostic...")
        # disable the button while running
        try:
            self.full_btn.setEnabled(False)
        except Exception:
            pass
        thread = threading.Thread(target=self._full_system_worker, daemon=True)
        thread.start()

    def _full_system_worker(self):
        # Run CPU test with live progress updates
        try:
            from diagnostics.cpu import cpu_test
        except Exception:
            cpu_test = None

        self.append_result("Running CPU test...")

        def _progress_cb(sample):
            # format a short progress message and emit via signal
            avg = sample.get("avg")
            msg = f"CPU sample: avg={avg:.1f}%"
            try:
                self.sig_append.emit(msg)
            except Exception:
                try:
                    self.append_result(msg)
                except Exception:
                    pass

        cpu_result = None
        if cpu_test:
            try:
                cpu_result = cpu_test.run_cpu_test(duration=15, progress_callback=_progress_cb)
                try:
                    self.sig_append.emit(f"CPU test complete. avg={cpu_result.get('avg_cpu_percent'):.1f}%")
                except Exception:
                    try:
                        self.append_result(f"CPU test complete. avg={cpu_result.get('avg_cpu_percent'):.1f}%")
                    except Exception:
                        pass
            except Exception as e:
                try:
                    self.sig_append.emit(f"CPU test failed: {e}")
                except Exception:
                    try:
                        self.append_result(f"CPU test failed: {e}")
                    except Exception:
                        pass
        else:
            try:
                self.sig_append.emit("CPU test not available")
            except Exception:
                try:
                    self.append_result("CPU test not available")
                except Exception:
                    pass

        # TODO: run RAM, SD and other diagnostics similarly (placeholders for now)
        # Run RAM test with progress
        try:
            from diagnostics.ram import ram_test
        except Exception:
            ram_test = None

        if ram_test:
            self.sig_append.emit("Running RAM test...")

            def _ram_progress(sample):
                try:
                    msg = f"RAM: tested={sample.get('tested_mb',0):.1f}MB chunk={sample.get('chunk_mb',0):.1f}MB"
                    self.sig_append.emit(msg)
                except Exception:
                    pass

            try:
                ram_res = ram_test.run_ram_test(total_mb=128, chunk_mb=16, passes=1, progress_callback=_ram_progress)
                self.sig_append.emit(f"RAM test complete: status={ram_res.get('status')} tested={ram_res.get('tested_mb'):.1f}MB throughput={ram_res.get('throughput_mb_s'):.1f}MB/s")
            except Exception as e:
                self.sig_append.emit(f"RAM test failed: {e}")
        else:
            try:
                self.sig_append.emit("RAM test not available")
            except Exception:
                pass

        # Build report and re-enable button
        report_path = build_sample_report(REPORT_DIR)
        try:
            self.sig_append.emit(f"Full diagnostic complete. Report: {report_path}")
            self.sig_set_button_enabled.emit(True)
        except Exception:
            try:
                self.append_result(f"Full diagnostic complete. Report: {report_path}")
                self.full_btn.setEnabled(True)
            except Exception:
                pass

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
        # Show a QR image for the most recent report (prefer pre-generated QR image)
        try:
            # pick latest HTML or JSON report
            candidates = list(REPORT_DIR.glob('report_*.html')) + list(REPORT_DIR.glob('report_*.json'))
            latest = max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None
            if not latest:
                self.append_result("No report available to generate QR for.")
                return

            base = latest.stem  # e.g. report_1765509939
            qr_dir = REPORT_DIR / 'qrs'
            qr_paths = [qr_dir / f"report_html_{base}.png", qr_dir / f"report_html_path_{base}.png"]
            img_path = None
            for p in qr_paths:
                if p.exists():
                    img_path = p
                    break

            if img_path is None:
                # try to generate a simple file:// QR pointing at the HTML/JSON
                try:
                    import qrcode
                    data = f"file://{str(latest.resolve())}"
                    tmp = Path('/tmp') / f"applepi_qr_{base}.png"
                    img = qrcode.make(data)
                    img.save(str(tmp))
                    img_path = tmp
                except Exception:
                    # fallback: attempt to use QRExportManager to serve and produce a URL
                    try:
                        qm = QRExportManager(str(REPORT_DIR), port=0)
                        url = qm.start()
                        if url:
                            dialog = QRDisplayDialog(url, parent=self)
                            dialog.exec_()
                            return
                    except Exception:
                        pass

            if img_path:
                dialog = QRDisplayDialog(img_path=img_path, parent=self)
                dialog.exec_()
            else:
                self.append_result("Failed to generate or locate QR code for report.")
        except Exception as e:
            self.append_result(f"Error showing QR: {e}")

class IndividualTestsDialog(QtWidgets.QDialog):
    sig_log = QtCore.pyqtSignal(str)
    sig_progress_cpu = QtCore.pyqtSignal(int)
    sig_progress_ram = QtCore.pyqtSignal(int)
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
        # CPU test options (duration seconds, workers 0=auto)
        cpu_opts = QtWidgets.QHBoxLayout()
        cpu_opts.addWidget(QtWidgets.QLabel("Duration (s):"))
        self.cpu_duration_spin = QtWidgets.QSpinBox()
        self.cpu_duration_spin.setRange(1, 600)
        self.cpu_duration_spin.setValue(15)
        cpu_opts.addWidget(self.cpu_duration_spin)

        cpu_opts.addWidget(QtWidgets.QLabel("Workers (0=auto):"))
        self.cpu_workers_spin = QtWidgets.QSpinBox()
        self.cpu_workers_spin.setRange(0, 128)
        self.cpu_workers_spin.setValue(0)
        cpu_opts.addWidget(self.cpu_workers_spin)
        layout.addLayout(cpu_opts)
        # CPU quick button
        cpu_btns = QtWidgets.QHBoxLayout()
        self.cpu_quick_btn = QtWidgets.QPushButton("Run CPU Test")
        cpu_btns.addWidget(self.cpu_quick_btn)
        layout.addLayout(cpu_btns)
        # connect button handler
        try:
            self.cpu_quick_btn.clicked.connect(self._on_cpu_quick_clicked)
        except Exception:
            pass
        # CPU progress + cancel
        self.cpu_progress = QtWidgets.QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)
        self.cpu_cancel_btn = QtWidgets.QPushButton("Cancel CPU")
        cpu_pb_row = QtWidgets.QHBoxLayout()
        cpu_pb_row.addWidget(self.cpu_progress)
        cpu_pb_row.addWidget(self.cpu_cancel_btn)
        layout.addLayout(cpu_pb_row)
        try:
            self.sig_progress_cpu.connect(self.cpu_progress.setValue)
            self.cpu_cancel_btn.clicked.connect(self._on_cpu_cancel_clicked)
        except Exception:
            pass
        layout.addWidget(self.check_ram)
        # RAM options already added; add quick button
        ram_btns = QtWidgets.QHBoxLayout()
        self.ram_quick_btn = QtWidgets.QPushButton("Run RAM Test")
        ram_btns.addWidget(self.ram_quick_btn)
        layout.addLayout(ram_btns)
        try:
            self.ram_quick_btn.clicked.connect(self._on_ram_quick_clicked)
        except Exception:
            pass
        # RAM progress + cancel
        self.ram_progress = QtWidgets.QProgressBar()
        self.ram_progress.setRange(0, 100)
        self.ram_progress.setValue(0)
        self.ram_cancel_btn = QtWidgets.QPushButton("Cancel RAM")
        ram_pb_row = QtWidgets.QHBoxLayout()
        ram_pb_row.addWidget(self.ram_progress)
        ram_pb_row.addWidget(self.ram_cancel_btn)
        layout.addLayout(ram_pb_row)
        try:
            self.sig_progress_ram.connect(self.ram_progress.setValue)
            self.ram_cancel_btn.clicked.connect(self._on_ram_cancel_clicked)
        except Exception:
            pass
        # RAM test options (total MB, chunk MB, passes)
        ram_opts = QtWidgets.QHBoxLayout()
        ram_opts.addWidget(QtWidgets.QLabel("Total MB:"))
        self.ram_total_spin = QtWidgets.QSpinBox()
        self.ram_total_spin.setRange(16, 8192)
        self.ram_total_spin.setValue(128)
        ram_opts.addWidget(self.ram_total_spin)

        ram_opts.addWidget(QtWidgets.QLabel("Chunk MB:"))
        self.ram_chunk_spin = QtWidgets.QSpinBox()
        self.ram_chunk_spin.setRange(1, 2048)
        self.ram_chunk_spin.setValue(16)
        ram_opts.addWidget(self.ram_chunk_spin)

        ram_opts.addWidget(QtWidgets.QLabel("Passes:"))
        self.ram_passes_spin = QtWidgets.QSpinBox()
        self.ram_passes_spin.setRange(1, 10)
        self.ram_passes_spin.setValue(1)
        ram_opts.addWidget(self.ram_passes_spin)
        layout.addLayout(ram_opts)
        layout.addWidget(self.check_sd)

        run_btn = QtWidgets.QPushButton("Run Selected")
        run_btn.clicked.connect(self.run_selected)
        layout.addWidget(run_btn)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        # wire signal to append to the log safely from worker threads
        try:
            self.sig_log.connect(self.log.append)
        except Exception:
            pass
        # running handles for cancellation
        self._cpu_stop_event = None
        self._ram_stop_event = None

    # CPU button handlers
    def _on_cpu_quick_clicked(self):
        try:
            from diagnostics.cpu import cpu_test
        except Exception:
            self.sig_log.emit("CPU test module not available")
            return

        duration = int(self.cpu_duration_spin.value())
        workers = int(self.cpu_workers_spin.value())

        def _run():
            import multiprocessing as _mp
            import time as _time

            stop_ev = _mp.Event()
            self._cpu_stop_event = stop_ev

            start_ts = _time.time()

            def _cb(sample):
                try:
                    avg = sample.get('avg', 0.0)
                    # estimate percent from elapsed vs duration
                    elapsed = max(0.0, sample.get('ts', _time.time()) - start_ts)
                    pct = min(100, int((elapsed / max(1, duration)) * 100))
                    try:
                        self.sig_progress_cpu.emit(pct)
                    except Exception:
                        pass
                    self.sig_log.emit(f"CPU: avg={avg:.1f}%")
                except Exception:
                    pass

            try:
                res = cpu_test.run_cpu_quick_test(duration=duration, workers=(None if workers == 0 else workers), progress_callback=_cb, stop_event=stop_ev)
                self.sig_log.emit(f"CPU quick finished: avg={res.get('avg_cpu_percent',0):.1f}%")
            except Exception as e:
                self.sig_log.emit(f"CPU quick failed: {e}")
            finally:
                # ensure progress shows complete briefly then reset, and clear stop handle
                try:
                    self.sig_progress_cpu.emit(100)
                except Exception:
                    pass
                try:
                    self.sig_progress_cpu.emit(0)
                except Exception:
                    pass
                self._cpu_stop_event = None

        threading.Thread(target=_run, daemon=True).start()

    
    # RAM button handlers
    def _on_ram_quick_clicked(self):
        try:
            from diagnostics.ram import ram_test
        except Exception:
            self.sig_log.emit("RAM test module not available")
            return

        total_mb = int(self.ram_total_spin.value())
        chunk_mb = int(self.ram_chunk_spin.value())
        passes = int(self.ram_passes_spin.value())

        def _run():
            import multiprocessing as _mp
            import time as _time

            stop_ev = _mp.Event()
            self._ram_stop_event = stop_ev
            start_ts = _time.time()

            def _cb(sample):
                try:
                    tested = sample.get('tested_mb', 0.0)
                    pct = min(100, int((tested / max(1, total_mb)) * 100))
                    try:
                        self.sig_progress_ram.emit(pct)
                    except Exception:
                        pass
                    self.sig_log.emit(f"RAM: pass={sample.get('pass',0)} tested={tested:.1f}MB")
                except Exception:
                    pass

            try:
                res = ram_test.run_ram_quick_test(total_mb=total_mb, chunk_mb=chunk_mb, passes=passes, progress_callback=_cb, stop_event=stop_ev)
                self.sig_log.emit(f"RAM quick finished: status={res.get('status')} tested={res.get('tested_mb',0):.1f}MB throughput={res.get('throughput_mb_s',0):.2f}MB/s")
            except Exception as e:
                self.sig_log.emit(f"RAM quick failed: {e}")
            finally:
                try:
                    self.sig_progress_ram.emit(100)
                except Exception:
                    pass
                try:
                    self.sig_progress_ram.emit(0)
                except Exception:
                    pass
                self._ram_stop_event = None

        threading.Thread(target=_run, daemon=True).start()

    
    def _on_cpu_cancel_clicked(self):
        # signal CPU quick to stop
        try:
            if self._cpu_stop_event is not None:
                try:
                    self._cpu_stop_event.set()
                except Exception:
                    pass
        except Exception:
            pass

    def _on_ram_cancel_clicked(self):
        try:
            if self._ram_stop_event is not None:
                try:
                    self._ram_stop_event.set()
                except Exception:
                    pass
        except Exception:
            pass

    def run_selected(self):
        self.log.append("Running selected tests...")
        # CPU: if Run Selected used, default to quick CPU test
        if self.check_cpu.isChecked():
            try:
                from diagnostics.cpu import cpu_test
            except Exception:
                cpu_test = None

            if not cpu_test:
                self.log.append("CPU test module not available")
            else:
                # start quick CPU test as the default action for Run Selected
                duration = int(self.cpu_duration_spin.value())
                workers = int(self.cpu_workers_spin.value())

                def _run_cpu_quick_selected():
                    def _cb(sample):
                        try:
                            avg = sample.get('avg', 0.0)
                            msg = f"CPU: avg={avg:.1f}%"
                            self.sig_log.emit(msg)
                        except Exception:
                            pass

                    try:
                        res = cpu_test.run_cpu_quick_test(duration=duration, workers=(None if workers == 0 else workers), progress_callback=_cb)
                        self.sig_log.emit(f"CPU quick finished: avg={res.get('avg_cpu_percent',0):.1f}%")
                    except Exception as e:
                        self.sig_log.emit(f"CPU quick failed: {e}")

                threading.Thread(target=_run_cpu_quick_selected, daemon=True).start()

        # RAM: run in a background thread and emit progress via sig_log
        if self.check_ram.isChecked():
            try:
                from diagnostics.ram import ram_test
            except Exception:
                ram_test = None

            if not ram_test:
                self.log.append("RAM test module not available")
            else:
                total_mb = int(self.ram_total_spin.value())
                chunk_mb = int(self.ram_chunk_spin.value())
                passes = int(self.ram_passes_spin.value())

                def _run_ram():
                    def _cb(sample):
                        try:
                            msg = f"RAM: pass={sample.get('pass',0)} tested={sample.get('tested_mb',0):.1f}MB chunk={sample.get('chunk_mb',0):.1f}MB"
                            self.sig_log.emit(msg)
                        except Exception:
                            pass

                    try:
                        res = ram_test.run_ram_test(total_mb=total_mb, chunk_mb=chunk_mb, passes=passes, progress_callback=_cb)
                        self.sig_log.emit(f"RAM test finished: status={res.get('status')} tested={res.get('tested_mb',0):.1f}MB throughput={res.get('throughput_mb_s',0):.2f}MB/s")
                    except Exception as e:
                        self.sig_log.emit(f"RAM test failed: {e}")

                thr = threading.Thread(target=_run_ram, daemon=True)
                thr.start()

        # SD placeholder
        if self.check_sd.isChecked():
            self.log.append("SD card test placeholder: OK")

class QRDisplayDialog(QtWidgets.QDialog):
    def __init__(self, url: str | None = None, img_path: Path | str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QR Code - Scan to View Report")
        self.setMinimumSize(420, 480)
        layout = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel("Scan this QR code with your phone to open the report:")
        layout.addWidget(lbl)
        self.qr_label = QtWidgets.QLabel()
        self.qr_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.qr_label, stretch=1)

        pix = None
        # If an image path was provided, use it
        if img_path:
            try:
                pix = QtGui.QPixmap(str(img_path))
            except Exception:
                pix = None

        # If a URL was provided instead, attempt to generate a QR image
        if pix is None and url:
            try:
                from exports.export_qr import generate_qr_image
                img_path2 = generate_qr_image(url, Path('/tmp') / 'applepi_qr.png')
                pix = QtGui.QPixmap(str(img_path2))
            except Exception:
                pix = None

        if pix is not None and not pix.isNull():
            self.qr_label.setPixmap(pix.scaled(360, 360, QtCore.Qt.KeepAspectRatio))
        else:
            self.qr_label.setText('QR image unavailable')


class DetailedResultsDialog(QtWidgets.QDialog):
    """Show per-test detailed JSON/metrics in a dialog."""
    def __init__(self, test_name: str = None, data: object = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detailed Results{(' - ' + test_name) if test_name else ''}")
        self.setMinimumSize(600, 400)
        layout = QtWidgets.QVBoxLayout(self)
        self.text = QtWidgets.QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        btn_row = QtWidgets.QHBoxLayout()
        self.copy_btn = QtWidgets.QPushButton("Copy JSON")
        btn_row.addWidget(self.copy_btn)
        self.close_btn = QtWidgets.QPushButton("Close")
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        self.close_btn.clicked.connect(self.accept)
        self.copy_btn.clicked.connect(self._copy)

        if data is not None:
            try:
                import json as _json
                pretty = _json.dumps(data, indent=2)
            except Exception:
                pretty = str(data)
            self.text.setPlainText(pretty)

    def _copy(self):
        try:
            cb = QtWidgets.QApplication.clipboard()
            cb.setText(self.text.toPlainText())
        except Exception:
            pass


class SettingsDialog(QtWidgets.QDialog):
    """Simple settings: dark mode toggle, font size, QR server port."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(420, 220)
        layout = QtWidgets.QFormLayout(self)

        self.dark_chk = QtWidgets.QCheckBox("Enable dark mode")
        self.dark_chk.setToolTip("Toggle dark theme for the application")
        layout.addRow(self.dark_chk)

        self.font_spin = QtWidgets.QSpinBox()
        self.font_spin.setRange(8, 28)
        self.font_spin.setValue(12)
        self.font_spin.setToolTip("Change base UI font size")
        layout.addRow("Font size:", self.font_spin)

        self.port_spin = QtWidgets.QSpinBox()
        self.port_spin.setRange(0, 65535)
        self.port_spin.setValue(8888)
        self.port_spin.setToolTip("Port for the local report share server (0 for auto)")
        layout.addRow("QR server port:", self.port_spin)

        btn_row = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Save")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addRow(btn_row)

        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)

        # load settings
        try:
            settings = QtCore.QSettings('applepi', 'diagnostics')
            self.dark_chk.setChecked(settings.value('dark', False, type=bool))
            self.font_spin.setValue(settings.value('font_size', 12, type=int))
            self.port_spin.setValue(settings.value('qr_port', 8888, type=int))
        except Exception:
            pass

    def _save(self):
        try:
            settings = QtCore.QSettings('applepi', 'diagnostics')
            settings.setValue('dark', bool(self.dark_chk.isChecked()))
            settings.setValue('font_size', int(self.font_spin.value()))
            settings.setValue('qr_port', int(self.port_spin.value()))
            # apply dark mode immediately (simple stylesheet)
            if self.dark_chk.isChecked():
                qss = "QWidget{background:#222;color:#ddd} QPushButton{background:#333;color:#fff}"
                QtWidgets.QApplication.instance().setStyleSheet(qss)
            else:
                QtWidgets.QApplication.instance().setStyleSheet("")
        except Exception:
            pass
        self.accept()


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
