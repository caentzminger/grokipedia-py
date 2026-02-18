from __future__ import annotations

from typing import Protocol

from .fetch import FetchResponse, Fetcher


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
