from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
import logging
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from .errors import ParseError
from .models import (
    InfoboxField,
    LeadFigure,
    Page,
    PageMetadata,
    Reference,
    Section,
    SectionMedia,
)

logger = logging.getLogger(__name__)

_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

_SKIP_INLINE_TAGS = {
    "button",
    "script",
    "style",
    "svg",
    "path",
    "noscript",
}

_SKIP_SUBTREE_TAGS = {
    "script",
    "style",
    "noscript",
}


@dataclass(slots=True)
class _Node:
    tag: str
    attrs: dict[str, str]
    children: list[_Node | str] = field(default_factory=list)


class _DOMBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node(tag="document", attrs={})
        self._stack: list[_Node] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(
            tag=tag.lower(),
            attrs={key.lower(): (value or "") for key, value in attrs},
        )
        self._stack[-1].children.append(node)
        if node.tag not in _VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(
            tag=tag.lower(),
            attrs={key.lower(): (value or "") for key, value in attrs},
        )
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        target = tag.lower()
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == target:
                del self._stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if data:
            self._stack[-1].children.append(data)


@dataclass(slots=True)
class _FigureData:
    image_url: str
    caption: str | None
    alt_text: str | None


@dataclass(slots=True)
class _Block:
    kind: str
    text: str
    node: _Node | None
    heading_level: int | None = None
    heading_id: str | None = None
    heading_title: str | None = None
    figure: _FigureData | None = None


def parse_page_html(
    html: str,
    *,
    source_url: str | None,
    status_code: int,
    fetched_at_utc: datetime | None = None,
) -> Page:
    logger.debug("Parsing HTML source_url=%s status_code=%s", source_url, status_code)
    builder = _DOMBuilder()
    try:
        builder.feed(html)
    except Exception as exc:
        raise ParseError(f"Unable to parse HTML: {exc}") from exc

    root = builder.root
    article = _select_article(root)
    if article is None:
        raise ParseError("Could not identify main content article")

    canonical_url = _extract_canonical_url(root)
    page_url = source_url or canonical_url or ""

    blocks = _extract_blocks(article, base_url=page_url)
    title = _extract_title(blocks)
    if not title:
        title = _extract_meta_title(root)
    if not title:
        raise ParseError("Could not extract page title")

    intro_text = _extract_intro(blocks)
    infobox = _extract_infobox(article)
    lead_figure = _extract_lead_figure(article, base_url=page_url)
    sections, references = _build_sections_and_references(blocks)
    _attach_markdown_media_from_payload(html, sections, base_url=page_url)
    links = _extract_links(article, base_url=page_url)

    metadata = PageMetadata(
        status_code=status_code,
        fetched_at_utc=fetched_at_utc or datetime.now(timezone.utc),
        canonical_url=canonical_url,
        description=_extract_description(root),
        keywords=_extract_keywords(root),
    )

    media_count = sum(
        len(section.media)
        + sum(len(subsection.media) for subsection in section.subsections)
        for section in sections
    )
    logger.debug(
        "Parsed page title=%s sections=%d references=%d media=%d keywords=%d",
        title,
        len(sections),
        len(references),
        media_count,
        len(metadata.keywords or []),
    )

    return Page(
        url=page_url,
        slug=_extract_slug(page_url),
        title=title,
        intro_text=intro_text,
        infobox=infobox,
        lead_figure=lead_figure,
        sections=sections,
        references=references,
        links=links,
        metadata=metadata,
    )


def _iter_nodes(node: _Node) -> Iterable[_Node]:
    yield node
    for child in node.children:
        if isinstance(child, _Node):
            yield from _iter_nodes(child)


