from __future__ import annotations

from datetime import datetime, timezone
import logging
from urllib.parse import quote

from .errors import (
    HttpStatusError,
    PageNotFoundError,
)
from .fetch import FetchResponse, Fetcher, UrllibFetcher
from .models import Page
from .parser import parse_page_html
from .robots import assert_allowed_by_robots
from .search import run_search
from .sitemaps import SitemapManifest

DEFAULT_USER_AGENT = "grokipedia-py/0.1"
DEFAULT_BASE_URL = "https://grokipedia.com"
DEFAULT_SITEMAP_INDEX_URL = "https://assets.grokipedia.com/sitemap/sitemap-index.xml"

logger = logging.getLogger(__name__)


def _configure_verbose_logging(*, enabled: bool) -> None:
    if not enabled:
        return

    package_logger = logging.getLogger("grokipedia")
    package_logger.setLevel(logging.DEBUG)

    has_non_null_handler = any(
        not isinstance(handler, logging.NullHandler)
        for handler in package_logger.handlers
    )
    if has_non_null_handler:
        return

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    package_logger.addHandler(handler)
    package_logger.propagate = False


def _resolve_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ValueError("base_url must not be empty")
    return normalized


def _resolve_user_agent(user_agent: str | None) -> str:
    return user_agent or DEFAULT_USER_AGENT


def _maybe_check_robots(
    target_url: str,
    *,
    fetcher: Fetcher,
    timeout: float,
    user_agent: str,
    respect_robots: bool,
    allow_robots_override: bool,
) -> None:
    if respect_robots and not allow_robots_override:
        assert_allowed_by_robots(
            target_url,
            fetcher=fetcher,
            timeout=timeout,
            user_agent=user_agent,
        )


def _fetch_text(
    url: str,
    *,
    timeout: float,
    respect_robots: bool,
    allow_robots_override: bool,
    user_agent: str,
    fetcher: Fetcher,
    not_found_is_page: bool,
) -> FetchResponse:
    _maybe_check_robots(
        url,
        fetcher=fetcher,
        timeout=timeout,
        user_agent=user_agent,
        respect_robots=respect_robots,
        allow_robots_override=allow_robots_override,
    )

    response = fetcher.fetch_text(
        url,
        timeout=timeout,
        headers={"User-Agent": user_agent},
    )

    logger.debug("Fetched url=%s status_code=%s", response.url, response.status_code)

    if response.status_code == 404 and not_found_is_page:
        raise PageNotFoundError(response.url)
    if response.status_code >= 400:
        raise HttpStatusError(response.status_code, response.url)

    return response


def _parse_fetched_page(response: FetchResponse) -> Page:
    page = parse_page_html(
        response.text,
        source_url=response.url,
        status_code=response.status_code,
        fetched_at_utc=datetime.now(timezone.utc),
    )
    logger.debug("Parsed page url=%s title=%s", page.url, page.title)
    return page


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
    resolved_user_agent = _resolve_user_agent(user_agent)

    logger.debug(
        "from_url start url=%s timeout=%s respect_robots=%s allow_robots_override=%s",
        url,
        timeout,
        respect_robots,
        allow_robots_override,
    )

    response = _fetch_text(
        url,
        timeout=timeout,
        respect_robots=respect_robots,
        allow_robots_override=allow_robots_override,
        user_agent=resolved_user_agent,
        fetcher=resolved_fetcher,
        not_found_is_page=True,
    )
    return _parse_fetched_page(response)


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


def _page_url_from_title(title: str, *, base_url: str) -> str:
    normalized_title = "_".join(title.strip().split())
    if not normalized_title:
        raise ValueError("title must not be empty")

    # Keep URL-safe punctuation and encode the rest.
    slug = quote(normalized_title, safe="!$&'()*+,;=:@._~-")
    return f"{_resolve_base_url(base_url)}/page/{slug}"


