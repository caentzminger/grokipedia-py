from __future__ import annotations

from datetime import datetime, timezone
import logging

from .errors import HttpStatusError, PageNotFoundError
from .fetch import Fetcher, UrllibFetcher
from .models import Page
from .parser import parse_page_html
from .robots import assert_allowed_by_robots

DEFAULT_USER_AGENT = "grokipedia-py/0.1"

logger = logging.getLogger(__name__)


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

    logger.debug(
        "from_url start url=%s timeout=%s respect_robots=%s allow_robots_override=%s",
        url,
        timeout,
        respect_robots,
        allow_robots_override,
    )

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
    logger.debug("Fetched url=%s status_code=%s", response.url, response.status_code)

    if response.status_code == 404:
        logger.info("Page not found url=%s", response.url)
        raise PageNotFoundError(response.url)
    if response.status_code >= 400:
        logger.info(
            "HTTP error url=%s status_code=%s", response.url, response.status_code
        )
        raise HttpStatusError(response.status_code, response.url)

    page = parse_page_html(
        response.text,
        source_url=response.url,
        status_code=response.status_code,
        fetched_at_utc=datetime.now(timezone.utc),
    )
    logger.debug("Parsed page url=%s title=%s", page.url, page.title)
    return page


def from_html(html: str, *, source_url: str | None = None) -> Page:
    logger.debug("from_html start source_url=%s", source_url)
    page = parse_page_html(
        html,
        source_url=source_url,
        status_code=200,
        fetched_at_utc=datetime.now(timezone.utc),
    )
    logger.debug("from_html parsed source_url=%s title=%s", source_url, page.title)
    return page
