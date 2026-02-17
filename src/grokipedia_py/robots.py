from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from .errors import RobotsDisallowedError, RobotsUnavailableError
from .fetch import Fetcher


def robots_url_for(target_url: str) -> str:
    parsed = urlparse(target_url)
    if not parsed.scheme or not parsed.netloc:
        raise RobotsUnavailableError(
            robots_url="",
            message=f"Could not derive robots.txt URL from target URL: {target_url}",
        )
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def assert_allowed_by_robots(
    target_url: str,
    *,
    fetcher: Fetcher,
    timeout: float,
    user_agent: str,
) -> None:
    robots_url = robots_url_for(target_url)
    try:
        response = fetcher.fetch_text(
            robots_url,
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )
    except Exception as exc:
        raise RobotsUnavailableError(
            robots_url,
            message=f"Could not fetch robots.txt at {robots_url}: {exc}",
        ) from exc

    if response.status_code >= 400:
        raise RobotsUnavailableError(
            robots_url,
            message=(
                f"Could not fetch robots.txt at {robots_url}: "
                f"HTTP {response.status_code}"
            ),
        )

    parser = RobotFileParser()
    try:
        parser.parse(response.text.splitlines())
    except Exception as exc:
        raise RobotsUnavailableError(
            robots_url,
            message=f"Could not parse robots.txt at {robots_url}: {exc}",
        ) from exc

    allowed = parser.can_fetch(user_agent, target_url)
    if not allowed:
        raise RobotsDisallowedError(target_url)

