from __future__ import annotations

import logging

from .client import (
    DEFAULT_SITEMAP_INDEX_URL,
    Grokipedia,
    from_html,
    from_url,
    page,
    search,
)
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
from .models import (
    InfoboxField,
    LeadFigure,
    Page,
    PageMetadata,
    Reference,
    Section,
    SectionMedia,
)

SITEMAP_INDEX = DEFAULT_SITEMAP_INDEX_URL

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "FetchError",
    "FetchResponse",
    "Fetcher",
    "Grokipedia",
    "GrokipediaError",
    "HttpStatusError",
    "InfoboxField",
    "LeadFigure",
    "Page",
    "PageMetadata",
    "PageNotFoundError",
    "ParseError",
    "Reference",
    "RobotsDisallowedError",
    "RobotsUnavailableError",
    "SITEMAP_INDEX",
    "Section",
    "SectionMedia",
    "UrllibFetcher",
    "from_html",
    "from_url",
    "page",
    "search",
]
