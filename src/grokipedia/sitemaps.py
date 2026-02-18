from __future__ import annotations

import logging
from typing import Protocol
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from .errors import ParseError
from .fetch import FetchResponse, Fetcher

logger = logging.getLogger(__name__)


class FetchTextFn(Protocol):
    def __call__(
        self,
        url: str,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
        fetcher: Fetcher,
        not_found_is_page: bool,
    ) -> FetchResponse: ...


def _parse_sitemap_locs(xml_text: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ParseError(f"Unable to parse sitemap XML: {exc}") from exc

    urls: list[str] = []
    seen: set[str] = set()
    for node in root.findall(".//{*}loc"):
        value = (node.text or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        urls.append(value)

    return urls


def _canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = unquote(parsed.path)
    return f"{scheme}://{netloc}{path}"


class SitemapManifest:
    def __init__(
        self,
        *,
        sitemap_index_url: str,
        fetch_text: FetchTextFn,
        fetcher: Fetcher,
    ) -> None:
        self.sitemap_index_url = sitemap_index_url
        self._fetch_text = fetch_text
        self._fetcher = fetcher

        self._sitemap_index_urls_cache: list[str] | None = None
        self._manifest_by_sitemap: dict[str, list[str]] = {}
        self._loaded_sitemaps: set[str] = set()

    def _get_sitemap_index_urls(
        self,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
    ) -> list[str]:
        if self._sitemap_index_urls_cache is not None:
            return self._sitemap_index_urls_cache

        response = self._fetch_text(
            self.sitemap_index_url,
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
            fetcher=self._fetcher,
            not_found_is_page=False,
        )
        sitemap_urls = _parse_sitemap_locs(response.text)

        previous_manifest = self._manifest_by_sitemap
        self._manifest_by_sitemap = {
            sitemap_url: list(previous_manifest.get(sitemap_url, []))
            for sitemap_url in sitemap_urls
        }
        self._loaded_sitemaps.intersection_update(self._manifest_by_sitemap.keys())
        self._sitemap_index_urls_cache = sitemap_urls
        logger.debug("Loaded sitemap index count=%s", len(sitemap_urls))
        return sitemap_urls

    def _get_or_load_child_sitemap_urls(
        self,
        sitemap_url: str,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
    ) -> list[str]:
        if sitemap_url in self._loaded_sitemaps:
            return self._manifest_by_sitemap.get(sitemap_url, [])

        response = self._fetch_text(
            sitemap_url,
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
            fetcher=self._fetcher,
            not_found_is_page=False,
        )
        page_urls = _parse_sitemap_locs(response.text)
        self._manifest_by_sitemap[sitemap_url] = page_urls
        self._loaded_sitemaps.add(sitemap_url)
        logger.debug(
            "Loaded child sitemap sitemap_url=%s page_count=%s",
            sitemap_url,
            len(page_urls),
        )
        return page_urls

    def _manifest_snapshot(self) -> dict[str, list[str]]:
        return {
            sitemap_url: list(page_urls)
            for sitemap_url, page_urls in self._manifest_by_sitemap.items()
        }

    def refresh(
        self,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
    ) -> dict[str, list[str]]:
        self._sitemap_index_urls_cache = None
        self._manifest_by_sitemap = {}
        self._loaded_sitemaps.clear()

        self._get_sitemap_index_urls(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )
        return self._manifest_snapshot()

    def find_matching_url(
        self,
        candidate_url: str,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
    ) -> str | None:
        candidate_key = _canonicalize_url(candidate_url)

        for sitemap_url in self._get_sitemap_index_urls(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        ):
            page_urls = self._get_or_load_child_sitemap_urls(
                sitemap_url,
                timeout=timeout,
                respect_robots=respect_robots,
                allow_robots_override=allow_robots_override,
                user_agent=user_agent,
            )

            for page_url in page_urls:
                if _canonicalize_url(page_url) == candidate_key:
                    return page_url

        return None
