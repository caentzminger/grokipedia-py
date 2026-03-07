from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from .client import from_url, page, search
from .errors import GrokipediaError
from .models import Page


class _ParserExit(Exception):
    def __init__(self, status: int, message: str | None = None) -> None:
        self.status = status
        self.message = message
        super().__init__(message)


class _ArgumentParser(argparse.ArgumentParser):
    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        raise _ParserExit(status, message)

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _default_prog() -> str:
    program_name = Path(sys.argv[0]).name
    if program_name == "__main__.py":
        return "python -m grokipedia"
    if program_name:
        return program_name
    return "grokipedia"


def _add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Network timeout in seconds",
    )
    parser.add_argument(
        "--user-agent",
        help="Override the HTTP User-Agent header",
    )


def _build_parser(*, prog: str | None = None) -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog=_default_prog() if prog is None else prog,
    )
    _add_shared_arguments(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search for page URLs")
    _add_shared_arguments(search_parser)
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--limit",
        type=_non_negative_int,
        default=None,
        help="Maximum number of results to print",
    )
    search_parser.add_argument(
        "--no-respect-robots",
        action="store_true",
        help="Skip robots.txt validation",
    )

    page_parser = subparsers.add_parser("page", help="Fetch a page by title")
    _add_shared_arguments(page_parser)
    page_parser.add_argument("title", help="Page title")
    page_output_group = page_parser.add_mutually_exclusive_group()
    page_output_group.add_argument(
        "--json",
        action="store_true",
        help="Print the parsed page as JSON",
    )
    page_output_group.add_argument(
        "--markdown",
        action="store_true",
        help="Print the parsed page as Markdown",
    )

    from_url_parser = subparsers.add_parser(
        "from-url",
        help="Fetch and parse a page from a full URL",
    )
    _add_shared_arguments(from_url_parser)
    from_url_parser.add_argument("url", help="Full Grokipedia page URL")
    from_url_output_group = from_url_parser.add_mutually_exclusive_group()
    from_url_output_group.add_argument(
        "--json",
        action="store_true",
        help="Print the parsed page as JSON",
    )
    from_url_output_group.add_argument(
        "--markdown",
        action="store_true",
        help="Print the parsed page as Markdown",
    )
    from_url_parser.add_argument(
        "--no-respect-robots",
        action="store_true",
        help="Skip robots.txt validation",
    )

    return parser


def _print_page(page_obj: Page, *, as_json: bool, as_markdown: bool) -> None:
    if as_json:
        print(page_obj.to_json(indent=2))
        return
    if as_markdown:
        print(page_obj.markdown)
        return

    print(page_obj.title)
    print(page_obj.url)
    if page_obj.intro_text:
        print()
        print(page_obj.intro_text)


def _run_search(args: argparse.Namespace) -> None:
    results = search(
        args.query,
        respect_robots=not args.no_respect_robots,
        timeout=args.timeout,
        user_agent=args.user_agent,
    )
    if args.limit is not None:
        results = results[: args.limit]

    for result in results:
        print(result)


def _run_page(args: argparse.Namespace) -> None:
    page_obj = page(
        args.title,
        timeout=args.timeout,
        user_agent=args.user_agent,
    )
    _print_page(page_obj, as_json=args.json, as_markdown=args.markdown)


def _run_from_url(args: argparse.Namespace) -> None:
    page_obj = from_url(
        args.url,
        respect_robots=not args.no_respect_robots,
        timeout=args.timeout,
        user_agent=args.user_agent,
    )
    _print_page(page_obj, as_json=args.json, as_markdown=args.markdown)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser(prog="grokipedia" if argv is not None else None)

    try:
        args = parser.parse_args(list(argv) if argv is not None else None)

        if args.command == "search":
            _run_search(args)
        elif args.command == "page":
            _run_page(args)
        elif args.command == "from-url":
            _run_from_url(args)
        else:
            parser.error(f"unknown command: {args.command}")

        return 0
    except _ParserExit as exc:
        stream = sys.stderr if exc.status else sys.stdout
        if exc.message:
            print(exc.message, file=stream, end="")
        return exc.status
    except KeyboardInterrupt:
        return 130
    except (GrokipediaError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
