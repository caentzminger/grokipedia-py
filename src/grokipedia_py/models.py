from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class PageMetadata:
    status_code: int
    fetched_at_utc: datetime
    fact_check_label: str | None
    canonical_url: str | None
    description: str | None


@dataclass(slots=True)
class Reference:
    index: int
    text: str
    url: str | None


@dataclass(slots=True)
class Section:
    id: str | None
    title: str
    level: int
    markdown: str
    subsections: list[Section] = field(default_factory=list)


@dataclass(slots=True)
class Page:
    url: str
    slug: str
    title: str
    lede_markdown: str | None
    sections: list[Section]
    references: list[Reference]
    metadata: PageMetadata

