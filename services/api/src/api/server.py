"""Stdlib HTTP wiring for local development; no framework dependency added."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from learning import LearningEngine
from learning.providers.fake import FakeProvider

from .domain import AnalysisService
from .routes import dispatch

MAX_HEADER_BODY = 64_000


def build_handler(service: AnalysisService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "DevComprehendAPI/0.1"

        def _handle(self, method: str):
            length = self.headers.get("Content-Length")
            try:
                size = int(length) if length is not None else 0
            except ValueError:
                size = MAX_HEADER_BODY + 1
            raw = self.rfile.read(size) if 0 <= size <= MAX_HEADER_BODY else b"x" * (MAX_HEADER_BODY + 1)
            status, payload = dispatch(service, method, self.path.split("?", 1)[0],
                                       dict(self.headers), raw)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def log_message(self, format, *args):
            # Suppress access logs: request lines can carry user content.
            pass

    return Handler


def create_server(host: str = "127.0.0.1", port: int = 8000,
                  service: AnalysisService | None = None) -> ThreadingHTTPServer:
    service = service or AnalysisService(LearningEngine(FakeProvider()))
    return ThreadingHTTPServer((host, port), build_handler(service))
