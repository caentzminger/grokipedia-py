from __future__ import annotations

from contextlib import contextmanager
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Iterator

import pytest

from grokipedia import HttpxFetcher, UrllibFetcher


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/ok":
            payload = b"<html><body><h1>ok</h1></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        payload = b"missing"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


@contextmanager
def local_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        address = server.server_address
        host = str(address[0])
        port = int(address[1])
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_urllib_fetcher_reads_success_and_error_statuses() -> None:
    fetcher = UrllibFetcher()
    with local_server() as base_url:
        ok = fetcher.fetch_text(
            f"{base_url}/ok",
            timeout=2,
            headers={"User-Agent": "grokipedia-py-test"},
        )
        missing = fetcher.fetch_text(
            f"{base_url}/missing",
            timeout=2,
            headers={"User-Agent": "grokipedia-py-test"},
        )

    assert ok.status_code == 200
    assert "<h1>ok</h1>" in ok.text
    assert missing.status_code == 404
    assert "missing" in missing.text


def test_httpx_fetcher_optional_dependency_behavior() -> None:
    if importlib.util.find_spec("httpx") is None:
        with pytest.raises(ImportError):
            HttpxFetcher()
        return

    fetcher = HttpxFetcher()
    with local_server() as base_url:
        response = fetcher.fetch_text(
            f"{base_url}/ok",
            timeout=2,
            headers={"User-Agent": "grokipedia-py-test"},
        )

    assert response.status_code == 200
    assert "<h1>ok</h1>" in response.text
