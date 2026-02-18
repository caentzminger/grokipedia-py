from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any


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
class InfoboxField:
    label: str
    value: str


@dataclass(slots=True)
class LeadMedia:
    image_url: str
    caption: str | None
    alt_text: str | None


@dataclass(slots=True)
class Section:
    id: str | None
    title: str
    level: int
    text: str
    subsections: list[Section] = field(default_factory=list)


@dataclass(slots=True)
class Page:
    url: str
    slug: str
    title: str
    lede_text: str | None
    infobox: list[InfoboxField]
    lead_media: LeadMedia | None
    sections: list[Section]
    references: list[Reference]
    metadata: PageMetadata

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
