from __future__ import annotations

import json
import mimetypes
import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from quanttool.live import DEFAULT_WATCHLIST, LiveMarketScanner, clean_symbols


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
SCANNER = LiveMarketScanner()


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
                    "api_keys": {
                        "alpha_vantage": bool(SCANNER.alpha_key),
                        "polygon": bool(SCANNER.polygon_key),
                        "finnhub": bool(SCANNER.finnhub_key),
                    },
                }
            )
            return

        self.serve_static(parsed.path)

    def handle_scan(self, query: str) -> None:
        params = urllib.parse.parse_qs(query)
        symbols_text = params.get("symbols", [""])[0]
        symbols = clean_symbols(symbols_text.split(",")) if symbols_text else DEFAULT_WATCHLIST
        limit = int(params.get("limit", ["30"])[0])
        self.write_json(SCANNER.scan(symbols, limit=limit))

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        file_path = (WEB_ROOT / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(WEB_ROOT.resolve())) or not file_path.exists():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

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
    print(f"Static root: {WEB_ROOT} exists={WEB_ROOT.exists()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
