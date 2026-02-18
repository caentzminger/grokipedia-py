from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
import logging
from urllib.parse import quote_plus, urljoin, urlparse

from ._types import FetchTextFn
from ._urls import (
    canonicalize_url,
    page_url_from_slug,
    resolve_base_url,
    resolve_user_agent,
)
from .errors import (
    HttpStatusError,
    ParseError,
    RobotsDisallowedError,
    RobotsUnavailableError,
)
from .fetch import FetchResponse, Fetcher, UrllibFetcher

DEFAULT_SEARCH_API_PATH = "/api/full-text-search"

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _SearchRequest:
    query: str
    timeout: float
    respect_robots: bool
    allow_robots_override: bool
    user_agent: str
    fetcher: Fetcher
    base_url: str

    @property
    def api_url(self) -> str:
        encoded_query = quote_plus(self.query)
        return (
            f"{self.base_url}{DEFAULT_SEARCH_API_PATH}"
            f"?query={encoded_query}&limit=25&offset=0"
        )

    @property
    def html_url(self) -> str:
        return f"{self.base_url}/search?q={quote_plus(self.query)}"


class _SearchResultLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)
                return


def _extract_search_page_urls(html: str, *, base_url: str) -> list[str]:
    parser = _SearchResultLinkParser()
    try:
        parser.feed(html)
    except Exception as exc:
        raise ParseError(f"Unable to parse search results HTML: {exc}") from exc

    base = resolve_base_url(base_url)
    expected_host = urlparse(base).netloc.lower()
    seen: set[str] = set()
    page_urls: list[str] = []

    for href in parser.hrefs:
        absolute_url = urljoin(f"{base}/", href)
        parsed = urlparse(absolute_url)

        if parsed.netloc.lower() != expected_host:
            continue
        if not parsed.path.startswith("/page/"):
            continue

        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized in seen:
            continue

        seen.add(normalized)
        page_urls.append(normalized)

    return page_urls


def _extract_search_api_page_urls(payload: str, *, base_url: str) -> list[str]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Unable to parse search API JSON: {exc}") from exc

    raw_results = data.get("results")
    if not isinstance(raw_results, list):
        raise ParseError("Search API JSON missing 'results' list")

    seen: set[str] = set()
    page_urls: list[str] = []
    for entry in raw_results:
        if not isinstance(entry, dict):
            continue

        slug = entry.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            continue

        page_url = page_url_from_slug(slug, base_url=base_url)
        dedupe_key = canonicalize_url(page_url)
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        page_urls.append(page_url)

    return page_urls


def _fetch_search_response(
    url: str,
    *,
    request: _SearchRequest,
    fetch_text: FetchTextFn,
) -> FetchResponse:
    return fetch_text(
        url,
        timeout=request.timeout,
        respect_robots=request.respect_robots,
        allow_robots_override=request.allow_robots_override,
        user_agent=request.user_agent,
        fetcher=request.fetcher,
        not_found_is_page=False,
    )


def run_search(
    search_term_string: str,
    *,
    timeout: float,
    respect_robots: bool,
    allow_robots_override: bool,
    user_agent: str | None,
    fetcher: Fetcher | None,
    base_url: str,
    default_user_agent: str,
    fetch_text: FetchTextFn,
    logger: logging.Logger | None = None,
) -> list[str]:
    active_logger = logger or _logger

    query = search_term_string.strip()
    if not query:
        raise ValueError("search_term_string must not be empty")

    request = _SearchRequest(
        query=query,
        timeout=timeout,
        respect_robots=respect_robots,
        allow_robots_override=allow_robots_override,
        user_agent=resolve_user_agent(
            user_agent,
            default_user_agent=default_user_agent,
        ),
        fetcher=fetcher or UrllibFetcher(),
        base_url=resolve_base_url(base_url),
    )
    active_logger.debug("search start query=%s url=%s", query, request.api_url)

    try:
        response = _fetch_search_response(
            request.api_url,
            request=request,
            fetch_text=fetch_text,
        )
        page_urls = _extract_search_api_page_urls(
            response.text,
            base_url=request.base_url,
        )
        active_logger.debug(
            "search api results query=%s count=%s", query, len(page_urls)
        )
        return page_urls
    except (
        HttpStatusError,
        ParseError,
        RobotsDisallowedError,
        RobotsUnavailableError,
    ) as exc:
        active_logger.debug(
            "search api failed query=%s error=%s; falling back to /search HTML",
            query,
            exc,
        )

    response = _fetch_search_response(
        request.html_url,
        request=request,
        fetch_text=fetch_text,
    )
    page_urls = _extract_search_page_urls(response.text, base_url=request.base_url)
    active_logger.debug(
        "search html fallback results query=%s count=%s", query, len(page_urls)
    )
    return page_urls
