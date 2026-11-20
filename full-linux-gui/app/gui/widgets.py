#!/usr/bin/env python3
"""Custom modern PyQt5 widgets for Apple Pi Diagnostics."""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets
from gui.theme import THEMES, make_svg_pixmap


class HealthRingWidget(QtWidgets.QWidget):
    """Smooth circular health ring displaying overall diagnostic pass rate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(128, 128)
        self._passed = 0
        self._total = 0
        self._failed = 0
        self._warnings = 0
        self._theme = THEMES["dark"]

    def set_theme(self, theme_name: str):
        self._theme = THEMES.get(theme_name, THEMES["dark"])
        self.update()

    def set_counts(self, passed: int, warnings: int, failed: int, total: int):
        self._passed = passed
        self._warnings = warnings
        self._failed = failed
        self._total = total
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = QtCore.QRectF(12, 12, self.width() - 24, self.height() - 24)
        pen_w = 10

        # Track
        track_pen = QtGui.QPen(QtGui.QColor(self._theme["ring_track"]), pen_w)
        track_pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Progress arc
        if self._total > 0:
            completed = self._passed + self._warnings + self._failed
            ratio = min(1.0, max(0.0, completed / float(self._total)))
            if self._failed > 0:
                arc_color = self._theme["danger"]
            elif self._warnings > 0:
                arc_color = self._theme["warning"]
            else:
                arc_color = self._theme["success"]

            if ratio > 0:
                arc_pen = QtGui.QPen(QtGui.QColor(arc_color), pen_w)
                arc_pen.setCapStyle(QtCore.Qt.RoundCap)
                painter.setPen(arc_pen)
                painter.drawArc(rect, 90 * 16, int(-ratio * 360 * 16))

        # Center text
        if self._total == 0 or (self._passed + self._warnings + self._failed) == 0:
            big_text = "Ready"
            sub_text = "No tests yet"
        else:
            big_text = f"{self._passed}/{self._total}"
            sub_text = (
                f"{self._failed} failed" if self._failed
                else f"{self._warnings} warn" if self._warnings
                else "Healthy"
            )

        painter.setPen(QtGui.QColor(self._theme["text"]))
        painter.setFont(QtGui.QFont("Sans", 18, QtGui.QFont.Bold))
        painter.drawText(
            QtCore.QRectF(0, 32, self.width(), 34),
            QtCore.Qt.AlignCenter,
            big_text,
        )

        painter.setPen(QtGui.QColor(self._theme["text_secondary"]))
        painter.setFont(QtGui.QFont("Sans", 10))
        painter.drawText(
            QtCore.QRectF(0, 68, self.width(), 24),
            QtCore.Qt.AlignCenter,
            sub_text,
        )
        painter.end()


class TelemetryTile(QtWidgets.QFrame):
    """Live telemetry card with icon, bold metric value, subtext, and gauge bar."""

    def __init__(self, title: str, icon_key: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.icon_key = icon_key
        self._theme = THEMES["dark"]
        self._build_ui(title)

    def _build_ui(self, title: str):
        self.setMinimumHeight(104)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        self.icon_lbl = QtWidgets.QLabel()
        self.icon_lbl.setFixedSize(18, 18)
        top.addWidget(self.icon_lbl)

        self.title_lbl = QtWidgets.QLabel(title)
        self.title_lbl.setObjectName("KeyLabel")
        top.addWidget(self.title_lbl)
        top.addStretch()
        layout.addLayout(top)

        self.value_lbl = QtWidgets.QLabel("—")
        self.value_lbl.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(self.value_lbl)

        self.sub_lbl = QtWidgets.QLabel("")
        self.sub_lbl.setObjectName("MutedLabel")
        layout.addWidget(self.sub_lbl)

        self.bar = QtWidgets.QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(5)
        layout.addWidget(self.bar)

    def set_theme(self, theme_name: str):
        self._theme = THEMES.get(theme_name, THEMES["dark"])
        pix = make_svg_pixmap(self.icon_key, size=18, color=self._theme["accent"])
        if pix:
            self.icon_lbl.setPixmap(pix)

    def update_metric(self, value: str, subtext: str = "", percent: int = 0, tone: str = "accent"):
        self.value_lbl.setText(value)
        self.sub_lbl.setText(subtext)
        self.bar.setValue(max(0, min(100, int(percent))))
        color = self._theme.get(tone, self._theme["accent"])
        self.bar.setStyleSheet(
            f"QProgressBar {{ background-color: {self._theme['ring_track']}; border: none; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )


class DiagnosticCard(QtWidgets.QFrame):
    """Spacious, responsive diagnostic module card with status pill and icon badge."""

    def __init__(self, title: str, subtitle: str, icon_key: str, category: str = "Core", parent=None):
        super().__init__(parent)
        self.setObjectName("CardInteractive")
        self.title = title
        self.subtitle = subtitle
        self.icon_key = icon_key
        self.category = category
        self.status = "PENDING"
        self.details = ""
        self._theme = THEMES["dark"]
        self._build_ui()

    def _build_ui(self):
        self.setMinimumSize(210, 178)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        # Header row: icon badge + title/subtitle + status pill
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(10)

        self.icon_badge = QtWidgets.QLabel()
        self.icon_badge.setFixedSize(36, 36)
        self.icon_badge.setAlignment(QtCore.Qt.AlignCenter)
        top.addWidget(self.icon_badge)

        title_col = QtWidgets.QVBoxLayout()
        title_col.setSpacing(1)
        self.title_lbl = QtWidgets.QLabel(self.title)
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.sub_lbl = QtWidgets.QLabel(self.subtitle)
        self.sub_lbl.setObjectName("MutedLabel")
        title_col.addWidget(self.title_lbl)
        title_col.addWidget(self.sub_lbl)
        top.addLayout(title_col, stretch=1)
        layout.addLayout(top)

        # Status pill row
        pill_row = QtWidgets.QHBoxLayout()
        self.status_pill = QtWidgets.QLabel("○ Pending")
        self.status_pill.setAlignment(QtCore.Qt.AlignCenter)
        pill_row.addWidget(self.status_pill)
        pill_row.addStretch()
        layout.addLayout(pill_row)

        # Details
        self.details_label = QtWidgets.QLabel("Ready to run")
        self.details_label.setObjectName("MutedLabel")
        self.details_label.setWordWrap(True)
        self.details_label.setMinimumHeight(30)
        layout.addWidget(self.details_label)

        layout.addStretch()

        # Run button
        self.test_btn = QtWidgets.QPushButton("Run Test")
        self.test_btn.setObjectName("SecondaryButton")
        self.test_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        layout.addWidget(self.test_btn)

        self.set_theme("dark")

    def set_theme(self, theme_name: str):
        self._theme = THEMES.get(theme_name, THEMES["dark"])
        self._refresh_visuals()

    def _refresh_visuals(self):
        t = self._theme
        s = self.status.upper()
        if s in ("OK", "PASS"):
            fg, bg, label = t["success"], t["success_soft"], "✓ Passed"
        elif s in ("FAIL", "ERROR"):
            fg, bg, label = t["danger"], t["danger_soft"], "✗ Failed"
        elif s == "WARNING":
            fg, bg, label = t["warning"], t["warning_soft"], "⚠ Warning"
        elif s == "UNSUPPORTED":
            fg, bg, label = t["warning"], t["warning_soft"], "— Unsupported"
        elif s == "RUNNING":
            fg, bg, label = t["accent"], t["accent_soft"], "⟳ Running…"
        else:
            fg, bg, label = t["text_secondary"], t["neutral_soft"], "○ Pending"

        self.icon_badge.setStyleSheet(
            f"background-color: {bg}; border-radius: 10px;"
        )
        pix = make_svg_pixmap(self.icon_key, size=20, color=fg if s != "PENDING" else t["accent"])
        if pix:
            self.icon_badge.setPixmap(pix)

        self.status_pill.setText(label)
        self.status_pill.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {fg}; "
            f"background-color: {bg}; border-radius: 10px; padding: 3px 10px;"
        )

    @QtCore.pyqtSlot(str, str)
    def set_status(self, status: str, details: str = ""):
        self.status = status
        self.details = details
        self._refresh_visuals()
        if details:
            shown = details if len(details) <= 84 else details[:81] + "…"
            self.details_label.setText(shown)
            self.details_label.setToolTip(details)
        else:
            self.details_label.setText("Ready to run" if status == "PENDING" else "")
            self.details_label.setToolTip("")


class ToolActionCard(QtWidgets.QFrame):
    """Large feature card on the Hardware Tools page."""

    def __init__(self, title: str, description: str, button_text: str, icon_key: str, parent=None):
        super().__init__(parent)
        self.setObjectName("CardInteractive")
        self.icon_key = icon_key
        self._theme = THEMES["dark"]

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.icon_badge = QtWidgets.QLabel()
        self.icon_badge.setFixedSize(44, 44)
        self.icon_badge.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.icon_badge)

        t_lbl = QtWidgets.QLabel(title)
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(t_lbl)

        d_lbl = QtWidgets.QLabel(description)
        d_lbl.setObjectName("MutedLabel")
        d_lbl.setWordWrap(True)
        layout.addWidget(d_lbl)

        layout.addStretch()

        self.action_btn = QtWidgets.QPushButton(button_text)
        self.action_btn.setObjectName("PrimaryButton")
        self.action_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        layout.addWidget(self.action_btn)

        self.set_theme("dark")

    def set_theme(self, theme_name: str):
        self._theme = THEMES.get(theme_name, THEMES["dark"])
        self.icon_badge.setStyleSheet(
            f"background-color: {self._theme['accent_soft']}; border-radius: 12px;"
        )
        pix = make_svg_pixmap(self.icon_key, size=24, color=self._theme["accent"])
        if pix:
            self.icon_badge.setPixmap(pix)
