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
        # Start a simple HTTP server to serve report directory and show QR
        qm = QRExportManager(str(REPORT_DIR), port=8888)
        url = qm.start()
        if url:
            dialog = QRDisplayDialog(url, parent=self)
            dialog.exec_()
        else:
            self.append_result("Failed to start QR export server.")

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
        # CPU quick + stress buttons
        cpu_btns = QtWidgets.QHBoxLayout()
        self.cpu_quick_btn = QtWidgets.QPushButton("Run CPU Test")
        self.cpu_stress_btn = QtWidgets.QPushButton("CPU Stress Test")
        cpu_btns.addWidget(self.cpu_quick_btn)
        cpu_btns.addWidget(self.cpu_stress_btn)
        layout.addLayout(cpu_btns)
        # connect button handlers
        try:
            self.cpu_quick_btn.clicked.connect(self._on_cpu_quick_clicked)
            self.cpu_stress_btn.clicked.connect(self._on_cpu_stress_clicked)
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
        # RAM options already added; add quick + stress buttons
        ram_btns = QtWidgets.QHBoxLayout()
        self.ram_quick_btn = QtWidgets.QPushButton("Run RAM Test")
        self.ram_stress_btn = QtWidgets.QPushButton("RAM Stress Test")
        ram_btns.addWidget(self.ram_quick_btn)
        ram_btns.addWidget(self.ram_stress_btn)
        layout.addLayout(ram_btns)
        try:
            self.ram_quick_btn.clicked.connect(self._on_ram_quick_clicked)
            self.ram_stress_btn.clicked.connect(self._on_ram_stress_clicked)
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
        self._cpu_stress_proc = None
        self._ram_stop_event = None
        self._ram_stress_proc = None

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
                # ensure progress shows complete and clear stop handle
                try:
                    self.sig_progress_cpu.emit(100)
                except Exception:
                    pass
                self._cpu_stop_event = None

        threading.Thread(target=_run, daemon=True).start()

    def _on_cpu_stress_clicked(self):
        try:
            from diagnostics.cpu import cpu_test
        except Exception:
            self.sig_log.emit("CPU test module not available")
            return

        duration = int(self.cpu_duration_spin.value())
        workers = int(self.cpu_workers_spin.value())

        def _run():
            import shutil as _shutil
            import subprocess as _subp
            import time as _time

            # prefer using stress-ng directly via Popen so we can cancel it
            if _shutil.which("stress-ng"):
                cmd = ["stress-ng", "--cpu", str(workers if workers and workers > 0 else (_time.time() and workers or '' )).replace('','1'), "--timeout", f"{int(duration)}s"]
                # simpler: compute workers properly
                cpu_count = None
                try:
                    import psutil as _ps
                    cpu_count = _ps.cpu_count(logical=True) or 1
                except Exception:
                    cpu_count = 1
                if workers is None or workers == 0:
                    use_workers = cpu_count
                else:
                    use_workers = workers
                cmd = ["stress-ng", "--cpu", str(use_workers), "--timeout", f"{int(duration)}s", "--metrics-brief"]

                try:
                    proc = _subp.Popen(cmd, stdout=_subp.PIPE, stderr=_subp.PIPE, text=True)
                    self._cpu_stress_proc = proc
                    out, err = proc.communicate()
                    self._cpu_stress_proc = None
                    status = "OK" if proc.returncode == 0 else "FAIL"
                    self.sig_log.emit(f"CPU stress finished: status={status}")
                except Exception as e:
                    self.sig_log.emit(f"CPU stress failed: {e}")
            else:
                # fallback to internal test (with cancel support)
                import multiprocessing as _mp
                stop_ev = _mp.Event()
                self._cpu_stop_event = stop_ev

                def _cb(sample):
                    try:
                        avg = sample.get('avg', 0.0)
                        self.sig_log.emit(f"CPU(stress-fallback): avg={avg:.1f}%")
                    except Exception:
                        pass

                try:
                    res = cpu_test.run_cpu_test(duration=duration, workers=(None if workers == 0 else workers), progress_callback=_cb, stop_event=stop_ev)
                    self.sig_log.emit(f"CPU stress-fallback finished: avg={res.get('avg_cpu_percent',0):.1f}%")
                except Exception as e:
                    self.sig_log.emit(f"CPU stress failed: {e}")
                finally:
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
                self._ram_stop_event = None

        threading.Thread(target=_run, daemon=True).start()

    def _on_ram_stress_clicked(self):
        try:
            from diagnostics.ram import ram_test
        except Exception:
            self.sig_log.emit("RAM test module not available")
            return

        # use ram_quick UI fields to choose parameters for stress-ng wrapper
        total_mb = int(self.ram_total_spin.value())
        chunk_mb = int(self.ram_chunk_spin.value())
        passes = int(self.ram_passes_spin.value())
        workers = 1
        duration = int(self.cpu_duration_spin.value())

        def _run():
            import shutil as _shutil
            import subprocess as _subp

            if _shutil.which("stress-ng"):
                cmd = ["stress-ng", "--vm", "1", "--vm-bytes", f"{int(total_mb)}M", "--timeout", f"{int(duration)}s", "--metrics-brief"]
                try:
                    proc = _subp.Popen(cmd, stdout=_subp.PIPE, stderr=_subp.PIPE, text=True)
                    self._ram_stress_proc = proc
                    out, err = proc.communicate()
                    self._ram_stress_proc = None
                    status = "OK" if proc.returncode == 0 else "FAIL"
                    self.sig_log.emit(f"RAM stress finished: status={status}")
                except Exception as e:
                    self.sig_log.emit(f"RAM stress failed: {e}")
            else:
                # fallback to internal ram test (supports stop_event)
                import multiprocessing as _mp
                stop_ev = _mp.Event()
                self._ram_stop_event = stop_ev

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
                    res = ram_test.run_ram_test(total_mb=total_mb, chunk_mb=chunk_mb, passes=passes, progress_callback=_cb, stop_event=stop_ev)
                    self.sig_log.emit(f"RAM stress-fallback finished: status={res.get('status')} tested={res.get('tested_mb',0):.1f}MB")
                except Exception as e:
                    self.sig_log.emit(f"RAM stress failed: {e}")
                finally:
                    self._ram_stop_event = None

        threading.Thread(target=_run, daemon=True).start()

    def _on_cpu_cancel_clicked(self):
        # signal CPU quick/stress to stop
        try:
            if self._cpu_stop_event is not None:
                try:
                    self._cpu_stop_event.set()
                except Exception:
                    pass
            if getattr(self, '_cpu_stress_proc', None):
                try:
                    proc = self._cpu_stress_proc
                    proc.kill()
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
            if getattr(self, '_ram_stress_proc', None):
                try:
                    proc = self._ram_stress_proc
                    proc.kill()
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
