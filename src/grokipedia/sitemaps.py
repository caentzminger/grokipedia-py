from __future__ import annotations

import logging
from xml.etree import ElementTree

from ._types import FetchTextFn
from ._urls import canonicalize_url
from .errors import ParseError
from .fetch import Fetcher

logger = logging.getLogger(__name__)


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
        self._canonical_page_url: dict[str, str] = {}
        self._canonical_keys_by_sitemap: dict[str, set[str]] = {}
        self._canonical_owners: dict[str, set[str]] = {}

    def _remove_sitemap_indexes(self, sitemap_url: str) -> None:
        keys = self._canonical_keys_by_sitemap.pop(sitemap_url, set())
        for key in keys:
            owners = self._canonical_owners.get(key)
            if owners is None:
                continue

            owners.discard(sitemap_url)
            if owners:
                continue

            self._canonical_owners.pop(key, None)
            self._canonical_page_url.pop(key, None)

    def _index_sitemap_urls(self, sitemap_url: str, page_urls: list[str]) -> None:
        self._remove_sitemap_indexes(sitemap_url)

        canonical_keys: set[str] = set()
        for page_url in page_urls:
            key = canonicalize_url(page_url)
            canonical_keys.add(key)
            self._canonical_page_url[key] = page_url
            self._canonical_owners.setdefault(key, set()).add(sitemap_url)

        self._canonical_keys_by_sitemap[sitemap_url] = canonical_keys

    def _fetch_sitemap_urls(
        self,
        url: str,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
    ) -> list[str]:
        response = self._fetch_text(
            url,
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
            fetcher=self._fetcher,
            not_found_is_page=False,
        )
        return _parse_sitemap_locs(response.text)

    def _sync_manifest_with_index(self, sitemap_urls: list[str]) -> None:
        previous_sitemaps = set(self._manifest_by_sitemap.keys())
        previous_manifest = self._manifest_by_sitemap
        self._manifest_by_sitemap = {
            sitemap_url: list(previous_manifest.get(sitemap_url, []))
            for sitemap_url in sitemap_urls
        }
        self._loaded_sitemaps.intersection_update(self._manifest_by_sitemap.keys())
        for sitemap_url in previous_sitemaps - set(sitemap_urls):
            self._remove_sitemap_indexes(sitemap_url)

    def _ensure_sitemap_index_urls(
        self,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
    ) -> list[str]:
        if self._sitemap_index_urls_cache is not None:
            return self._sitemap_index_urls_cache

        sitemap_urls = self._fetch_sitemap_urls(
            self.sitemap_index_url,
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )
        self._sync_manifest_with_index(sitemap_urls)
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
            return self._manifest_by_sitemap.setdefault(sitemap_url, [])

        page_urls = self._fetch_sitemap_urls(
            sitemap_url,
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        )
        self._manifest_by_sitemap[sitemap_url] = page_urls
        self._loaded_sitemaps.add(sitemap_url)
        self._index_sitemap_urls(sitemap_url, page_urls)
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

    def _reset_cache(self) -> None:
        self._sitemap_index_urls_cache = None
        self._manifest_by_sitemap.clear()
        self._loaded_sitemaps.clear()
        self._canonical_page_url.clear()
        self._canonical_keys_by_sitemap.clear()
        self._canonical_owners.clear()

    def refresh(
        self,
        *,
        timeout: float,
        respect_robots: bool,
        allow_robots_override: bool,
        user_agent: str,
    ) -> dict[str, list[str]]:
        self._reset_cache()

        self._ensure_sitemap_index_urls(
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
        candidate_key = canonicalize_url(candidate_url)
        cached_match = self._canonical_page_url.get(candidate_key)
        if cached_match is not None:
            return cached_match

        for sitemap_url in self._ensure_sitemap_index_urls(
            timeout=timeout,
            respect_robots=respect_robots,
            allow_robots_override=allow_robots_override,
            user_agent=user_agent,
        ):
            self._get_or_load_child_sitemap_urls(
                sitemap_url,
                timeout=timeout,
                respect_robots=respect_robots,
                allow_robots_override=allow_robots_override,
                user_agent=user_agent,
            )
            cached_match = self._canonical_page_url.get(candidate_key)
            if cached_match is not None:
                return cached_match

        return None
