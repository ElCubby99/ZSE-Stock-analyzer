"""Mini HTTP API za frontend (M4) — stdlib, bez novih ovisnosti.

  GET /api/dionica/<TICKER>  -> JSON iz src.stock_json (čita bazu, ništa ne piše)
  ostalo                     -> statika iz frontend/dist (SPA fallback na index.html)

Pokretanje:
  python -m src.webapi            # port 8001
  PORT=9000 python -m src.webapi

Razvoj frontenda: vite dev server proxyja /api na ovaj proces (vidi
frontend/vite.config.js). Za produkcijski pregled: npm run build pa samo ovaj
proces (servira i statiku).
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .db import get_conn
from .stock_json import build_stock_json

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"
MIME = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
        ".svg": "image/svg+xml", ".json": "application/json",
        ".ico": "image/x-icon", ".png": "image/png", ".woff2": "font/woff2"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # dev CORS (vite na drugom portu); javni deploy ide iza reverse proxyja
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

    def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler API)
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/dionica/"):
            ticker = path.rsplit("/", 1)[-1].upper()
            if not ticker.isalnum() or len(ticker) > 8:
                return self._json(400, {"error": "neispravan ticker"})
            try:
                with get_conn() as conn:
                    return self._json(200, build_stock_json(conn, ticker))
            except ValueError as e:
                return self._json(404, {"error": str(e)})
            except Exception as e:  # noqa: BLE001 — dijagnostika u odgovoru
                return self._json(500, {"error": f"{type(e).__name__}: {e}"})
        if path.startswith("/api/"):
            return self._json(404, {"error": "nepoznata ruta"})

        # statika (frontend/dist) + SPA fallback
        rel = path.lstrip("/") or "index.html"
        f = (DIST / rel).resolve()
        if not (str(f).startswith(str(DIST)) and f.is_file()):
            f = DIST / "index.html"
        if not f.is_file():
            return self._send(503, "frontend nije buildan (npm run build u frontend/)"
                              .encode(), "text/plain")
        self._send(200, f.read_bytes(), MIME.get(f.suffix, "application/octet-stream"))

    def log_message(self, fmt, *args):  # tiši log
        sys.stderr.write("[webapi] %s\n" % (fmt % args))


def main() -> int:
    port = int(os.getenv("PORT", "8001"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"webapi na http://127.0.0.1:{port}  (API: /api/dionica/ADRS)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
