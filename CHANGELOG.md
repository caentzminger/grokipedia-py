# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Typed edit-history fetching via `edit_history()` and `Grokipedia.edit_history()`.
- `history.py` for parsing Grokipedia edit-history API responses.
- CLI support for `edit-history`, including `--json`, `--all`, and `--debug`.
- `Justfile` recipes for running tests and type checks across the supported Python version matrix.

### Changed

- Local type-checking now matches the CI Python matrix more closely.
- README and repository guidance now document edit-history usage, matrix checks, and debug logging.

### Removed

- `Page.lede_text` alias for `intro_text`.
- `Page.lead_media` alias for `lead_figure`.
- `SITEMAP_INDEX` alias in the package exports.

## [0.3.0] - 2026-03-07

### Added

- Docker support with multi-stage builds for minimal production images.
- GitHub Actions workflow for automated Docker image builds and pushes to GitHub Container Registry.
- Multi-platform Docker images supporting linux/amd64 and linux/arm64.
- Docker image attestations for build provenance verification.

### Changed

- Docker workflow includes test execution before image builds to ensure quality.
- README now includes Docker usage examples and installation instructions.

## [0.2.0] - 2026-03-07

### Added

- Zero-dependency CLI entrypoints for `grokipedia-py`, `grokipedia`, and `python -m grokipedia`.
- CLI support for text, JSON, and Markdown page output.
- Global CLI `--timeout` and `--user-agent` options.
- GitHub Actions publishing workflow for PyPI using `uv build`, smoke tests, and trusted publishing.

### Changed

- README CLI and publishing guidance now reflects the `uvx grokipedia-py` release flow.
- CLI tests now cover entrypoints, exit codes, packaging metadata, and output-mode behavior.

## [0.1.1] - 2026-02-18

### Added

- Shared internal helpers in `_urls.py` and `_types.py` for URL/user-agent resolution and internal fetch typing.
- Regression tests for sitemap lookup caching/failure paths, parser payload edge cases, markdown output stability, and client default/robots behaviors.

### Changed

- `Grokipedia` call-option resolution now uses a small dataclass for clearer internal option passing.
- `SitemapManifest` now maintains canonical URL indexes for faster repeated lookups while preserving lazy child sitemap loading.
- Parser markdown-media fallback now reads targeted `self.__next_f.push(...)` script payloads instead of scanning the full raw HTML string.
- `Page.markdown` assembly now uses shared helper functions to reduce duplicated rendering logic.
- Public API docstrings in `client.py` were expanded for clearer behavior/exception semantics.
- README install examples, quickstart safety, data-model notes, and development/CI guidance were improved for accuracy.
- Repo hygiene/docs metadata were tightened (`.gitignore` cache entries and `Documentation` project URL).

### Fixed

- CI dependency install command now uses valid locked `uv sync` flag syntax.

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
