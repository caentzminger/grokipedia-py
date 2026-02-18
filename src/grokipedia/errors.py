from __future__ import annotations


class GrokipediaError(Exception):
    pass


class FetchError(GrokipediaError):
    pass


class HttpStatusError(FetchError):
    def __init__(self, status_code: int, url: str, message: str | None = None) -> None:
        self.status_code = status_code
        self.url = url
        text = message or f"Unexpected HTTP status {status_code} for URL: {url}"
        super().__init__(text)


class PageNotFoundError(HttpStatusError):
    def __init__(self, url: str) -> None:
        super().__init__(status_code=404, url=url, message=f"Page not found: {url}")


class RobotsDisallowedError(GrokipediaError):
    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"URL disallowed by robots.txt: {url}")


class RobotsUnavailableError(GrokipediaError):
    def __init__(self, robots_url: str, message: str | None = None) -> None:
        self.robots_url = robots_url
        text = message or f"Could not validate robots.txt: {robots_url}"
        super().__init__(text)


class ParseError(GrokipediaError):
    pass