def _text_content(node: _Node, *, preserve_whitespace: bool = False) -> str:
    fragments: list[str] = []

    def visit(current: _Node | str) -> None:
        if isinstance(current, str):
            fragments.append(current)
            return

        if current.tag in _SKIP_INLINE_TAGS:
            return

        for child in current.children:
            visit(child)

    visit(node)
    text = "".join(fragments)
    if preserve_whitespace:
        return text
    return _normalize_ws(text)


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def _extract_meta_title(root: _Node) -> str | None:
    for node in _iter_nodes(root):
        if node.tag == "meta":
            prop = node.attrs.get("property", "")
            name = node.attrs.get("name", "")
            if prop == "og:title" or name == "twitter:title":
                content = _normalize_ws(node.attrs.get("content", ""))
                if content:
                    return content

        if node.tag == "title":
            title = _normalize_ws(_text_content(node))
            if title:
                return title

    return None


def _extract_canonical_url(root: _Node) -> str | None:
    for node in _iter_nodes(root):
        if node.tag == "link" and node.attrs.get("rel", "").lower() == "canonical":
            href = node.attrs.get("href", "").strip()
            if href:
                return href

    for node in _iter_nodes(root):
        if node.tag != "meta":
            continue

        prop = node.attrs.get("property", "")
        if prop in {"og:url", "twitter:url"}:
            content = node.attrs.get("content", "").strip()
            if content:
                return content

    return None


def _extract_description(root: _Node) -> str | None:
    for node in _iter_nodes(root):
        if node.tag != "meta":
            continue

        name = node.attrs.get("name", "")
        prop = node.attrs.get("property", "")
        if name == "description" or prop == "og:description":
            content = _normalize_ws(node.attrs.get("content", ""))
            if content:
                return content

    return None


def _extract_keywords(root: _Node) -> list[str] | None:
    for node in _iter_nodes(root):
        if node.tag != "meta":
            continue

        name = node.attrs.get("name", "").lower()
        item_prop = node.attrs.get("itemprop", "").lower()
        if name != "keywords" and item_prop != "keywords":
            continue

        content = node.attrs.get("content", "")
        if not content:
            continue

        keywords = [_normalize_ws(part) for part in content.split(",")]
        values = [keyword for keyword in keywords if keyword]
        if values:
            return values

    return None


def _extract_slug(url: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url)
    path = parsed.path
    if path.startswith("/page/"):
        slug = path[len("/page/") :]
        return unquote(slug)

    return unquote(path.strip("/"))


