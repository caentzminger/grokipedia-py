from __future__ import annotations

import pytest

from grokipedia_py import from_url
from grokipedia_py.errors import PageNotFoundError
from grokipedia_py.fetch import FetchResponse


class FakeFetcher:
    def fetch_text(
        self, url: str, *, timeout: float, headers: dict[str, str]
    ) -> FetchResponse:
        if url.endswith("/robots.txt"):
            return FetchResponse(
                url=url,
                status_code=200,
                headers={"content-type": "text/plain"},
                text="User-Agent: *\nDisallow: /api/\n",
            )
        return FetchResponse(
            url=url,
            status_code=404,
            headers={"content-type": "text/html"},
            text="<html><body><h1>Not found</h1></body></html>",
        )


def test_from_url_raises_page_not_found_on_404() -> None:
    with pytest.raises(PageNotFoundError):
        from_url(
            "https://grokipedia.com/page/does_not_exist",
            fetcher=FakeFetcher(),
            user_agent="grokipedia-py-test",
        )
