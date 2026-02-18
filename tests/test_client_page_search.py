from __future__ import annotations

import json
from typing import Mapping

import pytest

from grokipedia import from_url, page, search
from grokipedia.client import DEFAULT_USER_AGENT
from grokipedia.fetch import FetchResponse


def _robots_response(url: str, *, disallow_api: bool) -> FetchResponse:
    robots_text = (
        "User-agent: *\nDisallow: /api/\n"
        if disallow_api
        else "User-agent: *\nAllow: /\n"
    )
    return FetchResponse(
        url=url,
        status_code=200,
        headers={"content-type": "text/plain"},
        text=robots_text,
    )


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
        self.request_headers: list[dict[str, str]] = []

    def fetch_text(
        self, url: str, *, timeout: float, headers: Mapping[str, str]
    ) -> FetchResponse:
        self.request_urls.append(url)
        self.request_headers.append(dict(headers))

        if url.endswith("/robots.txt"):
            return _robots_response(url, disallow_api=False)

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
        self.request_headers: list[dict[str, str]] = []

    def fetch_text(
        self, url: str, *, timeout: float, headers: Mapping[str, str]
    ) -> FetchResponse:
        self.request_urls.append(url)
        self.request_headers.append(dict(headers))

        if url.endswith("/robots.txt"):
            return _robots_response(url, disallow_api=True)

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


class RichPageFetcher:
    def __init__(self) -> None:
        self.request_urls: list[str] = []
        self.request_headers: list[dict[str, str]] = []

    def fetch_text(
        self, url: str, *, timeout: float, headers: Mapping[str, str]
    ) -> FetchResponse:
        self.request_urls.append(url)
        self.request_headers.append(dict(headers))

        if url.endswith("/robots.txt"):
            return _robots_response(url, disallow_api=False)

        if "/page/" in url:
            return FetchResponse(
                url=url,
                status_code=200,
                headers={"content-type": "text/html"},
                text=(
                    "<html><head>"
                    "<meta name='keywords' content='sample, testing' />"
                    "</head><body><article class='text-[16px]'>"
                    "<h1 id='sample'>Sample Page</h1>"
                    "<span data-tts-block='true'>Sample intro text.</span>"
                    "<div><dt>Founded</dt><dd>2020</dd></div>"
                    "<figure>"
                    "<img src='https://assets.grokipedia.com/wiki/images/lead.jpg' alt='Lead image' />"
                    "<figcaption>Lead caption</figcaption>"
                    "</figure>"
                    "<h2 id='overview'>Overview</h2>"
                    "<h3 id='details'>Details</h3>"
                    "<span data-tts-block='true'>Details body text.</span>"
                    "<figure>"
                    "<img src='https://assets.grokipedia.com/wiki/images/detail.jpg' alt='Detail image' />"
                    "<figcaption>Detail caption</figcaption>"
                    "</figure>"
                    "</article></body></html>"
                ),
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


def test_search_uses_default_user_agent_when_unspecified() -> None:
    fetcher = RecordingFetcher()

    search("hello world", fetcher=fetcher, respect_robots=False)

    assert fetcher.request_headers
    assert all(
        headers.get("User-Agent") == DEFAULT_USER_AGENT
        for headers in fetcher.request_headers
    )


def test_search_skips_robots_when_respect_robots_false() -> None:
    fetcher = RecordingFetcher()

    search("hello world", fetcher=fetcher, respect_robots=False)

    assert all(not url.endswith("/robots.txt") for url in fetcher.request_urls)


def test_search_skips_robots_when_allow_override_true() -> None:
    fetcher = RecordingFetcher()

    search("hello world", fetcher=fetcher, allow_robots_override=True)

    assert all(not url.endswith("/robots.txt") for url in fetcher.request_urls)


def test_from_url_parses_structured_page_fields() -> None:
    fetcher = RichPageFetcher()

    page_obj = from_url("https://grokipedia.com/page/Sample_Page", fetcher=fetcher)

    assert page_obj.title == "Sample Page"
    assert page_obj.slug == "Sample_Page"
    assert page_obj.intro_text == "Sample intro text."
    assert page_obj.infobox[0].label == "Founded"
    assert page_obj.infobox[0].value == "2020"
    assert page_obj.lead_figure is not None
    assert page_obj.sections[0].title == "Overview"
    assert page_obj.sections[0].subsections[0].title == "Details"
    assert page_obj.sections[0].subsections[0].media[0].caption == "Detail caption"
    assert page_obj.metadata.keywords == ["sample", "testing"]
