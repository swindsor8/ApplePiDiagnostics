#!/usr/bin/env python3
"""Report builder for Apple Pi Diagnostics.

Produces PDF, HTML, and JSON reports using plain-English summaries.
The main entry point is `build_report(report_data, out_dir, formats)`.
"""
from __future__ import annotations

from pathlib import Path
import html
import json
import os
import platform
import socket
import time
import tempfile
from typing import Dict, Any, Optional, Sequence, List, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, KeepTogether, Image as RLImage,
)

try:
    import qrcode
    QR_SUPPORTED = True
except Exception:
    QR_SUPPORTED = False

try:
    from gui.splash import LOGO_PATH
except Exception:
    LOGO_PATH = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prepare_logo_for_pdf() -> Optional[str]:
    """Return a PNG path suitable for embedding in PDFs, or None."""
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
    tmp_dir = tempfile.mkdtemp(suffix="_apd_logo")
    tmp_path = os.path.join(tmp_dir, "logo.png")
    try:
        Image.open(str(p)).save(tmp_path, format="PNG")
        return tmp_path
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        try:
            os.rmdir(tmp_dir)
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
    try:
        if Path("/proc/device-tree/model").exists():
            md["pi_model"] = Path("/proc/device-tree/model").read_text(errors="ignore").strip('\x00\n')
        else:
            md["pi_model"] = None
    except Exception:
        md["pi_model"] = None
    return md


# ---------------------------------------------------------------------------
# Plain-English summariser  (mirrors the GUI's _summarize_result)
# ---------------------------------------------------------------------------

def _summarize_test(test_id: str, result: Dict[str, Any]) -> List[str]:
    """Return a list of plain-English sentences describing a single test result."""
    lines: List[str] = []

    if test_id == "cpu":
        avg = result.get("avg_cpu_percent")
        if avg is not None:
            lines.append(f"CPU averaged {avg:.1f}% load during the test.")
        workers = result.get("workers")
        if workers:
            lines.append(f"Used {workers} worker thread{'s' if workers != 1 else ''}.")
        temp = result.get("max_temperature")
        if temp is not None:
            lines.append(f"Peak temperature: {temp:.0f} \u00b0C.")
        per_cpu = result.get("per_cpu_percent", [])
        if per_cpu:
            lines.append(f"Per-core load: {', '.join(f'{v:.0f}%' for v in per_cpu)}.")

    elif test_id == "ram":
        tested = result.get("tested_mb")
        if tested is not None:
            lines.append(f"Tested {tested:.0f} MB of RAM.")
        errors = result.get("errors", [])
        if errors:
            # Strip file-path-like tokens from error strings before embedding in reports.
            def _sanitize_err(msg: str) -> str:
                import re
                return re.sub(r'/\S+', '[path]', str(msg))
            lines.append(f"Errors found: {'; '.join(_sanitize_err(e) for e in errors[:3])}.")
        else:
            lines.append("No memory errors detected.")
        tp = result.get("throughput_mb_s")
        if tp is not None:
            lines.append(f"Throughput: {tp:.0f} MB/s.")

    elif test_id == "sd":
        total = result.get("total_devices", 0)
        tested_d = result.get("tested_devices", 0)
        lines.append(f"Found {total} storage device{'s' if total != 1 else ''}; tested {tested_d}.")
        for dev in result.get("devices", []):
            name = dev.get("device", "?")
            size = dev.get("size_gb")
            fs = dev.get("fstype", "unknown fs")
            dev_status = dev.get("status", "?")
            w = dev.get("write_mb_s")
            r = dev.get("read_mb_s")
            note = dev.get("note", "")
            size_str = f"{size:.0f} GB, " if size else ""
            if w is not None and r is not None:
                speed = f" \u2014 {w:.0f} MB/s write, {r:.0f} MB/s read"
            elif note:
                speed = f" \u2014 {note}"
            else:
                speed = ""
            lines.append(f"{name} ({size_str}{fs}): {dev_status}{speed}.")

    elif test_id == "network":
        local_ip = result.get("local_ip")
        if local_ip:
            lines.append(f"Local IP address: {local_ip}.")
        up_ifaces = [i["name"] for i in result.get("interfaces", []) if i.get("up")]
        if up_ifaces:
            lines.append(f"Active interfaces: {', '.join(up_ifaces)}.")
        dns = result.get("dns", {})
        if dns.get("ok"):
            lat = dns.get("latency_s")
            lat_str = f" ({lat * 1000:.0f} ms)" if lat is not None else ""
            lines.append(f"DNS resolution OK{lat_str}.")
        elif dns:
            lines.append(f"DNS resolution failed: {dns.get('note', '')}.")
        ok_pings = [p["host"] for p in result.get("ping", []) if p.get("ok")]
        fail_pings = [p["host"] for p in result.get("ping", []) if not p.get("ok")]
        if ok_pings:
            lines.append(f"Ping OK to: {', '.join(ok_pings)}.")
        if fail_pings:
            lines.append(f"Ping failed to: {', '.join(fail_pings)}.")

    elif test_id == "usb":
        count = result.get("count")
        if count is not None:
            lines.append(f"Found {count} USB device{'s' if count != 1 else ''}.")
        for d in result.get("devices", [])[:5]:
            lines.append(f"  \u2022 {d}")
        extra = len(result.get("devices", [])) - 5
        if extra > 0:
            lines.append(f"  \u2026 and {extra} more.")
        note = result.get("note", "")
        if note and result.get("status") != "OK":
            lines.append(note)
        w = result.get("write_mb_s")
        r = result.get("read_mb_s")
        if w is not None and r is not None:
            lines.append(f"Speed test: {w:.0f} MB/s write, {r:.0f} MB/s read.")

    elif test_id == "hdmi":
        count = result.get("count")
        if count is not None:
            lines.append(f"{count} display{'s' if count != 1 else ''} connected.")
        for d in result.get("displays", []):
            name = d.get("name", "Unknown")
            res = d.get("resolution", "")
            lines.append(f"  \u2022 {name}{': ' + res if res else ''}.")
        note = result.get("note", "")
        if note:
            lines.append(note)

    elif test_id == "gpio":
        driver = result.get("driver", "")
        note = result.get("note", "")
        if driver:
            lines.append(f"GPIO driver: {driver}.")
        if note:
            lines.append(note)
        gpio_results = result.get("results", [])
        if gpio_results:
            passed = sum(1 for r in gpio_results if r)
            lines.append(f"Loopback: {passed}/{len(gpio_results)} pulses verified.")

    else:
        note = result.get("note", result.get("error", ""))
        if note:
            lines.append(note)

    if not lines:
        lines.append("No details available.")

    return lines


