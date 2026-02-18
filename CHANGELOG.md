# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-18

### Added

- Initial public release of `grokipedia-py`.
- Dependency-free runtime client for Grokipedia page retrieval and parsing.
- Public APIs:
  - `from_url()` and `from_html()` for parsing pages.
  - `page()` for title-to-page resolution.
  - `search()` with API-first + HTML fallback behavior.
  - `Grokipedia` class for reusable fetch/search/page operations.
- Robots-aware fetching with strict defaults and override controls.
- Structured typed models for pages, sections, references, infobox fields, metadata, and media.
- Markdown and JSON serialization helpers on `Page`.
- Sitemap-manifest utilities for cached title URL lookup.
- Test coverage for parser behavior, robots handling, fetchers, search/page APIs, and class workflows.
