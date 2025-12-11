#!/usr/bin/env python3
from pathlib import Path
import time
import tempfile
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Try to reuse the splash's logo discovery; fall back gracefully if unavailable
try:
    from gui.splash import LOGO_PATH
except Exception:
    LOGO_PATH = None


def _prepare_logo_for_pdf():
    """Return a file path to a PNG suitable for embedding in the PDF.

    If the discovered logo is already a PNG or JPG, return it. If it's in
    another format (e.g. PPM) convert it to a temp PNG using Pillow.
    Returns None if no logo is available.
    """
    if not LOGO_PATH:
        return None
    p = Path(LOGO_PATH)
    if not p.exists():
        return None
    # If already PNG/JPEG, return as-is
    if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return str(p)

    # Otherwise convert to a temporary PNG using Pillow
    try:
        from PIL import Image
    except Exception:
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()
    try:
        img = Image.open(str(p))
        img.save(tmp.name, format="PNG")
        return tmp.name
    except Exception:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        return None


def build_sample_report(report_dir: Path):
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    pdf_path = report_dir / f"report_{timestamp}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)

    # Draw logo if available
    logo_png = _prepare_logo_for_pdf()
    if logo_png:
        try:
            # place at top-left; reportlab origin is bottom-left
            # letter height is 792, so y ~ 720 places near top
            c.drawImage(logo_png, 50, 720, width=64, height=64, mask='auto')
        except Exception:
            pass

    # Title beside the logo (or left-aligned if no logo)
    title_x = 130 if logo_png else 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(title_x, 760, "Apple Pi Diagnostics - Sample Report")
    c.setFont("Helvetica", 10)
    c.drawString(title_x, 742, f"Generated: {time.ctime(timestamp)}")
    c.drawString(50, 700, "CPU: OK")
    c.drawString(50, 680, "RAM: OK")
    c.drawString(50, 660, "SD: OK")
    c.save()

    # If we created a temporary PNG, we should try to remove it next run; leaving
    # it ensures the PDF generation succeeds, caller can clean tmp if needed.
    return pdf_path