def _status_label(status: str) -> Tuple[str, str]:
    """Return (display text, hex colour) for a status string."""
    s = status.upper()
    if s in ("OK", "PASS"):
        return "Passed", "#1a8a4a"
    if s in ("FAIL", "ERROR"):
        return "Failed", "#cc2200"
    if s == "UNSUPPORTED":
        return "Not supported", "#b06000"
    if s == "RUNNING":
        return "Running", "#0066cc"
    return "Pending", "#666666"


_TEST_LABELS = {
    "cpu": "CPU", "ram": "RAM", "sd": "Storage",
    "network": "Network", "usb": "USB", "hdmi": "HDMI", "gpio": "GPIO",
}


# ---------------------------------------------------------------------------
# JSON report (unchanged — useful for machine reading)
# ---------------------------------------------------------------------------

def _write_json_report(report: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# HTML report — plain English, no JSON dumps
# ---------------------------------------------------------------------------

def _write_html_report(report: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    title = report.get("title", "Apple Pi Diagnostics Report")
    meta = report.get("metadata", {})
    details = report.get("details", {})

    os_name = ""
    if meta.get("os_release"):
        os_name = meta["os_release"].get("PRETTY_NAME", "")
    if not os_name:
        os_name = meta.get("platform", "")

    pi_model = meta.get("pi_model") or ""

    # Separate passing and failing tests
    issues: List[Tuple[str, str, List[str]]] = []   # (label, status, lines)
    passed: List[Tuple[str, str, List[str]]] = []

    for test_id, result in details.items():
        if not isinstance(result, dict):
            continue
        status = result.get("status", "UNKNOWN")
        label = _TEST_LABELS.get(test_id, test_id.upper())
        lines = _summarize_test(test_id, result)
        s_upper = status.upper()
        if s_upper in ("FAIL", "ERROR"):
            issues.append((label, status, lines))
        else:
            passed.append((label, status, lines))

    logo_tag = ""
    logo_path = _prepare_logo_for_pdf()
    if logo_path:
        logo_tag = f'<img class="logo" src="file://{logo_path}" alt="logo">'

    css = """
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
         color:#111;background:#fff;padding:2rem;max-width:860px;margin:0 auto}
    header{display:flex;align-items:center;gap:16px;margin-bottom:1.5rem;
           border-bottom:2px solid #0078d4;padding-bottom:1rem}
    .logo{width:52px;height:52px}
    h1{font-size:1.5rem;color:#0078d4}
    .meta{font-size:0.82rem;color:#555;margin-top:4px}
    h2{font-size:1.1rem;font-weight:700;margin:1.5rem 0 0.75rem;color:#111}
    .card{border:1px solid #ddd;border-radius:8px;padding:1rem;margin-bottom:0.75rem}
    .card-header{display:flex;justify-content:space-between;align-items:baseline;
                 margin-bottom:0.4rem}
    .card-title{font-weight:600;font-size:1rem}
    .badge{font-size:0.8rem;font-weight:600;padding:2px 8px;border-radius:12px}
    .pass{color:#1a8a4a;background:#e6f5ec}
    .fail{color:#cc2200;background:#fdecea}
    .unsupported{color:#b06000;background:#fff3e0}
    .other{color:#555;background:#f0f0f0}
    .lines{font-size:0.88rem;color:#333;line-height:1.6}
    .issues-section h2{color:#cc2200}
    .no-issues{color:#1a8a4a;font-size:0.9rem}
    hr{border:none;border-top:1px solid #e0e0e0;margin:1.5rem 0}
    @media(max-width:500px){body{padding:1rem}}
    """

    def badge(status: str) -> str:
        s = status.upper()
        if s in ("OK", "PASS"):
            return '<span class="badge pass">Passed</span>'
        if s in ("FAIL", "ERROR"):
            return '<span class="badge fail">Failed</span>'
        if s == "UNSUPPORTED":
            return '<span class="badge unsupported">Not supported</span>'
        return '<span class="badge other">Pending</span>'

    def render_card(label: str, status: str, lines: List[str]) -> str:
        safe_label = html.escape(label)
        lines_html = "<br>".join(
            html.escape(line).replace("  •", "&nbsp;&nbsp;&bull;").replace("  …", "&nbsp;&nbsp;&hellip;")
            for line in lines
        )
        return (
            f'<div class="card">'
            f'<div class="card-header"><span class="card-title">{safe_label}</span>{badge(status)}</div>'
            f'<div class="lines">{lines_html}</div>'
            f'</div>'
        )

    parts = [
        "<!doctype html><html lang=\"en\"><head>",
        f"<meta charset=\"utf-8\"><title>{html.escape(title)}</title>",
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<style>{css}</style>",
        "</head><body>",
        f"<header>{logo_tag}<div>",
        f"<h1>{html.escape(title)}</h1>",
        f'<div class="meta">Generated: {html.escape(meta.get("generated", ""))}',
        f" &nbsp;|&nbsp; Host: {html.escape(meta.get('hostname', ''))}" if meta.get("hostname") else "",
        f" &nbsp;|&nbsp; {html.escape(os_name)}" if os_name else "",
        f" &nbsp;|&nbsp; {html.escape(pi_model)}" if pi_model else "",
        "</div></div></header>",
    ]

    # Issues section first if any
    parts.append('<div class="issues-section">')
    parts.append("<h2>Highlighted Issues</h2>")
    if issues:
        for label, status, lines in issues:
            parts.append(render_card(label, status, lines))
    else:
        parts.append('<p class="no-issues">No issues found &mdash; all tests passed.</p>')
    parts.append("</div>")

    parts.append("<hr>")
    parts.append("<h2>All Results</h2>")
    for label, status, lines in passed:
        parts.append(render_card(label, status, lines))
    # also show issues again in full list
    for label, status, lines in issues:
        parts.append(render_card(label, status, lines))

    parts.append("</body></html>")
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# PDF report — plain English via reportlab platypus
# ---------------------------------------------------------------------------

def _write_pdf_report(report: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta = report.get("metadata", {})
    details = report.get("details", {})
    title_text = report.get("title", "Apple Pi Diagnostics Report")

    os_name = ""
    if meta.get("os_release"):
        os_name = meta["os_release"].get("PRETTY_NAME", "")
    if not os_name:
        os_name = meta.get("platform", "")
    pi_model = meta.get("pi_model") or ""

    # ---- styles ----
    base = getSampleStyleSheet()

    def style(name, **kw):
        s = ParagraphStyle(name, **kw)
        return s

    title_style = style("RPTitle",
        fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#0078d4"),
        spaceAfter=4, leading=22)
    meta_style = style("RPMeta",
        fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#555555"),
        spaceAfter=2, leading=13)
    h2_style = style("RPH2",
        fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#111111"),
        spaceBefore=14, spaceAfter=6, leading=18)
    h2_issue_style = style("RPH2Issue",
        fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#cc2200"),
        spaceBefore=14, spaceAfter=6, leading=18)
    test_name_style = style("RPTestName",
        fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#111111"),
        leading=14, spaceAfter=0)
    body_style = style("RPBody",
        fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#333333"),
        leading=15, leftIndent=12, spaceAfter=4)
    no_issues_style = style("RPNoIssues",
        fontName="Helvetica-Oblique", fontSize=10, textColor=colors.HexColor("#1a8a4a"),
        spaceAfter=6)

    STATUS_COLORS = {
        "OK": colors.HexColor("#1a8a4a"),
        "PASS": colors.HexColor("#1a8a4a"),
        "FAIL": colors.HexColor("#cc2200"),
        "ERROR": colors.HexColor("#cc2200"),
        "UNSUPPORTED": colors.HexColor("#b06000"),
    }

    def status_color(s: str):
        return STATUS_COLORS.get(s.upper(), colors.HexColor("#666666"))

    def status_text(s: str) -> str:
        return _status_label(s)[0]

    # ---- build flowables ----
    story = []

    # Header row: logo + title/meta
    logo_png = _prepare_logo_for_pdf()
    if logo_png:
        try:
            logo_img = RLImage(logo_png, width=52, height=52)
            header_data = [[logo_img,
                [Paragraph(title_text, title_style),
                 Paragraph(f"Generated: {meta.get('generated', '')}", meta_style),
                 Paragraph(f"Host: {meta.get('hostname', '')}  |  {os_name}" + (f"  |  {pi_model}" if pi_model else ""), meta_style)]]]
            header_table = Table(header_data, colWidths=[64, 400])
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(header_table)
        except Exception:
            story.append(Paragraph(title_text, title_style))
            story.append(Paragraph(f"Generated: {meta.get('generated', '')}", meta_style))
    else:
        story.append(Paragraph(title_text, title_style))
        story.append(Paragraph(f"Generated: {meta.get('generated', '')}", meta_style))
        info_parts = [p for p in [meta.get("hostname", ""), os_name, pi_model] if p]
        if info_parts:
            story.append(Paragraph("  |  ".join(info_parts), meta_style))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0078d4"), spaceAfter=8))

    # Collect issues vs passing
    issues = []
    passing = []
    for test_id, result in details.items():
        if not isinstance(result, dict):
            continue
        s = result.get("status", "UNKNOWN").upper()
        label = _TEST_LABELS.get(test_id, test_id.upper())
        lines = _summarize_test(test_id, result)
        if s in ("FAIL", "ERROR"):
            issues.append((label, s, lines))
        else:
            passing.append((label, s, lines))

    def test_block(label: str, raw_status: str, lines: List[str]) -> list:
        """Return a list of flowables for one test result."""
        sc = status_color(raw_status)
        st = status_text(raw_status)
        # Header row: name left, status right
        row = [[Paragraph(label, test_name_style),
                Paragraph(f'<font color="{sc.hexval()}">{st}</font>',
                          style("RPS", fontName="Helvetica-Bold", fontSize=10,
                                textColor=sc, leading=14, alignment=2))]]
        t = Table(row, colWidths=[300, 180])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#dddddd")),
        ]))
        flowables = [t]
        for line in lines:
            flowables.append(Paragraph(line.replace("  •", "&bull;").replace("  …", "&hellip;"), body_style))
        flowables.append(Spacer(1, 6))
        return flowables

    # ---- Highlighted Issues ----
    story.append(Paragraph("Highlighted Issues", h2_issue_style if issues else h2_style))
    if issues:
        for label, raw_status, lines in issues:
            story.append(KeepTogether(test_block(label, raw_status, lines)))
    else:
        story.append(Paragraph("No issues found \u2014 all tests passed.", no_issues_style))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=4))

    # ---- All Results ----
    story.append(Paragraph("All Results", h2_style))
    all_results = passing + issues
    for label, raw_status, lines in all_results:
        story.append(KeepTogether(test_block(label, raw_status, lines)))

    # ---- Build PDF ----
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=title_text,
        author="Apple Pi Diagnostics",
    )
    doc.build(story)
    return out_path


