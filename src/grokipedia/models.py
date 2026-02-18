from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any


@dataclass(slots=True)
class PageMetadata:
    status_code: int
    fetched_at_utc: datetime
    canonical_url: str | None
    description: str | None
    keywords: list[str] | None


@dataclass(slots=True)
class Reference:
    index: int
    text: str
    url: str | None


@dataclass(slots=True)
class InfoboxField:
    label: str
    value: str


@dataclass(slots=True)
class LeadFigure:
    image_url: str
    caption: str | None
    alt_text: str | None


@dataclass(slots=True)
class SectionMedia:
    index: int
    image_url: str
    caption: str | None
    alt_text: str | None


@dataclass(slots=True)
class Section:
    id: str | None
    title: str
    level: int
    text: str
    media: list[SectionMedia] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)


@dataclass(slots=True)
class Page:
    url: str
    slug: str
    title: str
    intro_text: str | None
    infobox: list[InfoboxField]
    lead_figure: LeadFigure | None
    sections: list[Section]
    references: list[Reference]
    metadata: PageMetadata

    @property
    def lede_text(self) -> str | None:
        return self.intro_text

    @property
    def lead_media(self) -> LeadFigure | None:
        return self.lead_figure

    def to_dict(self) -> dict[str, Any]:
        return _to_dict_compatible(asdict(self))

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
        )


def _to_dict_compatible(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat()
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _to_dict_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dict_compatible(item) for item in value]
    return value
