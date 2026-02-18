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
