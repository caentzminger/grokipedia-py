from __future__ import annotations

import json
from typing import Mapping

import pytest

from grokipedia import page, search
from grokipedia.fetch import FetchResponse


class RecordingFetcher:
    def __init__(
        self,
        *,
        search_html: str = "",
        search_json: str | None = None,
        search_api_status: int = 200,
    ) -> None:
        self.search_html = search_html
        self.search_json = search_json or json.dumps({"results": []})
        self.search_api_status = search_api_status
        self.request_urls: list[str] = []

    def fetch_text(
        self, url: str, *, timeout: float, headers: Mapping[str, str]
    ) -> FetchResponse:
        self.request_urls.append(url)

        if url.endswith("/robots.txt"):
            return FetchResponse(
                url=url,
                status_code=200,
                headers={"content-type": "text/plain"},
                text="User-agent: *\nAllow: /\n",
            )

        if "/api/full-text-search?" in url:
            return FetchResponse(
                url=url,
                status_code=self.search_api_status,
                headers={"content-type": "application/json"},
                text=self.search_json,
            )

        if "/search?" in url:
            return FetchResponse(
                url=url,
                status_code=200,
                headers={"content-type": "text/html"},
                text=self.search_html,
            )

        if "/page/" in url:
            return FetchResponse(
                url=url,
                status_code=200,
                headers={"content-type": "text/html"},
                text=(
                    "<html><body><article class='text-[16px]'>"
                    "<h1 id='sample'>Sample Page</h1>"
                    "<p>Sample intro.</p>"
                    "</article></body></html>"
                ),
            )

        return FetchResponse(
            url=url,
            status_code=404,
            headers={"content-type": "text/plain"},
            text="missing",
        )


class RobotsDisallowApiFetcher:
    def __init__(self, *, search_html: str) -> None:
        self.search_html = search_html
        self.request_urls: list[str] = []

    def fetch_text(
        self, url: str, *, timeout: float, headers: Mapping[str, str]
    ) -> FetchResponse:
        self.request_urls.append(url)

        if url.endswith("/robots.txt"):
            return FetchResponse(
                url=url,
                status_code=200,
                headers={"content-type": "text/plain"},
                text="User-agent: *\nDisallow: /api/\n",
            )

        if "/search?" in url:
            return FetchResponse(
                url=url,
                status_code=200,
                headers={"content-type": "text/html"},
                text=self.search_html,
            )

        return FetchResponse(
            url=url,
            status_code=404,
            headers={"content-type": "text/plain"},
            text="missing",
        )


def test_page_builds_expected_title_url() -> None:
    fetcher = RecordingFetcher()

    result = page(
        '"Hello, World!" program',
        fetcher=fetcher,
        user_agent="grokipedia-py-test",
    )

    assert result.title == "Sample Page"
    assert (
        fetcher.request_urls[1]
        == "https://grokipedia.com/page/%22Hello,_World!%22_program"
    )


def test_search_uses_full_text_search_api() -> None:
    fetcher = RecordingFetcher(
        search_json=json.dumps(
            {
                "results": [
                    {"slug": "Foo"},
                    {"slug": '"Hello,_World!"_program'},
                    {"slug": "Foo"},
                ]
            }
        )
    )

    results = search("hello world", fetcher=fetcher, user_agent="grokipedia-py-test")

    assert (
        fetcher.request_urls[1]
        == "https://grokipedia.com/api/full-text-search?query=hello+world&limit=25&offset=0"
    )
    assert results == [
        "https://grokipedia.com/page/Foo",
        "https://grokipedia.com/page/%22Hello,_World!%22_program",
    ]


def test_search_falls_back_to_html_when_api_unavailable() -> None:
    fetcher = RecordingFetcher(
        search_api_status=503,
        search_html=(
            "<html><body>"
            "<a href='/page/Fallback_One'>Fallback one</a>"
            "<a href='/page/Fallback_One#section'>Fallback duplicate</a>"
            "<a href='https://grokipedia.com/page/Fallback_Two'>Fallback two</a>"
            "</body></html>"
        ),
    )

    results = search("fallback", fetcher=fetcher, user_agent="grokipedia-py-test")

    assert (
        fetcher.request_urls[1]
        == "https://grokipedia.com/api/full-text-search?query=fallback&limit=25&offset=0"
    )
    assert fetcher.request_urls[-1] == "https://grokipedia.com/search?q=fallback"
    assert results == [
        "https://grokipedia.com/page/Fallback_One",
        "https://grokipedia.com/page/Fallback_Two",
    ]


def test_search_rejects_empty_query() -> None:
    fetcher = RecordingFetcher()

    with pytest.raises(ValueError):
        search("   ", fetcher=fetcher)

    assert fetcher.request_urls == []


def test_search_falls_back_to_html_when_robots_disallow_api() -> None:
    fetcher = RobotsDisallowApiFetcher(
        search_html=(
            "<html><body>"
            "<a href='/page/Robots_Fallback'>Robots fallback</a>"
            "</body></html>"
        )
    )

    results = search("robots", fetcher=fetcher, user_agent="grokipedia-py-test")

    assert all("/api/full-text-search?" not in url for url in fetcher.request_urls)
    assert fetcher.request_urls[-1] == "https://grokipedia.com/search?q=robots"
    assert fetcher.request_urls.count("https://grokipedia.com/robots.txt") == 1
    assert results == ["https://grokipedia.com/page/Robots_Fallback"]
