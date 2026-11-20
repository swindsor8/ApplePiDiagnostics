#!/usr/bin/env python3
"""Centralized theme palettes, QSS stylesheet, and SVG icon helpers for APD."""
from __future__ import annotations

from typing import Dict
from PyQt5 import QtCore, QtGui

THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "name": "dark",
        "bg": "#0d1117",
        "sidebar_bg": "#11161f",
        "surface": "#161b22",
        "surface_alt": "#1c232e",
        "surface_hover": "#212936",
        "border": "#293241",
        "border_strong": "#3b475a",
        "text": "#f0f6fc",
        "text_secondary": "#9da7b3",
        "text_muted": "#6e7681",
        "accent": "#0a84ff",
        "accent_hover": "#409cff",
        "accent_soft": "rgba(10, 132, 255, 0.16)",
        "success": "#30d158",
        "success_soft": "rgba(48, 209, 88, 0.16)",
        "warning": "#ff9f0a",
        "warning_soft": "rgba(255, 159, 10, 0.16)",
        "danger": "#ff453a",
        "danger_hover": "#ff6961",
        "danger_soft": "rgba(255, 69, 58, 0.16)",
        "neutral_soft": "rgba(157, 167, 179, 0.14)",
        "ring_track": "#242c38",
    },
    "light": {
        "name": "light",
        "bg": "#f4f6f9",
        "sidebar_bg": "#ffffff",
        "surface": "#ffffff",
        "surface_alt": "#f8fafc",
        "surface_hover": "#eef4fc",
        "border": "#e2e8f0",
        "border_strong": "#cbd5e1",
        "text": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#64748b",
        "accent": "#0071e3",
        "accent_hover": "#0077ed",
        "accent_soft": "rgba(0, 113, 227, 0.12)",
        "success": "#16a34a",
        "success_soft": "rgba(22, 163, 74, 0.12)",
        "warning": "#d97706",
        "warning_soft": "rgba(217, 119, 6, 0.12)",
        "danger": "#dc2626",
        "danger_hover": "#ef4444",
        "danger_soft": "rgba(220, 38, 38, 0.12)",
        "neutral_soft": "rgba(100, 116, 139, 0.12)",
        "ring_track": "#e2e8f0",
    },
}

SVG_ICONS: Dict[str, str] = {
    "dashboard": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="9" rx="1.5"/>
        <rect x="14" y="3" width="7" height="5" rx="1.5"/>
        <rect x="14" y="12" width="7" height="9" rx="1.5"/>
        <rect x="3" y="16" width="7" height="5" rx="1.5"/>
    </svg>""",
    "diagnostics": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>""",
    "tools": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
    </svg>""",
    "results": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>""",
    "settings": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.85 1 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>""",
    "cpu": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="4" y="4" width="16" height="16" rx="2"/>
        <rect x="9" y="9" width="6" height="6"/>
        <line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/>
        <line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>
        <line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/>
        <line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>
    </svg>""",
    "ram": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="7" width="20" height="10" rx="2"/>
        <line x1="6" y1="7" x2="6" y2="17"/><line x1="10" y1="7" x2="10" y2="17"/>
        <line x1="14" y1="7" x2="14" y2="17"/><line x1="18" y1="7" x2="18" y2="17"/>
        <line x1="6" y1="4" x2="6" y2="7"/><line x1="10" y1="4" x2="10" y2="7"/>
        <line x1="14" y1="4" x2="14" y2="7"/><line x1="18" y1="4" x2="18" y2="7"/>
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
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>""",
    "wifi": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M5 12.55a11 11 0 0 1 14.08 0"/>
        <path d="M1.42 9a16 16 0 0 1 21.16 0"/>
        <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
        <line x1="12" y1="20" x2="12.01" y2="20"/>
    </svg>""",
    "usb": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2v11"/><polyline points="8 6 12 2 16 6"/>
        <circle cx="8" cy="17" r="2"/><circle cx="16" cy="15" r="2"/>
        <path d="M12 13H8a2 2 0 0 0-2 2v2"/><path d="M12 13h4a2 2 0 0 0 2-2v-2"/>
    </svg>""",
    "hdmi": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="3" width="20" height="13" rx="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="16" x2="12" y2="21"/>
    </svg>""",
    "gpio": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="5" y="2" width="14" height="20" rx="2"/>
        <circle cx="9.5" cy="6.5" r="1"/><circle cx="14.5" cy="6.5" r="1"/>
        <circle cx="9.5" cy="12" r="1"/><circle cx="14.5" cy="12" r="1"/>
        <circle cx="9.5" cy="17.5" r="1"/><circle cx="14.5" cy="17.5" r="1"/>
    </svg>""",
    "power": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>""",
    "bootloader": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>""",
    "peripherals": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="7" width="20" height="10" rx="2"/>
        <circle cx="7" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/>
        <circle cx="17" cy="12" r="1.5"/>
    </svg>""",
    "sun": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>""",
    "moon": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>""",
    "reboot": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="23 4 23 10 17 10"/>
        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
    </svg>""",
    "shutdown": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>
        <line x1="12" y1="2" x2="12" y2="12"/>
    </svg>""",
    "qr": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
        <rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3h-3z"/><path d="M18 18h3v3h-3z"/>
    </svg>""",
    "play": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>""",
}


def make_svg_pixmap(icon_key: str, size: int = 20, color: str = "#9da7b3"):
    """Render a named SVG icon to a QPixmap at the requested size and color."""
    svg_str = SVG_ICONS.get(icon_key, "")
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


