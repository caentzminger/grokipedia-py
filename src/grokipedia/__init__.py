from __future__ import annotations

from .client import from_html, from_url
from .errors import (
    FetchError,
    GrokipediaError,
    HttpStatusError,
    PageNotFoundError,
    ParseError,
    RobotsDisallowedError,
    RobotsUnavailableError,
)
from .fetch import FetchResponse, Fetcher, UrllibFetcher
from .models import Page, PageMetadata, Reference, Section

SITEMAP_INDEX = "https://assets.grokipedia.com/sitemap/sitemap-index.xml"

__all__ = [
    "FetchError",
    "FetchResponse",
    "Fetcher",
    "GrokipediaError",
    "HttpStatusError",
    "Page",
    "PageMetadata",
    "PageNotFoundError",
    "ParseError",
    "Reference",
    "RobotsDisallowedError",
    "RobotsUnavailableError",
    "SITEMAP_INDEX",
    "Section",
    "UrllibFetcher",
    "from_html",
    "from_url",
]
