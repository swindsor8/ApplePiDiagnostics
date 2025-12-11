#!/usr/bin/env python3
import qrcode
from pathlib import Path
import socket
import threading
import http.server
import socketserver
import os
import time

def get_local_ip():
    # return local IPv4 address or None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # doesn't have to be reachable
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

class _ThreadedHTTPServer(threading.Thread):
    def __init__(self, directory, port=8888):
        super().__init__(daemon=True)
        self.directory = directory
        self.port = port
        self.httpd = None

    def run(self):
        handler = http.server.SimpleHTTPRequestHandler
        os.chdir(self.directory)
        with socketserver.TCPServer(("", self.port), handler) as httpd:
            self.httpd = httpd
            try:
                httpd.serve_forever()
            except Exception:
                pass

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()

class QRExportManager:
    def __init__(self, report_directory, port=8888):
        self.report_directory = report_directory
        self.port = port
        self.server_thread = None

    def start(self):
        ip = get_local_ip()
        if not ip:
            # fallback to localhost; the user will need to use device IP if phone can't reach it
            ip = "127.0.0.1"
        url = f"http://{ip}:{self.port}/"
        # start http server thread
        self.server_thread = _ThreadedHTTPServer(self.report_directory, port=self.port)
        self.server_thread.start()
        # small sleep to allow server to bind
        time.sleep(0.5)
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