def make_svg_icon(icon_key: str, size: int = 18, color: str = "#9da7b3") -> QtGui.QIcon:
    pix = make_svg_pixmap(icon_key, size=size, color=color)
    return QtGui.QIcon(pix) if pix else QtGui.QIcon()


def build_stylesheet(theme_name: str = "dark") -> str:
    """Build the complete application stylesheet for the requested theme."""
    t = THEMES.get(theme_name, THEMES["dark"])
    return f"""
    QMainWindow, QDialog {{
        background-color: {t["bg"]};
        color: {t["text"]};
        font-family: 'Inter', 'Noto Sans', 'DejaVu Sans', system-ui, sans-serif;
    }}
    QWidget {{
        color: {t["text"]};
        font-family: 'Inter', 'Noto Sans', 'DejaVu Sans', system-ui, sans-serif;
    }}
    QWidget#AppRoot {{
        background-color: {t["bg"]};
    }}
    QWidget#Sidebar {{
        background-color: {t["sidebar_bg"]};
        border-right: 1px solid {t["border"]};
    }}
    QWidget#TopBar {{
        background-color: {t["sidebar_bg"]};
        border-bottom: 1px solid {t["border"]};
    }}
    QWidget#Card, QFrame#Card {{
        background-color: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 14px;
    }}
    QWidget#CardInteractive {{
        background-color: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 14px;
    }}
    QWidget#CardInteractive:hover {{
        border: 1px solid {t["accent"]};
        background-color: {t["surface_hover"]};
    }}
    QWidget#HeroCard {{
        background-color: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 16px;
    }}
    QLabel {{
        background: transparent;
    }}
    QLabel#PageTitle {{
        font-size: 22px;
        font-weight: 700;
        color: {t["text"]};
    }}
    QLabel#PageSubtitle {{
        font-size: 13px;
        color: {t["text_secondary"]};
    }}
    QLabel#SectionHeading {{
        font-size: 15px;
        font-weight: 700;
        color: {t["text"]};
    }}
    QLabel#MutedLabel {{
        font-size: 12px;
        color: {t["text_secondary"]};
    }}
    QLabel#KeyLabel {{
        font-size: 12px;
        font-weight: 600;
        color: {t["text_secondary"]};
    }}
    QLabel#ValueLabel {{
        font-size: 13px;
        font-weight: 500;
        color: {t["text"]};
    }}
    QLabel#VersionPill {{
        font-size: 11px;
        font-weight: 700;
        color: {t["accent"]};
        background-color: {t["accent_soft"]};
        border: 1px solid {t["accent"]};
        border-radius: 9px;
        padding: 2px 8px;
    }}
    QPushButton#NavButton {{
        background-color: transparent;
        color: {t["text_secondary"]};
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        text-align: left;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton#NavButton:hover {{
        background-color: {t["surface_hover"]};
        color: {t["text"]};
    }}
    QPushButton#NavButton[active="true"] {{
        background-color: {t["accent_soft"]};
        color: {t["accent"]};
    }}
    QPushButton#PrimaryButton {{
        background-color: {t["accent"]};
        color: #ffffff;
        border: none;
        border-radius: 9px;
        padding: 9px 18px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
        background-color: {t["accent_hover"]};
    }}
    QPushButton#PrimaryButton:disabled {{
        background-color: {t["border"]};
        color: {t["text_muted"]};
    }}
    QPushButton#SecondaryButton {{
        background-color: {t["surface_alt"]};
        color: {t["text"]};
        border: 1px solid {t["border_strong"]};
        border-radius: 9px;
        padding: 8px 14px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton#SecondaryButton:hover {{
        background-color: {t["surface_hover"]};
        border-color: {t["accent"]};
    }}
    QPushButton#SecondaryButton:disabled {{
        color: {t["text_muted"]};
        border-color: {t["border"]};
    }}
    QPushButton#DangerButton {{
        background-color: {t["danger_soft"]};
        color: {t["danger"]};
        border: 1px solid {t["danger"]};
        border-radius: 9px;
        padding: 8px 14px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton#DangerButton:hover {{
        background-color: {t["danger"]};
        color: #ffffff;
    }}
    QPushButton#FilterPill {{
        background-color: {t["surface"]};
        color: {t["text_secondary"]};
        border: 1px solid {t["border"]};
        border-radius: 14px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton#FilterPill:hover {{
        border-color: {t["accent"]};
        color: {t["text"]};
    }}
    QPushButton#FilterPill[active="true"] {{
        background-color: {t["accent"]};
        color: #ffffff;
        border-color: {t["accent"]};
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t["border_strong"]};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QTextEdit, QTextBrowser, QListWidget, QLineEdit {{
        background-color: {t["surface_alt"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        border-radius: 10px;
        padding: 8px;
        font-size: 13px;
    }}
    QLineEdit:focus, QListWidget:focus {{
        border-color: {t["accent"]};
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 6px;
    }}
    QListWidget::item:selected {{
        background-color: {t["accent_soft"]};
        color: {t["accent"]};
    }}
    QProgressBar {{
        background-color: {t["ring_track"]};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {t["accent"]};
        border-radius: 4px;
    }}
    QStatusBar {{
        background-color: {t["sidebar_bg"]};
        color: {t["text_secondary"]};
        border-top: 1px solid {t["border"]};
        font-size: 12px;
    }}
    QMessageBox {{
        background-color: {t["surface"]};
        color: {t["text"]};
    }}
    """
