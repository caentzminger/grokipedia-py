from __future__ import annotations

from datetime import datetime, timezone

from .errors import HttpStatusError, PageNotFoundError
from .fetch import Fetcher, UrllibFetcher
from .models import Page
from .parser import parse_page_html
from .robots import assert_allowed_by_robots

DEFAULT_USER_AGENT = "grokipedia-py/0.1"


def from_url(
    url: str,
    *,
    timeout: float = 10.0,
    respect_robots: bool = True,
    allow_robots_override: bool = False,
    user_agent: str | None = None,
    fetcher: Fetcher | None = None,
) -> Page:
    resolved_fetcher = fetcher or UrllibFetcher()
    resolved_user_agent = user_agent or DEFAULT_USER_AGENT

    if respect_robots and not allow_robots_override:
        assert_allowed_by_robots(
            url,
            fetcher=resolved_fetcher,
            timeout=timeout,
            user_agent=resolved_user_agent,
        )

    response = resolved_fetcher.fetch_text(
        url,
        timeout=timeout,
        headers={"User-Agent": resolved_user_agent},
    )

    if response.status_code == 404:
        raise PageNotFoundError(response.url)
    if response.status_code >= 400:
        raise HttpStatusError(response.status_code, response.url)

    return parse_page_html(
        response.text,
        source_url=response.url,
        status_code=response.status_code,
        fetched_at_utc=datetime.now(timezone.utc),
    )


def from_html(html: str, *, source_url: str | None = None) -> Page:
    return parse_page_html(
        html,
        source_url=source_url,
        status_code=200,
        fetched_at_utc=datetime.now(timezone.utc),
    )
