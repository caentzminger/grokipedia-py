from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from typing import Iterable
from urllib.parse import unquote, urlparse

from .errors import ParseError
from .models import Page, PageMetadata, Reference, Section

_FACT_CHECK_PATTERN = re.compile(
    r"Fact-checked by Grok(?:\s*<!--.*?-->\s*)*\s*([^<\n]{0,120})",
    flags=re.IGNORECASE | re.DOTALL,
)

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
class _Block:
    kind: str
    markdown: str
    node: _Node | None
    heading_level: int | None = None
    heading_id: str | None = None
    heading_title: str | None = None


def parse_page_html(
    html: str,
    *,
    source_url: str | None,
    status_code: int,
    fetched_at_utc: datetime | None = None,
) -> Page:
    builder = _DOMBuilder()
    try:
        builder.feed(html)
    except Exception as exc:
        raise ParseError(f"Unable to parse HTML: {exc}") from exc

    root = builder.root
    article = _select_article(root)
    if article is None:
        raise ParseError("Could not identify main content article")

    blocks = _extract_blocks(article)
    title = _extract_title(blocks)
    if not title:
        title = _extract_meta_title(root)
    if not title:
        raise ParseError("Could not extract page title")

    lede_markdown = _extract_lede(blocks)
    sections, references = _build_sections_and_references(blocks)

    canonical_url = _extract_canonical_url(root)
    page_url = source_url or canonical_url or ""

    metadata = PageMetadata(
        status_code=status_code,
        fetched_at_utc=fetched_at_utc or datetime.now(timezone.utc),
        fact_check_label=_extract_fact_check_label(html),
        canonical_url=canonical_url,
        description=_extract_description(root),
    )

    return Page(
        url=page_url,
        slug=_extract_slug(page_url),
        title=title,
        lede_markdown=lede_markdown,
        sections=sections,
        references=references,
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


def _extract_fact_check_label(html: str) -> str | None:
    match = _FACT_CHECK_PATTERN.search(html)
    if not match:
        return None
    suffix = _normalize_ws(match.group(1))
    if not suffix:
        return "Fact-checked by Grok"
    return f"Fact-checked by Grok {suffix}"


def _extract_slug(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    path = parsed.path
    if path.startswith("/page/"):
        slug = path[len("/page/") :]
        return unquote(slug)
    return unquote(path.strip("/"))


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
            node
            for node in _iter_nodes(article)
            if node.tag in {"h1", "h2", "h3"}
        ]
        has_h1 = any(node.tag == "h1" for node in headings)
        has_references = any(_is_references_heading(node) for node in headings)
        if has_h1 and has_references:
            return article

    return articles[0]


def _extract_blocks(article: _Node) -> list[_Block]:
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
                        markdown="",
                        node=node,
                        heading_level=int(node.tag[-1]),
                        heading_id=node.attrs.get("id") or None,
                        heading_title=title,
                    )
                )
            return

        if node.tag == "p":
            markdown = _normalize_ws(_render_inline(node))
            if markdown:
                blocks.append(_Block(kind="paragraph", markdown=markdown, node=node))
            return

        if node.tag in {"ul", "ol"}:
            markdown = _render_list(node)
            if markdown:
                blocks.append(_Block(kind="list", markdown=markdown, node=node))
            return

        if node.tag == "pre":
            markdown = _render_pre(node)
            if markdown:
                blocks.append(_Block(kind="code", markdown=markdown, node=node))
            return

        if node.tag == "blockquote":
            quote = _normalize_ws(_render_inline(node))
            if quote:
                blocks.append(_Block(kind="blockquote", markdown=f"> {quote}", node=node))
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

    children = "".join(_render_inline(child, in_code=in_code) for child in node.children)

    if tag == "a":
        text = _normalize_ws(children)
        href = node.attrs.get("href", "").strip()
        if href and text:
            return f"[{text}]({href})"
        return text or href

    if tag in {"strong", "b"}:
        text = _normalize_ws(children)
        return f"**{text}**" if text else ""

    if tag in {"em", "i"}:
        text = _normalize_ws(children)
        return f"*{text}*" if text else ""

    if tag == "code" and not in_code:
        text = _normalize_ws(children)
        if not text:
            return ""
        escaped = text.replace("`", "\\`")
        return f"`{escaped}`"

    return children


def _render_list(node: _Node) -> str:
    ordered = node.tag == "ol"
    items = [child for child in node.children if isinstance(child, _Node) and child.tag == "li"]
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
    language = ""
    code_node: _Node | None = None
    for child in node.children:
        if isinstance(child, _Node) and child.tag == "code":
            code_node = child
            break

    if code_node is not None:
        classes = code_node.attrs.get("class", "")
        for value in classes.split():
            if value.startswith("language-"):
                language = value.replace("language-", "", 1)
                break
        code = _text_content(code_node, preserve_whitespace=True)
    else:
        code = _text_content(node, preserve_whitespace=True)

    code = code.strip("\n")
    if not code:
        return ""

    if language:
        return f"```{language}\n{code}\n```"
    return f"```\n{code}\n```"


def _extract_title(blocks: list[_Block]) -> str | None:
    for block in blocks:
        if block.kind == "heading" and block.heading_level == 1 and block.heading_title:
            return block.heading_title
    return None


def _extract_lede(blocks: list[_Block]) -> str | None:
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
            return block.markdown

    return None


def _append_markdown(current: str, addition: str) -> str:
    if not addition:
        return current
    if not current:
        return addition
    return f"{current}\n\n{addition}"


def _build_sections_and_references(blocks: list[_Block]) -> tuple[list[Section], list[Reference]]:
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
                    markdown="",
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
                        markdown="",
                        subsections=[],
                    )
                    sections.append(current_section)

                current_subsection = Section(
                    id=block.heading_id,
                    title=heading_title,
                    level=3,
                    markdown="",
                    subsections=[],
                )
                current_section.subsections.append(current_subsection)
                in_references = _normalize_ws(heading_title).lower() == "references"
                continue

        target_section = current_subsection or current_section
        if target_section is None:
            continue

        target_section.markdown = _append_markdown(target_section.markdown, block.markdown)

        if in_references and block.kind == "list" and block.node is not None:
            start_index = len(references) + 1
            references.extend(_extract_references_from_list(block.node, start_index=start_index))

    return sections, references


def _extract_references_from_list(node: _Node, *, start_index: int) -> list[Reference]:
    references: list[Reference] = []
    items = [child for child in node.children if isinstance(child, _Node) and child.tag == "li"]
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
