from __future__ import annotations

from collections import Counter
import logging
from typing import Mapping

from grokipedia import Grokipedia
from grokipedia.errors import HttpStatusError
from grokipedia.fetch import FetchResponse


class StaticFetcher:
    def __init__(self, responses: dict[str, tuple[int, str]]) -> None:
        self.responses = responses
        self.request_urls: list[str] = []

    def fetch_text(
        self, url: str, *, timeout: float, headers: Mapping[str, str]
    ) -> FetchResponse:
        self.request_urls.append(url)
        status_code, text = self.responses.get(
            url,
            (
                404,
                "missing",
            ),
        )
        return FetchResponse(
            url=url,
            status_code=status_code,
            headers={"content-type": "application/xml"},
            text=text,
        )


SITEMAP_INDEX_URL = "https://assets.grokipedia.com/sitemap/sitemap-index.xml"
SITEMAP_1_URL = "https://assets.grokipedia.com/sitemap/sitemap-00001.xml"
SITEMAP_2_URL = "https://assets.grokipedia.com/sitemap/sitemap-00002.xml"


def _sitemap_index_xml() -> str:
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
  <sitemap><loc>{SITEMAP_1_URL}</loc></sitemap>
  <sitemap><loc>{SITEMAP_2_URL}</loc></sitemap>
</sitemapindex>
"""


def _sitemap_1_xml() -> str:
    return """<?xml version='1.0' encoding='UTF-8'?>
<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
  <url><loc>https://grokipedia.com/page/Alpha</loc></url>
  <url><loc>https://grokipedia.com/page/&quot;Hello,_World!&quot;_program</loc></url>
</urlset>
"""


def _sitemap_2_xml() -> str:
    return """<?xml version='1.0' encoding='UTF-8'?>
<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
  <url><loc>https://grokipedia.com/page/Beta</loc></url>
</urlset>
"""


def test_find_page_url_is_lazy_and_cached() -> None:
    fetcher = StaticFetcher(
        {
            SITEMAP_INDEX_URL: (200, _sitemap_index_xml()),
            SITEMAP_1_URL: (200, _sitemap_1_xml()),
            SITEMAP_2_URL: (200, _sitemap_2_xml()),
        }
    )
    wiki = Grokipedia(fetcher=fetcher, respect_robots=False)

    found = wiki.find_page_url("Alpha")
    again = wiki.find_page_url("Alpha")

    assert found == "https://grokipedia.com/page/Alpha"
    assert again == "https://grokipedia.com/page/Alpha"

    counts = Counter(fetcher.request_urls)
    assert counts[SITEMAP_INDEX_URL] == 1
    assert counts[SITEMAP_1_URL] == 1
    assert counts[SITEMAP_2_URL] == 0


def test_find_page_url_matches_manifest_even_with_escaped_quotes() -> None:
    fetcher = StaticFetcher(
        {
            SITEMAP_INDEX_URL: (200, _sitemap_index_xml()),
            SITEMAP_1_URL: (200, _sitemap_1_xml()),
            SITEMAP_2_URL: (200, _sitemap_2_xml()),
        }
    )
    wiki = Grokipedia(fetcher=fetcher, respect_robots=False)

    found = wiki.find_page_url('"Hello, World!" program')

    assert found == 'https://grokipedia.com/page/"Hello,_World!"_program'


def test_find_page_url_reuses_loaded_sitemaps_across_different_titles() -> None:
    fetcher = StaticFetcher(
        {
            SITEMAP_INDEX_URL: (200, _sitemap_index_xml()),
            SITEMAP_1_URL: (200, _sitemap_1_xml()),
            SITEMAP_2_URL: (200, _sitemap_2_xml()),
        }
    )
    wiki = Grokipedia(fetcher=fetcher, respect_robots=False)

    assert wiki.find_page_url("Alpha") == "https://grokipedia.com/page/Alpha"
    assert wiki.find_page_url("Beta") == "https://grokipedia.com/page/Beta"
    assert wiki.find_page_url("Alpha") == "https://grokipedia.com/page/Alpha"

    counts = Counter(fetcher.request_urls)
    assert counts[SITEMAP_INDEX_URL] == 1
    assert counts[SITEMAP_1_URL] == 1
    assert counts[SITEMAP_2_URL] == 1


def test_find_page_url_propagates_index_fetch_failure_without_child_fetches() -> None:
    fetcher = StaticFetcher(
        {
            SITEMAP_INDEX_URL: (500, "server error"),
            SITEMAP_1_URL: (200, _sitemap_1_xml()),
            SITEMAP_2_URL: (200, _sitemap_2_xml()),
        }
    )
    wiki = Grokipedia(fetcher=fetcher, respect_robots=False)

    try:
        wiki.find_page_url("Alpha")
    except HttpStatusError as exc:
        assert exc.status_code == 500
    else:
        raise AssertionError("Expected HttpStatusError for sitemap index failure")

    counts = Counter(fetcher.request_urls)
    assert counts[SITEMAP_INDEX_URL] == 1
    assert counts[SITEMAP_1_URL] == 0
    assert counts[SITEMAP_2_URL] == 0


def test_refresh_manifest_reloads_index_and_resets_loaded_children() -> None:
    fetcher = StaticFetcher(
        {
            SITEMAP_INDEX_URL: (200, _sitemap_index_xml()),
            SITEMAP_1_URL: (200, _sitemap_1_xml()),
            SITEMAP_2_URL: (200, _sitemap_2_xml()),
        }
    )
    wiki = Grokipedia(fetcher=fetcher, respect_robots=False)

    assert wiki.find_page_url("Alpha") == "https://grokipedia.com/page/Alpha"

    manifest = wiki.refresh_manifest()

    assert manifest == {
        SITEMAP_1_URL: [],
        SITEMAP_2_URL: [],
    }

    assert wiki.find_page_url("Beta") == "https://grokipedia.com/page/Beta"

    counts = Counter(fetcher.request_urls)
    assert counts[SITEMAP_INDEX_URL] == 2
    assert counts[SITEMAP_1_URL] == 2
    assert counts[SITEMAP_2_URL] == 1


def test_grokipedia_verbose_enables_debug_logging() -> None:
    package_logger = logging.getLogger("grokipedia")
    original_level = package_logger.level
    original_handlers = list(package_logger.handlers)
    original_propagate = package_logger.propagate

    try:
        package_logger.handlers = []
        package_logger.setLevel(logging.NOTSET)
        package_logger.propagate = True

        Grokipedia(verbose=True, respect_robots=False)

        assert package_logger.level == logging.DEBUG
        assert any(
            not isinstance(handler, logging.NullHandler)
            for handler in package_logger.handlers
        )
    finally:
        package_logger.handlers = original_handlers
        package_logger.setLevel(original_level)
        package_logger.propagate = original_propagate
