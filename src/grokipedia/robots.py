from __future__ import annotations

import logging
from typing import cast
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from weakref import WeakKeyDictionary

from .errors import RobotsDisallowedError, RobotsUnavailableError
from .fetch import Fetcher

logger = logging.getLogger(__name__)
_ROBOTS_CACHE_BY_FETCHER: WeakKeyDictionary[object, dict[str, RobotFileParser]] = (
    WeakKeyDictionary()
)


def _cache_for_fetcher(fetcher: Fetcher) -> dict[str, RobotFileParser] | None:
    try:
        return _ROBOTS_CACHE_BY_FETCHER.setdefault(cast(object, fetcher), {})
    except TypeError:
        # Some custom fetchers may not support weak references; skip caching for those.
        logger.debug(
            "Robots cache unavailable for fetcher_type=%s (not weakref-able)",
            type(fetcher).__name__,
        )
        return None


def _load_robots_parser(
    robots_url: str,
    *,
    fetcher: Fetcher,
    timeout: float,
    user_agent: str,
) -> RobotFileParser:
    try:
        response = fetcher.fetch_text(
            robots_url,
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )
    except Exception as exc:
        logger.warning("Failed fetching robots robots_url=%s error=%s", robots_url, exc)
        raise RobotsUnavailableError(
            robots_url,
            message=f"Could not fetch robots.txt at {robots_url}: {exc}",
        ) from exc

    if response.status_code >= 400:
        logger.warning(
            "Robots unavailable robots_url=%s status_code=%s",
            robots_url,
            response.status_code,
        )
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
        logger.warning("Failed parsing robots robots_url=%s error=%s", robots_url, exc)
        raise RobotsUnavailableError(
            robots_url,
            message=f"Could not parse robots.txt at {robots_url}: {exc}",
        ) from exc

    return parser


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
    cache = _cache_for_fetcher(fetcher)
    parser = cache.get(robots_url) if cache is not None else None

    if parser is None:
        logger.debug("Robots cache miss robots_url=%s", robots_url)
        parser = _load_robots_parser(
            robots_url,
            fetcher=fetcher,
            timeout=timeout,
            user_agent=user_agent,
        )
        if cache is not None:
            cache[robots_url] = parser
    else:
        logger.debug("Robots cache hit robots_url=%s", robots_url)

    logger.debug(
        "Checking robots target_url=%s robots_url=%s user_agent=%s",
        target_url,
        robots_url,
        user_agent,
    )

    allowed = parser.can_fetch(user_agent, target_url)
    if not allowed:
        logger.info(
            "Robots disallowed target_url=%s user_agent=%s", target_url, user_agent
        )
        raise RobotsDisallowedError(target_url)

    logger.debug("Robots allowed target_url=%s", target_url)
