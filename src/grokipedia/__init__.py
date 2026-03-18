from __future__ import annotations

import logging

from .client import (
    DEFAULT_SITEMAP_INDEX_URL,
    Grokipedia,
    edit_history,
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
    EditHistoryEntry,
    EditHistoryPage,
    InfoboxField,
    LeadFigure,
    Page,
    PageMetadata,
    Reference,
    Section,
    SectionMedia,
)

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "FetchError",
    "FetchResponse",
    "Fetcher",
    "Grokipedia",
    "GrokipediaError",
    "HttpStatusError",
    "EditHistoryEntry",
    "EditHistoryPage",
    "InfoboxField",
    "LeadFigure",
    "Page",
    "PageMetadata",
    "PageNotFoundError",
    "ParseError",
    "Reference",
    "RobotsDisallowedError",
    "RobotsUnavailableError",
    "DEFAULT_SITEMAP_INDEX_URL",
    "Section",
    "SectionMedia",
    "UrllibFetcher",
    "edit_history",
    "from_html",
    "from_url",
    "page",
    "search",
]
