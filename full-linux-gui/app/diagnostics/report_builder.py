#!/usr/bin/env python3
from pathlib import Path
import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def build_sample_report(report_dir: Path):
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    pdf_path = report_dir / f"report_{timestamp}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 700, "Apple Pi Diagnostics - Sample Report")
    c.drawString(100, 680, f"Generated: {time.ctime(timestamp)}")
    c.drawString(100, 660, "CPU: OK")
    c.drawString(100, 640, "RAM: OK")
    c.drawString(100, 620, "SD: OK")
    c.save()
    return pdf_path