def _extract_links(article: _Node, *, base_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()

    for node in _iter_nodes(article):
        if node.tag != "a":
            continue

        href = node.attrs.get("href", "").strip()
        if not href:
            continue

        resolved = urljoin(base_url, href) if base_url else href
        if resolved in seen:
            continue

        seen.add(resolved)
        links.append(resolved)

    return links


def _extract_infobox(article: _Node) -> list[InfoboxField]:
    fields: list[InfoboxField] = []

    for container in _iter_nodes(article):
        direct_children = [
            child for child in container.children if isinstance(child, _Node)
        ]
        if not any(child.tag == "dt" for child in direct_children):
            continue

        pending_label: str | None = None
        for child in direct_children:
            if child.tag == "dt":
                label = _normalize_ws(_render_inline(child))
                pending_label = label or None
                continue

            if child.tag == "dd" and pending_label:
                value = _normalize_ws(_render_inline(child))
                if value:
                    fields.append(InfoboxField(label=pending_label, value=value))
                pending_label = None

    return fields


def _extract_lead_figure(article: _Node, *, base_url: str) -> LeadFigure | None:
    for node in _iter_nodes(article):
        if node.tag != "figure":
            continue

        figure = _extract_figure_data(node, base_url=base_url)
        if figure is None:
            continue

        return LeadFigure(
            image_url=figure.image_url,
            caption=figure.caption,
            alt_text=figure.alt_text,
        )

    return None


def _extract_figure_data(node: _Node, *, base_url: str) -> _FigureData | None:
    image_node = next(
        (child for child in _iter_nodes(node) if child.tag == "img"), None
    )
    if image_node is None:
        return None

    raw_src = image_node.attrs.get("src", "").strip()
    if not raw_src:
        raw_srcset = image_node.attrs.get("srcset", "").strip()
        if raw_srcset:
            raw_src = raw_srcset.split(",", maxsplit=1)[0].split(" ", maxsplit=1)[0]
    if not raw_src:
        return None

    image_url = _normalize_image_url(raw_src, base_url)

    caption_node = next(
        (child for child in _iter_nodes(node) if child.tag == "figcaption"),
        None,
    )
    caption = _normalize_ws(_render_inline(caption_node)) if caption_node else ""
    caption = caption or None

    alt_text = _normalize_ws(image_node.attrs.get("alt", ""))
    alt_text = alt_text or None

    return _FigureData(image_url=image_url, caption=caption, alt_text=alt_text)


def _normalize_image_url(raw_src: str, base_url: str) -> str:
    resolved = urljoin(base_url, raw_src) if base_url else raw_src
    parsed = urlparse(resolved)
    if parsed.path == "/_next/image":
        query = parse_qs(parsed.query)
        image_values = query.get("url")
        if image_values:
            inner = unquote(image_values[0])
            return urljoin(base_url, inner) if base_url else inner

    return resolved


def _select_article(root: _Node) -> _Node | None:
    articles = [node for node in _iter_nodes(root) if node.tag == "article"]
    if not articles:
        return None

    for article in articles:
        classes = article.attrs.get("class", "")
        if "text-[16px]" in classes:
            return article

    for article in articles:
        headings = [
            node for node in _iter_nodes(article) if node.tag in {"h1", "h2", "h3"}
        ]
        has_h1 = any(node.tag == "h1" for node in headings)
        has_references = any(_is_references_heading(node) for node in headings)
        if has_h1 and has_references:
            return article

    return articles[0]


def _extract_blocks(article: _Node, *, base_url: str) -> list[_Block]:
    blocks: list[_Block] = []

    def visit(node: _Node) -> None:
        if node.tag in _SKIP_SUBTREE_TAGS:
            return

        if node.tag in {"h1", "h2", "h3"}:
            title = _normalize_ws(_render_inline(node))
            if title:
                blocks.append(
                    _Block(
                        kind="heading",
                        text="",
                        node=node,
                        heading_level=int(node.tag[-1]),
                        heading_id=node.attrs.get("id") or None,
                        heading_title=title,
                    )
                )
            return

        if node.tag == "p":
            text = _normalize_ws(_render_inline(node))
            if text:
                blocks.append(_Block(kind="paragraph", text=text, node=node))
            return

        if node.tag == "span" and node.attrs.get("data-tts-block") == "true":
            text = _normalize_ws(_render_inline(node))
            if text:
                blocks.append(_Block(kind="paragraph", text=text, node=node))
            return

        if node.tag == "figure":
            figure = _extract_figure_data(node, base_url=base_url)
            if figure:
                blocks.append(_Block(kind="figure", text="", node=node, figure=figure))
            return

        if node.tag in {"ul", "ol"}:
            text = _render_list(node)
            if text:
                blocks.append(_Block(kind="list", text=text, node=node))
            return

        if node.tag == "pre":
            text = _render_pre(node)
            if text:
                blocks.append(_Block(kind="code", text=text, node=node))
            return

        if node.tag == "blockquote":
            quote = _normalize_ws(_render_inline(node))
            if quote:
                blocks.append(_Block(kind="blockquote", text=quote, node=node))
            return

        for child in node.children:
            if isinstance(child, _Node):
                visit(child)

    visit(article)
    return blocks


def _render_inline(node: _Node | str, *, in_code: bool = False) -> str:
    if isinstance(node, str):
        return node

    tag = node.tag
    if tag in _SKIP_INLINE_TAGS:
        return ""
    if tag == "br":
        return "\n"

    children = "".join(
        _render_inline(child, in_code=in_code) for child in node.children
    )

    if tag == "a":
        text = _normalize_ws(children)
        href = node.attrs.get("href", "").strip()
        if href and text:
            return text
        return text or href

    if tag == "code" and not in_code:
        text = _normalize_ws(children)
        return text

    return children


def _render_list(node: _Node) -> str:
    ordered = node.tag == "ol"
    items = [
        child
        for child in node.children
        if isinstance(child, _Node) and child.tag == "li"
    ]
    if not items:
        items = [child for child in _iter_nodes(node) if child.tag == "li"]

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        text = _normalize_ws(_render_inline(item))
        if not text:
            continue

        prefix = f"{index}." if ordered else "-"
        lines.append(f"{prefix} {text}")

    return "\n".join(lines)


def _render_pre(node: _Node) -> str:
    code_node: _Node | None = None
    for child in node.children:
        if isinstance(child, _Node) and child.tag == "code":
            code_node = child
            break

    if code_node is not None:
        code = _text_content(code_node, preserve_whitespace=True)
    else:
        code = _text_content(node, preserve_whitespace=True)

    code = code.strip("\n")
    if not code:
        return ""

    return code


def _extract_title(blocks: list[_Block]) -> str | None:
    for block in blocks:
        if block.kind == "heading" and block.heading_level == 1 and block.heading_title:
            return block.heading_title

    return None


def _extract_intro(blocks: list[_Block]) -> str | None:
    first_h2_index = next(
        (
            index
            for index, block in enumerate(blocks)
            if block.kind == "heading" and block.heading_level == 2
        ),
        None,
    )

    end = first_h2_index if first_h2_index is not None else len(blocks)
    for block in blocks[:end]:
        if block.kind == "paragraph":
            return block.text

    return None


def _append_text(current: str, addition: str) -> str:
    if not addition:
        return current
    if not current:
        return addition
    return f"{current}\n\n{addition}"


def _build_sections_and_references(
    blocks: list[_Block],
) -> tuple[list[Section], list[Reference]]:
    sections: list[Section] = []
    references: list[Reference] = []
    current_section: Section | None = None
    current_subsection: Section | None = None
    in_references = False

    for block in blocks:
        if block.kind == "heading":
            if block.heading_level == 1:
                continue

            heading_title = block.heading_title or ""

            if block.heading_level == 2:
                current_section = Section(
                    id=block.heading_id,
                    title=heading_title,
                    level=2,
                    text="",
                    media=[],
                    subsections=[],
                )
                sections.append(current_section)
                current_subsection = None
                in_references = _normalize_ws(heading_title).lower() == "references"
                continue

            if block.heading_level == 3:
                if current_section is None:
                    current_section = Section(
                        id=None,
                        title="Overview",
                        level=2,
                        text="",
                        media=[],
                        subsections=[],
                    )
                    sections.append(current_section)

                current_subsection = Section(
                    id=block.heading_id,
                    title=heading_title,
                    level=3,
                    text="",
                    media=[],
                    subsections=[],
                )
                current_section.subsections.append(current_subsection)
                in_references = _normalize_ws(heading_title).lower() == "references"
                continue

        target_section = current_subsection or current_section
        if target_section is None:
            continue

        if block.kind == "figure" and block.figure is not None:
            _append_section_media(target_section, block.figure)
            continue

        target_section.text = _append_text(target_section.text, block.text)

        if in_references and block.kind == "list" and block.node is not None:
            start_index = len(references) + 1
            references.extend(
                _extract_references_from_list(block.node, start_index=start_index)
            )

    return sections, references


def _attach_markdown_media_from_payload(
    html: str,
    sections: list[Section],
    *,
    base_url: str,
) -> None:
    if not sections:
        return

    decoded = html.replace('\\"', '"').replace("\\n", "\n")
    if "## " not in decoded or "![" not in decoded:
        return

    current_section: Section | None = None
    current_subsection: Section | None = None
    section_cursor = -1
    subsection_cursor = -1

    lines = decoded.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("## "):
            title = _normalize_ws(stripped[3:])
            current_section, section_cursor = _match_section_by_title(
                sections,
                title,
                start_index=section_cursor + 1,
            )
            current_subsection = None
            subsection_cursor = -1
            continue

        if stripped.startswith("### "):
            if current_section is None:
                continue

            title = _normalize_ws(stripped[4:])
            current_subsection, subsection_cursor = _match_section_by_title(
                current_section.subsections,
                title,
                start_index=subsection_cursor + 1,
            )
            continue

        parsed_image = _parse_markdown_image(stripped)
        if parsed_image is None:
            continue

        target_section = current_subsection or current_section
        if target_section is None:
            continue

        alt_value, link_value = parsed_image
        raw_url = _extract_markdown_image_url(link_value)
        if not raw_url:
            continue

        image_url = _normalize_image_url(raw_url, base_url)
        alt_text = _normalize_ws(alt_value) or None
        caption = _extract_markdown_caption(lines, start_index=index + 1)

        _append_section_media(
            target_section,
            _FigureData(
                image_url=image_url,
                caption=caption,
                alt_text=alt_text,
            ),
        )


def _match_section_by_title(
    sections: list[Section],
    title: str,
    *,
    start_index: int,
) -> tuple[Section | None, int]:
    normalized_title = _normalize_ws(title).lower()
    if not normalized_title:
        return None, start_index - 1

    for index in range(max(start_index, 0), len(sections)):
        if _normalize_ws(sections[index].title).lower() == normalized_title:
            return sections[index], index

    for index, section in enumerate(sections):
        if _normalize_ws(section.title).lower() == normalized_title:
            return section, index

    return None, start_index - 1


def _parse_markdown_image(line: str) -> tuple[str, str] | None:
    start = line.find("![")
    while start != -1:
        alt_start = start + 2
        alt_end = line.find("]", alt_start)
        if alt_end == -1:
            return None

        if alt_end + 1 >= len(line) or line[alt_end + 1] != "(":
            start = line.find("![", alt_end + 1)
            continue

        link_start = alt_end + 2
        depth = 1
        cursor = link_start
        while cursor < len(line):
            char = line[cursor]
            prev = line[cursor - 1] if cursor > link_start else ""
            if char == "(" and prev != "\\":
                depth += 1
            elif char == ")" and prev != "\\":
                depth -= 1
                if depth == 0:
                    alt = line[alt_start:alt_end]
                    link = line[link_start:cursor]
                    return alt, link
            cursor += 1

        return None

    return None


def _extract_markdown_image_url(link_value: str) -> str | None:
    value = _normalize_ws(link_value)
    if not value:
        return None

    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]

    first_token = value.split(" ", maxsplit=1)[0]
    return first_token or None


