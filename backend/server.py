"""Zero-dependency HTTP server.

Run locally with one command:  python -m backend
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .api import dispatch
from .db import Database


class Handler(BaseHTTPRequestHandler):
    server_version = "content_feed/1.0"
    db: Database

    def _send(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self) -> None:
        if self.command == "OPTIONS":
            self._send(204, {})
            return
        parts = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = None
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._send(400, {"error": {"code": "invalid_json", "message": "invalid JSON body"}})
                return
        status, payload = dispatch(
            self.command, parts.path, body, dict(self.headers), self.db
        )
        self._send(status, payload)

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_DELETE = _handle
    do_OPTIONS = _handle

    def log_message(self, fmt: str, *args) -> None:
        print(f"[http] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}",
              flush=True)


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    db = Database()
    Handler.db = db
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"content_feed backend on http://{host}:{port}", flush=True)
    print(f"engine: {db.kind} ({db.url})", flush=True)
    print("Login codes are printed to this console. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        db.close()


if __name__ == "__main__":
    main()
