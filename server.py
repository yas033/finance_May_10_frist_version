from __future__ import annotations

import json
import mimetypes
import os
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from quanttool.live import DEFAULT_WATCHLIST, LiveMarketScanner, clean_symbols


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
STATIC_ROOTS = (WEB_ROOT, ROOT)
SCANNER = LiveMarketScanner()
SCAN_RATE_LIMIT = 180
RATE_LIMIT_WINDOW_SECONDS = 60
SCAN_REQUESTS_BY_IP: dict[str, list[float]] = {}


class QuantHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/scan":
            self.handle_scan(parsed.query)
            return
        if parsed.path == "/api/config":
            self.write_json(
                {
                    "watchlist": DEFAULT_WATCHLIST,
                    "providers": ["Yahoo Finance", "Alpha Vantage", "Polygon", "Finnhub"],
                }
            )
            return

        self.serve_static(parsed.path)

    def handle_scan(self, query: str) -> None:
        if self.is_rate_limited():
            self.send_response(429)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Retry-After", "60")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Rate limit exceeded"}).encode("utf-8"))
            return

        params = urllib.parse.parse_qs(query)
        symbols_text = params.get("symbols", [""])[0]
        symbols = clean_symbols(symbols_text.split(",")) if symbols_text else DEFAULT_WATCHLIST
        limit = int(params.get("limit", ["30"])[0])
        self.write_json(SCANNER.scan(symbols, limit=limit))

    def is_rate_limited(self) -> bool:
        forwarded_for = self.headers.get("X-Forwarded-For", "")
        ip_address = (forwarded_for.split(",")[0].strip() if forwarded_for else self.client_address[0]) or "unknown"
        now = time.time()
        recent = [stamp for stamp in SCAN_REQUESTS_BY_IP.get(ip_address, []) if now - stamp < RATE_LIMIT_WINDOW_SECONDS]
        if len(recent) >= SCAN_RATE_LIMIT:
            SCAN_REQUESTS_BY_IP[ip_address] = recent
            return True
        recent.append(now)
        SCAN_REQUESTS_BY_IP[ip_address] = recent
        return False

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        file_path = self.find_static_file(path)
        if file_path is None:
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def find_static_file(self, path: str) -> Path | None:
        relative_path = path.lstrip("/")
        for root in STATIC_ROOTS:
            root_resolved = root.resolve()
            file_path = (root / relative_path).resolve()
            if str(file_path).startswith(str(root_resolved)) and file_path.exists() and file_path.is_file():
                return file_path
        return None

    def write_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), QuantHandler)
    print(f"Quant Stock Tool running at http://{host}:{port}")
    print(f"Static roots: {', '.join(f'{root} exists={root.exists()}' for root in STATIC_ROOTS)}")
    server.serve_forever()


if __name__ == "__main__":
    main()
