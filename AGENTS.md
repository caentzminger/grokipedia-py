# Repository Guidelines

## Project Structure & Module Organization

- Core package code lives in `src/grokipedia/`.
- Main modules are split by concern: `client.py` (public entry points), `fetch.py`/`robots.py` (network and robots handling), `sitemaps.py` (cached sitemap index/lookup), `parser.py` (HTML parsing), `models.py` (typed data models), `_urls.py` (URL/user-agent helpers), `_types.py` (typing protocols), and `errors.py` (exception hierarchy).
- Tests are in `tests/`, with reusable HTML fixtures in `tests/fixtures/`.
- Project metadata and tooling config live in `pyproject.toml`; task shortcuts live in `Justfile`.

## Build, Test, and Development Commands

- `just setup`: install and lock all dev dependencies via `uv`.
- `just test`: run the full test suite with `pytest`.
- `just lint-py`: run `ruff check` across `src/` and `tests/`.
- `just lint-fix-py`: auto-fix lint issues when possible.
- `just fmt-py`: format Python code with `ruff format`.
- `just typecheck`: run static checks with `ty`.
- `just fmt-all`: run Python and Markdown formatting.

## Coding Style & Naming Conventions

- Target Python `>=3.10`; keep code compatible with stdlib-first design.
- Use 4-space indentation and type annotations for public APIs.
- Follow existing naming patterns: `snake_case` for functions/modules, `PascalCase` for data models/classes, `UPPER_SNAKE_CASE` for constants.
- Keep parsing logic deterministic and side-effect light; prefer small pure helpers.
- Run `just fmt-py just lint-py just typecheck` before opening a PR.

## Testing Guidelines

- Framework: `pytest`.
- Place tests in `tests/` with names like `test_<feature>.py` and functions `test_<behavior>()`.
- Prefer fixture-driven parser tests using `tests/fixtures/*.html` for stable coverage.
- Add or update tests for every bug fix and any new parsed field/behavior.

## Commit & Pull Request Guidelines

- Commit style in history is mostly Conventional Commits (`feat:`, `fix:`, `refactor:`); continue using that format.
- Keep commits focused and descriptive (one logical change per commit).
- PRs should include:
  - a short summary of behavior changes,
  - linked issue/context when applicable,
  - test evidence (e.g., `just test` output),
  - notes on parser edge cases or robots-related impacts.
