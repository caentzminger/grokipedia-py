from __future__ import annotations

from dataclasses import dataclass
from email.message import Message
import logging
from typing import Mapping, Protocol
import urllib.error
import urllib.request

from .errors import FetchError


DEFAULT_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FetchResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    text: str


class Fetcher(Protocol):
    def fetch_text(
        self,
        url: str,
        *,
        timeout: float,
        headers: Mapping[str, str],
    ) -> FetchResponse: ...


def _decode_payload(payload: bytes, response_headers: Message) -> str:
    charset = response_headers.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset)
    except LookupError:
        return payload.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        return payload.decode(charset, errors="replace")


class UrllibFetcher:
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
        logger.debug("Fetching URL via urllib url=%s timeout=%s", url, timeout)
        request = urllib.request.Request(url, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                status_code = response.getcode()
                response_url = response.geturl()
                response_headers = dict(response.headers.items())
                text = _decode_payload(body, response.headers)
                logger.debug(
                    "Fetched URL via urllib url=%s status_code=%s bytes=%s",
                    response_url,
                    status_code,
                    len(body),
                )
                return FetchResponse(
                    url=response_url,
                    status_code=status_code,
                    headers=response_headers,
                    text=text,
                )
        except urllib.error.HTTPError as exc:
            body = exc.read()
            text = _decode_payload(body, exc.headers)
            logger.debug(
                "HTTPError from urllib url=%s status_code=%s bytes=%s",
                exc.url or url,
                exc.code,
                len(body),
            )
            return FetchResponse(
                url=exc.url or url,
                status_code=exc.code,
                headers=dict(exc.headers.items()),
                text=text,
            )
        except urllib.error.URLError as exc:
            logger.warning("Network error fetching url=%s error=%s", url, exc)
            raise FetchError(f"Network error fetching {url}: {exc}") from exc