def page(
    title: str,
    *,
    timeout: float = 10.0,
    respect_robots: bool = True,
    allow_robots_override: bool = False,
    user_agent: str | None = None,
    fetcher: Fetcher | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> Page:
    page_url = _page_url_from_title(title, base_url=base_url)
    return from_url(
        page_url,
        timeout=timeout,
        respect_robots=respect_robots,
        allow_robots_override=allow_robots_override,
        user_agent=user_agent,
        fetcher=fetcher,
    )


def search(
    search_term_string: str,
    *,
    timeout: float = 10.0,
    respect_robots: bool = True,
    allow_robots_override: bool = False,
    user_agent: str | None = None,
    fetcher: Fetcher | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> list[str]:
    return run_search(
        search_term_string,
        timeout=timeout,
        respect_robots=respect_robots,
        allow_robots_override=allow_robots_override,
        user_agent=user_agent,
        fetcher=fetcher,
        base_url=base_url,
        default_user_agent=DEFAULT_USER_AGENT,
        fetch_text=_fetch_text,
        logger=logger,
    )


class Grokipedia:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        sitemap_index_url: str = DEFAULT_SITEMAP_INDEX_URL,
        timeout: float = 10.0,
        respect_robots: bool = True,
        allow_robots_override: bool = False,
        user_agent: str | None = None,
        fetcher: Fetcher | None = None,
        verbose: bool = False,
    ) -> None:
        _configure_verbose_logging(enabled=verbose)

        self.base_url = _resolve_base_url(base_url)
        self.sitemap_index_url = sitemap_index_url
        self.timeout = timeout
        self.respect_robots = respect_robots
        self.allow_robots_override = allow_robots_override
        self.user_agent = _resolve_user_agent(user_agent)
        self.fetcher = fetcher or UrllibFetcher()
        self._sitemap_manifest = SitemapManifest(
            sitemap_index_url=self.sitemap_index_url,
            fetch_text=_fetch_text,
            fetcher=self.fetcher,
        )

    def _resolve_call_options(
        self,
        *,
        timeout: float | None,
        respect_robots: bool | None,
        allow_robots_override: bool | None,
        user_agent: str | None,
    ) -> tuple[float, bool, bool, str]:
        return (
            self.timeout if timeout is None else timeout,
            self.respect_robots if respect_robots is None else respect_robots,
            (
                self.allow_robots_override
                if allow_robots_override is None
                else allow_robots_override
            ),
            self.user_agent if user_agent is None else user_agent,
        )

    def from_url(
        self,
        url: str,
        *,
        timeout: float | None = None,
        respect_robots: bool | None = None,
        allow_robots_override: bool | None = None,
        user_agent: str | None = None,
    ) -> Page:
        (
            resolved_timeout,
            resolved_respect_robots,
            resolved_allow_robots_override,
            resolved_user_agent,
        ) = self._resolve_call_options(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )

        return from_url(
            url,
            timeout=resolved_timeout,
            respect_robots=resolved_respect_robots,
            allow_robots_override=resolved_allow_robots_override,
            user_agent=resolved_user_agent,
            fetcher=self.fetcher,
        )

    def from_html(self, html: str, *, source_url: str | None = None) -> Page:
        return from_html(html, source_url=source_url)

    def page(
        self,
        title: str,
        *,
        timeout: float | None = None,
        respect_robots: bool | None = None,
        allow_robots_override: bool | None = None,
        user_agent: str | None = None,
    ) -> Page:
        (
            resolved_timeout,
            resolved_respect_robots,
            resolved_allow_robots_override,
            resolved_user_agent,
        ) = self._resolve_call_options(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )

        return page(
            title,
            timeout=resolved_timeout,
            respect_robots=resolved_respect_robots,
            allow_robots_override=resolved_allow_robots_override,
            user_agent=resolved_user_agent,
            fetcher=self.fetcher,
            base_url=self.base_url,
        )

    def search(
        self,
        search_term_string: str,
        *,
        timeout: float | None = None,
        respect_robots: bool | None = None,
        allow_robots_override: bool | None = None,
        user_agent: str | None = None,
    ) -> list[str]:
        (
            resolved_timeout,
            resolved_respect_robots,
            resolved_allow_robots_override,
            resolved_user_agent,
        ) = self._resolve_call_options(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )

        return search(
            search_term_string,
            timeout=resolved_timeout,
            respect_robots=resolved_respect_robots,
            allow_robots_override=resolved_allow_robots_override,
            user_agent=resolved_user_agent,
            fetcher=self.fetcher,
            base_url=self.base_url,
        )

    def refresh_manifest(
        self,
        *,
        timeout: float | None = None,
        respect_robots: bool | None = None,
        allow_robots_override: bool | None = None,
        user_agent: str | None = None,
    ) -> dict[str, list[str]]:
        (
            resolved_timeout,
            resolved_respect_robots,
            resolved_allow_robots_override,
            resolved_user_agent,
        ) = self._resolve_call_options(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )

        return self._sitemap_manifest.refresh(
            timeout=resolved_timeout,
            respect_robots=resolved_respect_robots,
            allow_robots_override=resolved_allow_robots_override,
            user_agent=resolved_user_agent,
        )

    def find_page_url(
        self,
        title: str,
        *,
        timeout: float | None = None,
        respect_robots: bool | None = None,
        allow_robots_override: bool | None = None,
        user_agent: str | None = None,
    ) -> str | None:
        (
            resolved_timeout,
            resolved_respect_robots,
            resolved_allow_robots_override,
            resolved_user_agent,
        ) = self._resolve_call_options(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )

        candidate_url = _page_url_from_title(title, base_url=self.base_url)
        return self._sitemap_manifest.find_matching_url(
            candidate_url,
            timeout=resolved_timeout,
            respect_robots=resolved_respect_robots,
            allow_robots_override=resolved_allow_robots_override,
            user_agent=resolved_user_agent,
        )
