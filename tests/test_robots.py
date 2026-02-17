from __future__ import annotations

import pytest

from grokipedia_py.errors import RobotsDisallowedError, RobotsUnavailableError
from grokipedia_py.fetch import FetchResponse
from grokipedia_py.robots import assert_allowed_by_robots


class FakeFetcher:
    def __init__(
        self, *, robots_text: str, robots_status: int = 200, should_raise: bool = False
    ) -> None:
        self._robots_text = robots_text
        self._robots_status = robots_status
        self._should_raise = should_raise

    def fetch_text(
        self, url: str, *, timeout: float, headers: dict[str, str]
    ) -> FetchResponse:
        if self._should_raise:
            raise RuntimeError("network down")
        return FetchResponse(
            url=url,
            status_code=self._robots_status,
            headers={"content-type": "text/plain"},
            text=self._robots_text,
        )


def test_robots_allows_page_urls() -> None:
    fetcher = FakeFetcher(robots_text="User-Agent: *\nDisallow: /api/\n")

    assert_allowed_by_robots(
        "https://grokipedia.com/page/13065923",
        fetcher=fetcher,
        timeout=5,
        user_agent="grokipedia-py-test",
    )


def test_robots_blocks_disallowed_urls() -> None:
    fetcher = FakeFetcher(robots_text="User-Agent: *\nDisallow: /api/\n")

    with pytest.raises(RobotsDisallowedError):
        assert_allowed_by_robots(
            "https://grokipedia.com/api/private",
            fetcher=fetcher,
            timeout=5,
            user_agent="grokipedia-py-test",
        )


def test_robots_unavailable_on_http_error() -> None:
    fetcher = FakeFetcher(robots_text="", robots_status=503)

    with pytest.raises(RobotsUnavailableError):
        assert_allowed_by_robots(
            "https://grokipedia.com/page/13065923",
            fetcher=fetcher,
            timeout=5,
            user_agent="grokipedia-py-test",
        )


def test_robots_unavailable_on_fetch_failure() -> None:
    fetcher = FakeFetcher(robots_text="", should_raise=True)

    with pytest.raises(RobotsUnavailableError):
        assert_allowed_by_robots(
            "https://grokipedia.com/page/13065923",
            fetcher=fetcher,
            timeout=5,
            user_agent="grokipedia-py-test",
        )