# ---------------------------------------------------------------------------
# Compact HTML for QR codes
# ---------------------------------------------------------------------------

def _write_compact_html_report(report: Dict[str, Any]) -> str:
    title = report.get("title", "Apple Pi Diagnostics Report")
    meta = report.get("metadata", {})
    details = report.get("details", {})
    css = "body{font-family:Arial,sans-serif;padding:8px;font-size:12px}h1{font-size:15px;margin:0 0 4px}.pass{color:#1a8a4a}.fail{color:#cc2200}.warn{color:#b06000}"
    parts = [f"<!doctype html><html><head><title>{title}</title>",
             "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
             f"<style>{css}</style></head><body>",
             f"<h1>{title}</h1>",
             f"<div><small>Generated: {meta.get('generated', '')}</small></div>"]
    for test_id, result in details.items():
        if not isinstance(result, dict):
            continue
        s = result.get("status", "?")
        label = _TEST_LABELS.get(test_id, test_id.upper())
        cls = "pass" if s.upper() in ("OK", "PASS") else "fail" if s.upper() in ("FAIL", "ERROR") else "warn"
        summary = _summarize_test(test_id, result)
        parts.append(f'<div><b>{label}:</b> <span class="{cls}">{_status_label(s)[0]}</span><br>')
        parts.append(f"<small>{' '.join(summary[:2])}</small></div>")
    parts.append("</body></html>")
    return " ".join("".join(parts).split())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_report(
    report_data: Dict[str, Any],
    out_dir: Path,
    formats: Sequence[str] = ("pdf", "html", "json"),
) -> Dict[str, Path]:
    """Build report in requested formats; return dict of format -> output path."""
    import urllib.parse

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = dict(report_data)
    report.setdefault("title", "Apple Pi Diagnostics Report")
    report.setdefault("metadata", _collect_system_metadata())
    report["metadata"].setdefault("generated", time.ctime(report["metadata"]["timestamp"]))

    results: Dict[str, Path] = {}
    base = out_dir / f"report_{int(time.time())}"

    if "json" in formats:
        results["json"] = _write_json_report(report, base.with_suffix(".json"))
    if "html" in formats:
        results["html"] = _write_html_report(report, base.with_suffix(".html"))
    if "pdf" in formats:
        results["pdf"] = _write_pdf_report(report, base.with_suffix(".pdf"))

    if "qr" in formats:
        try:
            qr_dir = out_dir / "qrs"
            qr_dir.mkdir(parents=True, exist_ok=True)
            compact_html = _write_compact_html_report(report)
            if "html" in results and QR_SUPPORTED:
                if len(compact_html) < 1500:
                    data_url = "data:text/html;utf-8," + urllib.parse.quote(compact_html)
                    img = qrcode.make(data_url)
                else:
                    data_url = f"file://{results['html'].resolve()}"
                    img = qrcode.make(data_url)
                out_q = qr_dir / f"report_html_{base.name}.png"
                img.save(str(out_q))
                results["qr_html"] = out_q
        except Exception:
            pass

    return results


def build_sample_report(out_dir):
    sample_data = {
        "summary": {},
        "details": {
            "cpu": {"status": "OK", "avg_cpu_percent": 10.5, "workers": 4},
            "ram": {"status": "OK", "tested_mb": 128, "throughput_mb_s": 150.2, "errors": []},
            "sd": {"status": "OK", "total_devices": 1, "tested_devices": 1,
                   "devices": [{"device": "/dev/mmcblk0", "size_gb": 32, "fstype": "ext4",
                                 "status": "OK", "write_mb_s": 18.7, "read_mb_s": 22.1}]},
        },
    }
    return build_report(sample_data, out_dir, formats=("pdf", "html", "json"))


if __name__ == "__main__":
    out = build_report(
        {"details": {
            "cpu": {"status": "OK", "avg_cpu_percent": 12.3, "workers": 4},
            "ram": {"status": "OK", "tested_mb": 64, "throughput_mb_s": 120.5, "errors": []},
            "hdmi": {"status": "FAIL", "note": "xrandr returned non-zero exit status 1."},
        }},
        Path.cwd() / "reports" / "sample",
        formats=("json", "html", "pdf"),
    )
    print({k: str(v) for k, v in out.items()})
