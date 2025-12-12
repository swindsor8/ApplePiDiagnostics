#!/usr/bin/env python3
"""Report builder for Apple Pi Diagnostics.

Exports reports in JSON, HTML (mobile-friendly), and PDF with embedded logo
and system metadata. The main entry is `build_report(report_data, out_dir, formats)`.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import platform
import socket
import time
import tempfile
from typing import Dict, Any, Optional, Sequence

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import urllib.parse

try:
    import qrcode
    QR_SUPPORTED = True
except Exception:
    QR_SUPPORTED = False


# Try to reuse the splash's logo discovery; fall back gracefully if unavailable
try:
    from gui.splash import LOGO_PATH
except Exception:
    LOGO_PATH = None


def _prepare_logo_for_pdf() -> Optional[str]:
    """Return a PNG path suitable for embedding in PDFs (may be temp file).

    If `LOGO_PATH` points to PNG/JPG we return it. Otherwise attempt a Pillow
    conversion. Returns None on failure.
    """
    if not LOGO_PATH:
        return None
    p = Path(LOGO_PATH)
    if not p.exists():
        return None
    if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return str(p)
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


def _collect_system_metadata() -> Dict[str, Any]:
    md: Dict[str, Any] = {}
    md["timestamp"] = time.time()
    md["generated"] = time.ctime(md["timestamp"])
    md["hostname"] = socket.gethostname()
    md["platform"] = platform.platform()
    md["python"] = platform.python_version()
    # attempt to read /etc/os-release for a nicer OS string
    try:
        out = {}
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for ln in f:
                if "=" in ln:
                    k, v = ln.strip().split("=", 1)
                    out[k] = v.strip('"')
        md["os_release"] = out
    except Exception:
        md["os_release"] = None
    # attempt to read Pi model information
    try:
        if Path("/proc/device-tree/model").exists():
            md["pi_model"] = Path("/proc/device-tree/model").read_text(errors="ignore").strip('\x00\n')
        else:
            md["pi_model"] = None
    except Exception:
        md["pi_model"] = None

    return md


def _write_json_report(report: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path


def _write_html_report(report: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # mobile-friendly single-page HTML with basic CSS and JSON embed
    title = report.get("title", "Apple Pi Diagnostics Report")
    meta = report.get("metadata", {})
    summary = report.get("summary", {})
    details = report.get("details", {})

    css = """
    body{font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial; padding:1rem;}
    header{display:flex;align-items:center;gap:10px}
    img.logo{width:48px;height:48px}
    .meta{font-size:0.9rem;color:#444}
    .card{border:1px solid #eee;padding:0.75rem;margin:0.5rem 0;border-radius:8px}
    pre.json{white-space:pre-wrap;word-break:break-word;background:#f8f8f8;padding:0.5rem;border-radius:6px}
    @media (max-width:420px){body{padding:0.5rem}}"""

    logo_tag = ""
    logo_path = _prepare_logo_for_pdf()
    if logo_path:
        # use file:// URL for local viewing
        logo_tag = f"<img class=\"logo\" src=\"file://{logo_path}\" alt=\"logo\">"

    html = ["<!doctype html>", "<html><head>", f"<title>{title}</title>", f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">", f"<style>{css}</style>", "</head><body>"]
    html.append(f"<header><div>{logo_tag}</div><div><h1>{title}</h1><div class=\"meta\">Generated: {meta.get('generated')}</div></div></header>")
    html.append("<section class=\"card\"><h2>Summary</h2>")
    for k, v in summary.items():
        html.append(f"<div><strong>{k}:</strong> {v}</div>")
    html.append("</section>")

    html.append("<section class=\"card\"><h2>Details</h2>")
    for test, data in details.items():
        html.append(f"<h3>{test}</h3>")
        html.append(f"<pre class=\"json\">{json.dumps(data, indent=2)}</pre>")
    html.append("</section>")

    html.append("<section class=\"card\"><h2>Full JSON</h2>")
    html.append(f"<pre class=\"json\">{json.dumps(report, indent=2)}</pre>")
    html.append("</section>")

    html.append("</body></html>")
    out_path.write_text('\n'.join(html), encoding="utf-8")
    return out_path


def _write_pdf_report(report: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=letter)
    width, height = letter

    logo_png = _prepare_logo_for_pdf()
    if logo_png:
        try:
            c.drawImage(logo_png, 50, height - 80, width=64, height=64, mask='auto')
        except Exception:
            pass

    title_x = 130 if logo_png else 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(title_x, height - 50, report.get("title", "Apple Pi Diagnostics Report"))
    c.setFont("Helvetica", 9)
    meta = report.get("metadata", {})
    c.drawString(title_x, height - 68, f"Generated: {meta.get('generated','')}")
    # metadata block
    y = height - 100
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "System Metadata")
    y -= 14
    c.setFont("Helvetica", 9)
    for k, v in meta.items():
        if y < 72:
            c.showPage()
            y = height - 50
        c.drawString(60, y, f"{k}: {str(v)}")
        y -= 12

    # summary
    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Summary")
    y -= 14
    c.setFont("Helvetica", 10)
    for k, v in report.get("summary", {}).items():
        if y < 72:
            c.showPage()
            y = height - 50
        c.drawString(60, y, f"{k}: {v}")
        y -= 12

    # details per test
    for test, data in report.get("details", {}).items():
        if y < 140:
            c.showPage()
            y = height - 50
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"{test}")
        y -= 14
        c.setFont("Helvetica", 9)
        text = json.dumps(data, indent=2)
        for line in text.splitlines():
            if y < 72:
                c.showPage()
                y = height - 50
            c.drawString(60, y, line[:100])
            y -= 10

    c.save()
    return out_path


def build_report(report_data: Dict[str, Any], out_dir: Path, formats: Sequence[str] = ("pdf", "html", "json")) -> Dict[str, Path]:
    """Build report in requested formats and return paths.

    `report_data` should include keys `summary` and `details` (dict of test name->data).
    The function will add `metadata` and `title` if missing.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = dict(report_data)  # shallow copy
    report.setdefault("title", "Apple Pi Diagnostics Report")
    report.setdefault("metadata", _collect_system_metadata())
    # ensure timestamps consistent
    report["metadata"].setdefault("generated", time.ctime(report["metadata"]["timestamp"]))

    results: Dict[str, Path] = {}
    base = out_dir / f"report_{int(time.time())}"
    if "json" in formats:
        p = _write_json_report(report, base.with_suffix(".json"))
        results["json"] = p
    if "html" in formats:
        p = _write_html_report(report, base.with_suffix(".html"))
        results["html"] = p
    if "pdf" in formats:
        p = _write_pdf_report(report, base.with_suffix(".pdf"))
        results["pdf"] = p

    # optionally generate QR codes pointing at the HTML or embedding the JSON
    if "qr" in formats:
        try:
            _qr_dir = out_dir / "qrs"
            _qr_dir.mkdir(parents=True, exist_ok=True)
            # HTML QR: prefer embedding html data if small, else point to file path
            if "html" in results:
                html_path = results["html"].resolve()
                html_text = html_path.read_text(encoding="utf-8")
                if QR_SUPPORTED:
                    if len(html_text) < 1500:
                        # embed as data URL
                        data_url = "data:text/html;utf-8," + urllib.parse.quote(html_text)
                        img = qrcode.make(data_url)
                        out_q = _qr_dir / f"report_html_{base.name}.png"
                        img.save(str(out_q))
                        results["qr_html"] = out_q
                    else:
                        data = f"file://{str(html_path)}"
                        img = qrcode.make(data)
                        out_q = _qr_dir / f"report_html_path_{base.name}.png"
                        img.save(str(out_q))
                        results["qr_html"] = out_q
                else:
                    # QR not available; write small helper file indicating how to open
                    results["qr_html"] = None

            # JSON QR: embed JSON if small
            if "json" in results:
                json_path = results["json"].resolve()
                jtext = json_path.read_text(encoding="utf-8")
                if QR_SUPPORTED and len(jtext) < 1200:
                    data = "data:application/json;utf-8," + urllib.parse.quote(jtext)
                    img = qrcode.make(data)
                    out_q = _qr_dir / f"report_json_{base.name}.png"
                    img.save(str(out_q))
                    results["qr_json"] = out_q
                else:
                    results["qr_json"] = None
        except Exception:
            # QR failures are non-fatal
            pass

    return results


if __name__ == "__main__":
    # quick local smoke test producing all three formats using sample data
    import json as _json
    sample = {
        "summary": {"CPU": "OK", "RAM": "OK", "SD": "OK"},
        "details": {
            "cpu": {"avg_cpu_percent": 12.3},
            "ram": {"tested_mb": 64, "throughput_mb_s": 120.5},
        },
    }
    out = build_report(sample, Path.cwd() / "reports" / "sample_report", formats=("json", "html", "pdf"))
    print({k: str(v) for k, v in out.items()})
