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
print(page.lede_text)
print([section.title for section in page.sections])
print(len(page.references))
```

Parse raw HTML without network access:

```python
from grokipedia import from_html

page = from_html(html, source_url="https://grokipedia.com/page/13065923")
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
- `lede_text`
- `sections` (`Section` tree with nested `subsections`)
- `references` (`Reference` list)
- `metadata` (`PageMetadata`)

## Exceptions

All library exceptions inherit from `GrokipediaError`.

- `FetchError`
- `HttpStatusError`
- `PageNotFoundError`
- `RobotsUnavailableError`
- `RobotsDisallowedError`
- `ParseError`
