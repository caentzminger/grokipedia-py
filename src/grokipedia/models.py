from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, cast


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
            _append_section_markdown(blocks, section)

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


@dataclass(slots=True)
class EditHistoryEntry:
    id: str
    slug: str
    user_id: str
    status: str
    type: str
    summary: str
    original_content: str | None
    proposed_content: str | None
    section_title: str | None
    created_at_utc: datetime
    updated_at_utc: datetime
    upvote_count: int
    downvote_count: int
    review_reason: str | None


@dataclass(slots=True)
class EditHistoryPage:
    edit_requests: list[EditHistoryEntry]
    total_count: int
    has_more: bool

    def to_dict(self) -> dict[str, Any]:
        return _to_dict_compatible(asdict(self))

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EditHistoryPage:
        return _edit_history_page_from_data(data)

    @classmethod
    def from_json(cls, payload: str) -> EditHistoryPage:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Edit history JSON must decode to an object")
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


def _append_section_markdown(blocks: list[str], section: Section) -> None:
    heading_prefix = "#" * max(1, section.level)
    blocks.append(f"{heading_prefix} {section.title}")

    if section.text:
        blocks.append(section.text)

    _append_section_media_markdown(blocks, section.media)
    for subsection in section.subsections:
        _append_section_markdown(blocks, subsection)


def _append_section_media_markdown(
    blocks: list[str],
    media_items: list[SectionMedia],
) -> None:
    for media in media_items:
        blocks.append(
            _render_markdown_media(
                image_url=media.image_url,
                alt_text=media.alt_text,
                caption=media.caption,
            )
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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _string_mapping(value: object) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return cast("Mapping[str, Any]", value)


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
        mapping_item = _string_mapping(item)
        if mapping_item is None:
            continue
        fields.append(
            InfoboxField(
                label=str(mapping_item.get("label", "")),
                value=str(mapping_item.get("value", "")),
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
        mapping_item = _string_mapping(item)
        if mapping_item is None:
            continue

        raw_index = mapping_item.get("index")
        media_index = (
            raw_index if isinstance(raw_index, int) and raw_index > 0 else index
        )

        image_url = str(mapping_item.get("image_url", ""))
        if not image_url:
            continue

        media.append(
            SectionMedia(
                index=media_index,
                image_url=image_url,
                caption=_optional_str(mapping_item.get("caption")),
                alt_text=_optional_str(mapping_item.get("alt_text")),
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
    return [_section_from_data(item) for item in value]


def _references_from_data(value: Any) -> list[Reference]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("references must be an array")

    references: list[Reference] = []
    for index, item in enumerate(value, start=1):
        mapping_item = _string_mapping(item)
        if mapping_item is None:
            continue

        raw_index = mapping_item.get("index")
        ref_index = raw_index if isinstance(raw_index, int) and raw_index > 0 else index

        references.append(
            Reference(
                index=ref_index,
                text=str(mapping_item.get("text", "")),
                url=_optional_str(mapping_item.get("url")),
            )
        )
    return references


def _links_from_data(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("links must be an array")
    return [str(item) for item in value if str(item)]


def _optional_non_empty_str(value: Any) -> str | None:
    text = _optional_str(value)
    if text is None:
        return None
    stripped = text.strip()
    return stripped or None


def _mapping_value(value: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in value:
            return value[key]
    return default


def _parse_epoch_utc(value: Any, *, field_name: str) -> datetime:
    if isinstance(value, int):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        return _parse_datetime_utc(value)
    raise ValueError(
        f"{field_name} must be an integer Unix timestamp or ISO datetime string"
    )


def _edit_history_entry_from_data(value: Any) -> EditHistoryEntry:
    if not isinstance(value, Mapping):
        raise ValueError("edit history entries must be objects")

    return EditHistoryEntry(
        id=str(value.get("id", "")),
        slug=str(value.get("slug", "")),
        user_id=str(_mapping_value(value, "userId", "user_id", default="")),
        status=str(value.get("status", "")),
        type=str(value.get("type", "")),
        summary=str(value.get("summary", "")),
        original_content=_optional_non_empty_str(
            _mapping_value(value, "originalContent", "original_content")
        ),
        proposed_content=_optional_non_empty_str(
            _mapping_value(value, "proposedContent", "proposed_content")
        ),
        section_title=_optional_non_empty_str(
            _mapping_value(value, "sectionTitle", "section_title")
        ),
        created_at_utc=_parse_epoch_utc(
            _mapping_value(value, "createdAt", "created_at_utc"),
            field_name="editRequests[].createdAt",
        ),
        updated_at_utc=_parse_epoch_utc(
            _mapping_value(value, "updatedAt", "updated_at_utc"),
            field_name="editRequests[].updatedAt",
        ),
        upvote_count=int(
            _mapping_value(value, "upvoteCount", "upvote_count", default=0)
        ),
        downvote_count=int(
            _mapping_value(value, "downvoteCount", "downvote_count", default=0)
        ),
        review_reason=_optional_non_empty_str(
            _mapping_value(value, "reviewReason", "review_reason")
        ),
    )


def _edit_history_entries_from_data(value: Any) -> list[EditHistoryEntry]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("editRequests must be an array")
    return [_edit_history_entry_from_data(item) for item in value]


def _edit_history_page_from_data(value: Mapping[str, Any]) -> EditHistoryPage:
    total_count_raw = _mapping_value(value, "totalCount", "total_count", default=0)
    has_more_raw = _mapping_value(value, "hasMore", "has_more", default=False)

    if not isinstance(total_count_raw, int):
        raise ValueError("totalCount must be an integer")
    if not isinstance(has_more_raw, bool):
        raise ValueError("hasMore must be a boolean")

    return EditHistoryPage(
        edit_requests=_edit_history_entries_from_data(
            _mapping_value(value, "editRequests", "edit_requests")
        ),
        total_count=total_count_raw,
        has_more=has_more_raw,
    )
