from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from .errors import RobotsDisallowedError, RobotsUnavailableError
from .fetch import Fetcher

logger = logging.getLogger(__name__)


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
    logger.debug(
        "Checking robots target_url=%s robots_url=%s user_agent=%s",
        target_url,
        robots_url,
        user_agent,
    )
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

    allowed = parser.can_fetch(user_agent, target_url)
    if not allowed:
        logger.info(
            "Robots disallowed target_url=%s user_agent=%s", target_url, user_agent
        )
        raise RobotsDisallowedError(target_url)

    logger.debug("Robots allowed target_url=%s", target_url)
