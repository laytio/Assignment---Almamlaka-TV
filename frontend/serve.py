"""Serve the frontend and proxy /api/* to the FastAPI backend (same origin, so no CORS needed).

Usage:  python frontend/serve.py
Env:    BACKEND_URL (default http://127.0.0.1:8000), HOST (127.0.0.1), PORT (5173)
"""

import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5173"))
ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.proxy()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.proxy()
        self.send_error(405)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        request = Request(
            BACKEND_URL + self.path,
            data=self.rfile.read(length) if length else None,
            method=self.command,
            headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
        )
        try:
            with urlopen(request, timeout=180) as response:
                status, body, ctype = response.status, response.read(), response.headers.get("Content-Type")
        except HTTPError as exc:  # backend answered with an error status: pass it through
            status, body, ctype = exc.code, exc.read(), exc.headers.get("Content-Type")
        except OSError:  # backend down or timed out
            status, body, ctype = 502, json.dumps({"detail": "Backend unavailable"}).encode(), "application/json"

        self.send_response(status)
        self.send_header("Content-Type", ctype or "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), partial(Handler, directory=str(ROOT)))
    print(f"Frontend on http://{HOST}:{PORT}  ->  API {BACKEND_URL}")
    server.serve_forever()
