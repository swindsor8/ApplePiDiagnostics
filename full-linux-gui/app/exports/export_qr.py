#!/usr/bin/env python3
"""Local LAN HTTP server and QR code generator for report sharing."""
from __future__ import annotations

from functools import partial
import html
import http.server
from pathlib import Path
import socket
import threading
import time
from typing import Optional

import qrcode

from config import APP_VERSION, GATEWAY_PROBE_HOST, QR_HTTP_PORT


def get_local_ip() -> Optional[str]:
    """Return a non-loopback local IPv4 address (works online and on offline LANs)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((GATEWAY_PROBE_HOST, 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # Offline LAN fallback: inspect active interfaces via psutil
    try:
        import psutil
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for name, if_addrs in addrs.items():
            if name == "lo":
                continue
            st = stats.get(name)
            if st and not st.isup:
                continue
            for addr in if_addrs:
                if addr.family == socket.AF_INET and addr.address and not addr.address.startswith("127."):
                    return addr.address
    except Exception:
        pass

    return None


class _ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address):
        """Ignore normal mobile browser connection resets / broken pipes."""
        import sys
        exc = sys.exc_info()[1]
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


class _ReportHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serves a clean mobile-friendly report index at / and report files directly."""

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_index()
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def _serve_index(self):
        root = Path(self.directory)
        pdfs = sorted(root.glob("report_*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        htmls = sorted(root.glob("report_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        jsons = sorted(root.glob("report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        latest_links = []
        if htmls:
            name = html.escape(htmls[0].name)
            latest_links.append(f'<a class="btn primary" href="/{name}">View Latest Report (HTML)</a>')
        if pdfs:
            name = html.escape(pdfs[0].name)
            latest_links.append(f'<a class="btn" href="/{name}">Download Latest PDF</a>')

        all_files = sorted(
            [p for p in root.iterdir() if p.is_file() and p.suffix in (".pdf", ".html", ".json")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        rows = "".join(
            f'<li><a href="/{html.escape(p.name)}">{html.escape(p.name)}</a>'
            f'<span>{p.stat().st_size // 1024} KB</span></li>'
            for p in all_files[:20]
        ) or "<li><span>No reports generated yet.</span></li>"

        body = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Apple Pi Diagnostics ({html.escape(APP_VERSION)})</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       background:#0d1117;color:#f0f6fc;margin:0;padding:24px;max-width:640px;margin:0 auto}}
  h1{{font-size:20px;margin:0 0 4px}}
  .sub{{color:#9da7b3;font-size:13px;margin:0 0 20px}}
  .actions{{display:flex;flex-direction:column;gap:10px;margin-bottom:24px}}
  .btn{{display:block;text-align:center;text-decoration:none;padding:12px 16px;border-radius:10px;
       font-weight:600;font-size:15px;background:#161b22;color:#f0f6fc;border:1px solid #30363d}}
  .btn.primary{{background:#0a84ff;border-color:#0a84ff;color:#fff}}
  h2{{font-size:14px;color:#9da7b3;text-transform:uppercase;letter-spacing:.05em;margin:0 0 10px}}
  ul{{list-style:none;padding:0;margin:0;background:#161b22;border:1px solid #293241;border-radius:12px}}
  li{{display:flex;justify-content:space-between;padding:11px 14px;border-bottom:1px solid #293241;font-size:14px}}
  li:last-child{{border-bottom:none}}
  li a{{color:#409cff;text-decoration:none;word-break:break-all}}
  li span{{color:#9da7b3;font-size:12px;margin-left:10px;white-space:nowrap}}
</style></head><body>
  <h1>Apple Pi Diagnostics</h1>
  <p class="sub">Version {html.escape(APP_VERSION)} &middot; Local Report Transfer</p>
  <div class="actions">{''.join(latest_links)}</div>
  <h2>All Reports</h2>
  <ul>{rows}</ul>
</body></html>""".encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 — standard BaseHTTPRequestHandler signature
        pass


class _ThreadedHTTPServer(threading.Thread):
    def __init__(self, directory, port=QR_HTTP_PORT, bind_address="127.0.0.1"):
        super().__init__(daemon=True)
        self.directory = directory
        self.port = port
        self.bind_address = bind_address
        self.httpd = None

    def run(self):
        handler = partial(
            _ReportHTTPRequestHandler,
            directory=str(self.directory),
        )
        with _ReusableThreadingHTTPServer((self.bind_address, self.port), handler) as httpd:
            self.httpd = httpd
            try:
                httpd.serve_forever()
            except Exception:
                pass

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()


class QRExportManager:
    def __init__(self, report_directory, port=QR_HTTP_PORT):
        self.report_directory = report_directory
        self.port = port
        self.server_thread = None

    def start(self):
        ip = get_local_ip()
        if not ip:
            ip = "127.0.0.1"
        url = f"http://{ip}:{self.port}/"
        self.server_thread = _ThreadedHTTPServer(
            self.report_directory, port=self.port, bind_address=ip or "127.0.0.1"
        )
        self.server_thread.start()
        time.sleep(0.3)
        return url

    def stop(self):
        if self.server_thread:
            self.server_thread.stop()


def generate_qr_image(url, out_path):
    out_path = Path(out_path)
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
