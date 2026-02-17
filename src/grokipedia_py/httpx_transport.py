from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from .errors import FetchError
from .fetch import DEFAULT_ACCEPT, FetchResponse

if TYPE_CHECKING:
    import httpx
else:
    httpx = None


class HttpxFetcher:
    def __init__(self, client: "httpx.Client" | None = None) -> None:
        if httpx is None:
            try:
                import httpx as imported_httpx
            except ImportError as exc:
                raise ImportError(
                    "httpx is not installed. Install with: pip install 'grokipedia-py[http]'",
                ) from exc
            globals()["httpx"] = imported_httpx

        self._client = client

    def fetch_text(
        self,
        url: str,
        *,
        timeout: float,
        headers: Mapping[str, str],
    ) -> FetchResponse:
        request_headers = {
            "Accept": DEFAULT_ACCEPT,
            **headers,
        }

        try:
            if self._client is not None:
                response = self._client.get(
                    url,
                    timeout=timeout,
                    headers=request_headers,
                    follow_redirects=True,
                )
            else:
                with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                    response = client.get(url, headers=request_headers)
        except Exception as exc:
            raise FetchError(f"Network error fetching {url}: {exc}") from exc

        return FetchResponse(
            url=str(response.url),
            status_code=response.status_code,
            headers=dict(response.headers.items()),
            text=response.text,
        )
