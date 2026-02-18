# grokipedia-py

Near-zero dependency Python client for extracting structured content from Grokipedia pages.

## Install

```bash
pip install grokipedia-py
```

## Quickstart

```python
from grokipedia import from_url

page = from_url("https://grokipedia.com/page/13065923")

print(page.title)
print(page.slug)
print(page.intro_text)
print(page.infobox[:3])
print(page.lead_figure)
print([section.title for section in page.sections])
first_media = next(
    (
        subsection.media
        for section in page.sections
        for subsection in section.subsections
        if subsection.media
    ),
    [],
)
print(first_media[:1])
print(len(page.references))
print(page.links[:5])
print(page.metadata.keywords)
print(page.markdown[:500])
print(page.to_json(indent=2))
```

Parse raw HTML without network access:

```python
from grokipedia import from_html

page = from_html(html, source_url="https://grokipedia.com/page/13065923")
```

Resolve a page from a title:

```python
from grokipedia import page

page_obj = page('"Hello, World!" program')
```

Search for page URLs:

```python
from grokipedia import search

results = search("hello world")
print(results[:5])
```

If this returns `[]`, try:

```python
results = search("hello world", respect_robots=False)
```

As of February 18, 2026, `https://grokipedia.com/robots.txt` disallows `/api/`, and `/search` is mostly client-rendered HTML.

Use class-based API with sitemap manifest caching:

```python
from grokipedia import Grokipedia

wiki = Grokipedia(verbose=True)
result = wiki.page("The C Programming Language")
matches = wiki.search("programming language")

# Lazy sitemap lookup + cached child sitemap manifests.
url = wiki.find_page_url('"Hello, World!" program')
manifest = wiki.refresh_manifest()
```

## Logging

The library uses Python's standard `logging` module (logger namespace: `grokipedia`).

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("grokipedia").setLevel(logging.DEBUG)
```

## Development & CI

This project stays runtime dependency-free (`dependencies = []`) and relies on
the standard library for runtime behavior.

```bash
just setup
just fmt-py
just lint-py
just typecheck
just test
just ci
```

## Robots behavior

`from_url()` enforces `robots.txt` by default.

- `respect_robots=True` (default): validate `robots.txt` before page fetch.
- `search()` first tries `/api/full-text-search` and falls back to `/search` HTML parsing.
- `allow_robots_override=False` (default): strict mode.
- if `robots.txt` is unavailable or malformed, the library fails closed with `RobotsUnavailableError`.
- if URL is disallowed, it raises `RobotsDisallowedError`.

You can bypass robots enforcement by setting either:

- `respect_robots=False`, or
- `allow_robots_override=True`

## Data model

`from_url()` and `from_html()` return `Page` with:

- `url`
- `slug`
- `title`
- `intro_text`
- `infobox` (`InfoboxField` list for `dt`/`dd` fact rows)
- `lead_figure` (`LeadFigure` from the top figure image/caption when present)
- `sections` (`Section` tree with nested `subsections`; each section includes indexed `media`)
- `references` (`Reference` list)
- `links` (ordered unique links extracted from the main article)
- `metadata` (`PageMetadata`, including optional `keywords`)

`Page` also includes `markdown`, `to_dict()`, and `to_json()` for simple serialization.

## Exceptions

All library exceptions inherit from `GrokipediaError`.

- `FetchError`
- `HttpStatusError`
- `PageNotFoundError`
- `RobotsUnavailableError`
- `RobotsDisallowedError`
- `ParseError`
