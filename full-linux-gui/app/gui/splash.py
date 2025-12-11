#!/usr/bin/env python3
# Splash screen module for Apple Pi Diagnostics (Option B: logo + text underneath)

from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore


def _find_logo_filename(name_without_ext="apple_pi_logo"):
    """Search parent folders for an `assets/` dir that contains the logo.

    Looks for common extensions (.png, .ppm, .jpg, .jpeg) starting from
    this file's parent and walking up. Returns a Path or None.
    """
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

class SplashScreen(QtWidgets.QDialog):
    def __init__(self, parent=None, duration_ms=2500):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self.setWindowFlags(
            QtCore.Qt.Dialog
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Logo
        logo_label = QtWidgets.QLabel()
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        if LOGO_PATH and LOGO_PATH.exists():
            pix = QtGui.QPixmap(str(LOGO_PATH))
            # scale preserving aspect ratio
            pix = pix.scaledToWidth(320, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("[Apple Pi Diagnostics]")
            logo_label.setStyleSheet("font-size:20px; font-weight:600;")

        layout.addWidget(logo_label, alignment=QtCore.Qt.AlignCenter)

        # App title text under logo
        title = QtWidgets.QLabel("Apple Pi Diagnostics")
        title.setAlignment(QtCore.Qt.AlignCenter)
        # Use neutral sans stack; if you later add Noto/Inter, change font-family here.
        title.setStyleSheet("""
            font-family: system-ui, 'Noto Sans', 'Inter', Arial, sans-serif;
            font-size: 28px;
            font-weight: 600;
            color: #ffffff;
        """)
        layout.addWidget(title, alignment=QtCore.Qt.AlignCenter)

        # minor footer line (version/place)
        footer = QtWidgets.QLabel("Initializing…")
        footer.setAlignment(QtCore.Qt.AlignCenter)
        footer.setStyleSheet("font-size:12px; color:#ffffff;")
        layout.addWidget(footer, alignment=QtCore.Qt.AlignCenter)

        # center dialog on screen
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        w = min(560, screen.width() - 200)
        h = min(380, screen.height() - 200)
        self.setFixedSize(w, h)
        self.center_on_screen()

    def center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def exec_and_wait(self):
        # show non-blocking then wait using a timer loop
        self.show()
        QtCore.QTimer.singleShot(self.duration_ms, self.accept)
        self.exec_()