def _extract_markdown_caption(lines: list[str], *, start_index: int) -> str | None:
    for line in lines[start_index : start_index + 4]:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("##") or stripped.startswith("!["):
            return None

        if stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2:
            caption = _normalize_ws(stripped[1:-1])
            return caption or None

        return None

    return None


def _append_section_media(section: Section, figure: _FigureData) -> None:
    if any(existing.image_url == figure.image_url for existing in section.media):
        return

    section.media.append(
        SectionMedia(
            index=len(section.media) + 1,
            image_url=figure.image_url,
            caption=figure.caption,
            alt_text=figure.alt_text,
        )
    )


def _extract_references_from_list(node: _Node, *, start_index: int) -> list[Reference]:
    references: list[Reference] = []
    items = [
        child
        for child in node.children
        if isinstance(child, _Node) and child.tag == "li"
    ]
    if not items:
        items = [child for child in _iter_nodes(node) if child.tag == "li"]

    for offset, item in enumerate(items):
        text = _normalize_ws(_render_inline(item))
        if not text:
            continue

        href = _first_link(item)
        references.append(
            Reference(index=start_index + offset, text=text, url=href),
        )

    return references


def _first_link(node: _Node) -> str | None:
    for child in _iter_nodes(node):
        if child.tag == "a":
            href = child.attrs.get("href", "").strip()
            if href:
                return href

    return None


def _is_references_heading(node: _Node) -> bool:
    if node.tag not in {"h2", "h3"}:
        return False
    return _normalize_ws(_render_inline(node)).lower() == "references"
