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
print(page.sections[0].subsections[0].media[:1])
print(len(page.references))
print(page.metadata.keywords)
print(page.to_json(indent=2))
```

Parse raw HTML without network access:

```python
from grokipedia import from_html

page = from_html(html, source_url="https://grokipedia.com/page/13065923")
```

## Logging

The library uses Python's standard `logging` module (logger namespace: `grokipedia`).

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("grokipedia").setLevel(logging.DEBUG)
```

## Robots behavior

`from_url()` enforces `robots.txt` by default.

- `respect_robots=True` (default): validate `robots.txt` before page fetch.
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
- `metadata` (`PageMetadata`, including optional `keywords`)

`Page` also includes `to_dict()` and `to_json()` for simple serialization.

## Exceptions

All library exceptions inherit from `GrokipediaError`.

- `FetchError`
- `HttpStatusError`
- `PageNotFoundError`
- `RobotsUnavailableError`
- `RobotsDisallowedError`
- `ParseError`
