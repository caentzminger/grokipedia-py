from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


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
    links: list[str]
    metadata: PageMetadata

    @property
    def lede_text(self) -> str | None:
        return self.intro_text

    @property
    def lead_media(self) -> LeadFigure | None:
        return self.lead_figure

    @property
    def markdown(self) -> str:
        blocks: list[str] = [f"# {self.title}"]

        if self.intro_text:
            blocks.append(self.intro_text)

        if self.infobox:
            infobox_lines = [
                f"- **{field.label}:** {field.value}" for field in self.infobox
            ]
            blocks.append("## Infobox\n" + "\n".join(infobox_lines))

        if self.lead_figure is not None:
            blocks.append(
                _render_markdown_media(
                    image_url=self.lead_figure.image_url,
                    alt_text=self.lead_figure.alt_text,
                    caption=self.lead_figure.caption,
                )
            )

        for section in self.sections:
            blocks.append(f"## {section.title}")
            if section.text:
                blocks.append(section.text)

            for media in section.media:
                blocks.append(
                    _render_markdown_media(
                        image_url=media.image_url,
                        alt_text=media.alt_text,
                        caption=media.caption,
                    )
                )

            for subsection in section.subsections:
                blocks.append(f"### {subsection.title}")
                if subsection.text:
                    blocks.append(subsection.text)

                for media in subsection.media:
                    blocks.append(
                        _render_markdown_media(
                            image_url=media.image_url,
                            alt_text=media.alt_text,
                            caption=media.caption,
                        )
                    )

        return "\n\n".join(block for block in blocks if block.strip())

    def to_dict(self) -> dict[str, Any]:
        return _to_dict_compatible(asdict(self))

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Page:
        metadata_raw = data.get("metadata")
        if not isinstance(metadata_raw, Mapping):
            raise ValueError("Page data must include object field 'metadata'")

        return cls(
            url=str(data.get("url", "")),
            slug=str(data.get("slug", "")),
            title=str(data.get("title", "")),
            intro_text=_optional_str(data.get("intro_text")),
            infobox=_infobox_from_data(data.get("infobox")),
            lead_figure=_lead_figure_from_data(data.get("lead_figure")),
            sections=_sections_from_data(data.get("sections")),
            references=_references_from_data(data.get("references")),
            links=_links_from_data(data.get("links")),
            metadata=_metadata_from_data(metadata_raw),
        )

    @classmethod
    def from_json(cls, payload: str) -> Page:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Page JSON must decode to an object")
        return cls.from_dict(data)


def _render_markdown_media(
    *,
    image_url: str,
    alt_text: str | None,
    caption: str | None,
) -> str:
    image_line = f"![{alt_text or ''}]({image_url})"
    if caption:
        return f"{image_line}\n*{caption}*"
    return image_line


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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _parse_datetime_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        dt = datetime.fromisoformat(normalized)
    else:
        raise ValueError("metadata.fetched_at_utc must be an ISO datetime string")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _metadata_from_data(value: Mapping[str, Any]) -> PageMetadata:
    status_code_raw = value.get("status_code")
    if not isinstance(status_code_raw, int):
        raise ValueError("metadata.status_code must be an integer")

    return PageMetadata(
        status_code=status_code_raw,
        fetched_at_utc=_parse_datetime_utc(value.get("fetched_at_utc")),
        canonical_url=_optional_str(value.get("canonical_url")),
        description=_optional_str(value.get("description")),
        keywords=_keywords_from_data(value.get("keywords")),
    )


def _keywords_from_data(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("metadata.keywords must be an array of strings or null")
    return [str(item) for item in value if str(item)]


def _infobox_from_data(value: Any) -> list[InfoboxField]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("infobox must be an array")

    fields: list[InfoboxField] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        fields.append(
            InfoboxField(
                label=str(item.get("label", "")),
                value=str(item.get("value", "")),
            )
        )
    return fields


def _lead_figure_from_data(value: Any) -> LeadFigure | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("lead_figure must be an object or null")

    image_url = str(value.get("image_url", ""))
    if not image_url:
        return None

    return LeadFigure(
        image_url=image_url,
        caption=_optional_str(value.get("caption")),
        alt_text=_optional_str(value.get("alt_text")),
    )


def _section_media_from_data(value: Any) -> list[SectionMedia]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("section media must be an array")

    media: list[SectionMedia] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue

        raw_index = item.get("index")
        media_index = (
            raw_index if isinstance(raw_index, int) and raw_index > 0 else index
        )

        image_url = str(item.get("image_url", ""))
        if not image_url:
            continue

        media.append(
            SectionMedia(
                index=media_index,
                image_url=image_url,
                caption=_optional_str(item.get("caption")),
                alt_text=_optional_str(item.get("alt_text")),
            )
        )
    return media


def _section_from_data(value: Any) -> Section:
    if not isinstance(value, Mapping):
        raise ValueError("section entries must be objects")

    return Section(
        id=_optional_str(value.get("id")),
        title=str(value.get("title", "")),
        level=int(value.get("level", 2)),
        text=str(value.get("text", "")),
        media=_section_media_from_data(value.get("media")),
        subsections=_sections_from_data(value.get("subsections")),
    )


def _sections_from_data(value: Any) -> list[Section]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("sections must be an array")

    sections: list[Section] = []
    for item in value:
        sections.append(_section_from_data(item))
    return sections


def _references_from_data(value: Any) -> list[Reference]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("references must be an array")

    references: list[Reference] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue

        raw_index = item.get("index")
        ref_index = raw_index if isinstance(raw_index, int) and raw_index > 0 else index

        references.append(
            Reference(
                index=ref_index,
                text=str(item.get("text", "")),
                url=_optional_str(item.get("url")),
            )
        )
    return references


def _links_from_data(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("links must be an array")
    return [str(item) for item in value if str(item)]
