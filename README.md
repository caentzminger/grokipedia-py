# grokipedia-py

Zero-dependency Python client for extracting structured content from Grokipedia pages.

## Install

```bash
pip install grokipedia-py
```

```bash
uv pip install https://github.com/caentzminger/grokipedia-py.git
uv add "grokipedia-py @ git+https://github.com/caentzminger/grokipedia-py.git"
uv tool install grokipedia-py
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

Fetch edit history for a page:

```python
from grokipedia import edit_history

history = edit_history(
    '"Hello, World!" program',
    respect_robots=False,
    limit=10,
)

print(history.total_count)
print(history.has_more)
print(history.edit_requests[0].status)
print(history.edit_requests[0].summary)
```

## CLI

The package also includes a CLI:

Install it as a tool using `uv`:

```bash
uv tool install -U grokipedia-py
```

Or give it a try using:

```bash
uvx grokipedia-py --help
```

More examples:

```bash
uvx grokipedia-py --timeout 5 --user-agent "grokipedia-py/cli" search "hello world"
grokipedia-py search "hello world" --limit 5 --no-respect-robots
grokipedia-py page '"Hello, World!" program'
grokipedia-py page '"Hello, World!" program' --markdown
grokipedia-py today --json
grokipedia-py edit-history '"Hello, World!" program' --no-respect-robots
grokipedia-py edit-history '"Hello, World!" program' --all --json --no-respect-robots
grokipedia-py edit-history '"Hello, World!" program' --debug --no-respect-robots
grokipedia-py from-url "https://grokipedia.com/page/13065923" --json
grokipedia-py from-url "https://grokipedia.com/page/13065923" --markdown
```

Published package usage:

```bash
uvx grokipedia-py --help
uvx grokipedia-py search "hello world" --limit 5 --no-respect-robots
```

Installed convenience commands:

```bash
uv run grokipedia --help
uv run gf --help
python -m grokipedia --help
```

The published package name is `grokipedia-py`. It also installs `grokipedia`
and `gf` commands for local convenience, but the supported published `uvx`
invocation is `uvx grokipedia-py`.

## Docker

The package is also available as a Docker image from GitHub Container Registry:

```bash
docker pull ghcr.io/caentzminger/grokipedia-py:latest
docker run --rm ghcr.io/caentzminger/grokipedia-py:latest --help
```

Examples:

```bash
docker run --rm ghcr.io/caentzminger/grokipedia-py:latest search "hello world" --limit 5
docker run --rm ghcr.io/caentzminger/grokipedia-py:latest page '"Hello, World!" program'
docker run --rm ghcr.io/caentzminger/grokipedia-py:latest today
docker run --rm ghcr.io/caentzminger/grokipedia-py:latest from-url "https://grokipedia.com/page/13065923" --json
```

Available tags:

- `latest` - latest build from main branch
- `v0.2.0`, `v0.2`, `v0` - semantic version tags
- `sha-abc123` - short commit SHA

Multi-platform images are available for `linux/amd64` and `linux/arm64`.

`page` and `from-url` support three output modes:

- default text output: title, URL, and intro text when present
- `--json`: structured page JSON
- `--markdown`: `Page.markdown` output

`edit-history` supports:

- default text output: status, type, timestamp, optional section title, and summary
- `--json`: structured edit-history JSON
- `--all`: page through the full edit history using `--limit` as the batch size
- `--debug`: enable `grokipedia` debug logging

Use class-based API with sitemap manifest caching:

```python
from grokipedia import Grokipedia

wiki = Grokipedia(verbose=True)
result = wiki.page("The C Programming Language")
matches = wiki.search("programming language")
history = wiki.edit_history('"Hello, World!" program', respect_robots=False)

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
just typecheck-matrix
just test-matrix
just check-matrix
just ci
```

Matrix-friendly one-off commands are also available:

```bash
just typecheck-py 3.10
just test-py 3.11
just check-py 3.12
```

## Publishing

GitHub Actions publishing is configured for both PyPI and Docker:

### PyPI

[`publish.yml`](.github/workflows/publish.yml) uses `uv` and PyPI trusted publishing.

- Push a version tag like `v0.2.0` to trigger the publish workflow.
- The workflow builds the wheel and sdist with `uv build`.
- It smoke-tests both artifacts before publishing.
- The GitHub repository must be added as a trusted publisher for the
  `grokipedia-py` project on PyPI.

### Docker

[`docker.yml`](.github/workflows/docker.yml) builds and pushes Docker images to GitHub Container Registry.

- Triggered on pushes to main branch, version tags, or manually via workflow_dispatch.
- Builds multi-platform images (linux/amd64, linux/arm64).
- Includes build attestations for provenance verification.
- Runs tests before building to ensure image quality.

## Jujutsu

This repo is initialized for `jj` in colocated mode, so both `jj` and `git` work from the same
working tree.

- `jj status` shows the current working copy state.
- `jj bookmark list` lists the local bookmarks.
- `jj git fetch` updates the remote-tracking bookmarks from GitHub.
- `jj bookmark track main codex/edit-history-draft-pr --remote origin` keeps the tracked
  bookmarks aligned with `origin`.
- `jj new main` creates a new change based on `main`.

## Robots behavior

`from_url()` and `edit_history()` enforce `robots.txt` by default.

- `respect_robots=True` (default): validate `robots.txt` before page fetch.
- `search()` first tries `/api/full-text-search` and falls back to `/search` HTML parsing.
- `edit_history()` uses `/api/list-edit-requests-by-slug`, so it is blocked by the live `robots.txt` policy unless you opt out.
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

`Page` also includes:

- `markdown`
- `to_dict()` / `to_json()`
- `from_dict()` / `from_json()`

`edit_history()` returns `EditHistoryPage` with:

- `edit_requests` (`EditHistoryEntry` list)
- `total_count`
- `has_more`

Each `EditHistoryEntry` includes:

- `id`
- `slug`
- `user_id`
- `status`
- `type`
- `summary`
- `original_content`
- `proposed_content`
- `section_title`
- `created_at_utc`
- `updated_at_utc`
- `upvote_count`
- `downvote_count`
- `review_reason`

## Exceptions

All library exceptions inherit from `GrokipediaError`.

- `FetchError`
- `HttpStatusError`
- `PageNotFoundError`
- `RobotsUnavailableError`
- `RobotsDisallowedError`
- `ParseError`
