from __future__ import annotations

from importlib.metadata import entry_points
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

from grokipedia.cli import main
from grokipedia.errors import PageNotFoundError
from grokipedia.models import EditHistoryEntry, EditHistoryPage, Page, PageMetadata


def _sample_page() -> Page:
    return Page(
        url="https://grokipedia.com/page/Sample_Page",
        slug="Sample_Page",
        title="Sample Page",
        intro_text="Sample intro text.",
        infobox=[],
        lead_figure=None,
        sections=[],
        references=[],
        links=[],
        metadata=PageMetadata(
            status_code=200,
            fetched_at_utc=datetime(2026, 2, 18, tzinfo=timezone.utc),
            canonical_url="https://grokipedia.com/page/Sample_Page",
            description="Sample description",
            keywords=["sample"],
        ),
    )


def _sample_edit_history() -> EditHistoryPage:
    return EditHistoryPage(
        edit_requests=[_sample_edit_history_entry()],
        total_count=1,
        has_more=False,
    )


def _sample_edit_history_entry(
    *,
    id: str = "edit-1",
    slug: str = "Sample_Page",
    user_id: str = "user-1",
    status: str = "EDIT_REQUEST_STATUS_APPROVED",
    type: str = "EDIT_REQUEST_TYPE_FIX_TYPO",
    summary: str = "Fix typo in lead",
    original_content: str | None = None,
    proposed_content: str | None = "the",
    section_title: str | None = "Overview",
    created_at_utc: datetime = datetime(2026, 2, 18, 15, 30, tzinfo=timezone.utc),
    updated_at_utc: datetime = datetime(2026, 2, 18, 15, 35, tzinfo=timezone.utc),
    upvote_count: int = 3,
    downvote_count: int = 1,
    review_reason: str | None = None,
) -> EditHistoryEntry:
    return EditHistoryEntry(
        id=id,
        slug=slug,
        user_id=user_id,
        status=status,
        type=type,
        summary=summary,
        original_content=original_content,
        proposed_content=proposed_content,
        section_title=section_title,
        created_at_utc=created_at_utc,
        updated_at_utc=updated_at_utc,
        upvote_count=upvote_count,
        downvote_count=downvote_count,
        review_reason=review_reason,
    )


def test_help_works(capsys) -> None:
    exit_code = main(["--help"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage: grokipedia" in captured.out
    assert "--debug" in captured.out
    assert "search" in captured.out
    assert "edit-history" in captured.out
    assert "page" in captured.out
    assert "from-url" in captured.out


def test_search_command_prints_results_and_applies_limit(
    monkeypatch,
    capsys,
) -> None:
    def fake_search(
        query: str,
        *,
        respect_robots: bool = True,
        timeout: float = 10.0,
        user_agent: str | None = None,
    ) -> list[str]:
        assert query == "hello world"
        assert respect_robots is False
        assert timeout == 2.5
        assert user_agent == "grokipedia-py-test"
        return [
            "https://grokipedia.com/page/One",
            "https://grokipedia.com/page/Two",
        ]

    monkeypatch.setattr("grokipedia.cli.search", fake_search)

    exit_code = main(
        [
            "search",
            "hello world",
            "--limit",
            "1",
            "--no-respect-robots",
            "--timeout",
            "2.5",
            "--user-agent",
            "grokipedia-py-test",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "https://grokipedia.com/page/One\n"
    assert captured.err == ""


def test_search_command_supports_limit_zero(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "grokipedia.cli.search",
        lambda *args, **kwargs: ["https://grokipedia.com/page/One"],
    )

    exit_code = main(["search", "hello world", "--limit", "0"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_search_command_with_no_results_prints_nothing(monkeypatch, capsys) -> None:
    monkeypatch.setattr("grokipedia.cli.search", lambda *args, **kwargs: [])

    exit_code = main(["search", "hello world"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""


def test_debug_flag_enables_logging_configuration(monkeypatch, capsys) -> None:
    called: list[bool] = []

    monkeypatch.setattr(
        "grokipedia.cli._configure_verbose_logging",
        lambda *, enabled: called.append(enabled),
    )
    monkeypatch.setattr("grokipedia.cli.search", lambda *args, **kwargs: [])

    exit_code = main(["search", "hello world", "--debug"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert called == [True]
    assert captured.out == ""
    assert captured.err == ""


def test_page_command_supports_json(monkeypatch, capsys) -> None:
    def fake_page(
        title: str,
        *,
        timeout: float = 10.0,
        user_agent: str | None = None,
    ) -> Page:
        assert title == "Sample Page"
        assert timeout == 1.25
        assert user_agent == "grokipedia-py-test"
        return _sample_page()

    monkeypatch.setattr("grokipedia.cli.page", fake_page)

    exit_code = main(
        [
            "page",
            "Sample Page",
            "--json",
            "--timeout",
            "1.25",
            "--user-agent",
            "grokipedia-py-test",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"title": "Sample Page"' in captured.out
    assert captured.err == ""


def test_page_command_supports_markdown(monkeypatch, capsys) -> None:
    monkeypatch.setattr("grokipedia.cli.page", lambda *args, **kwargs: _sample_page())

    exit_code = main(["page", "Sample Page", "--markdown"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "# Sample Page\n\nSample intro text.\n"
    assert captured.err == ""


def test_edit_history_command_prints_human_readable_output(monkeypatch, capsys) -> None:
    def fake_edit_history(
        title: str,
        *,
        limit: int = 25,
        offset: int = 0,
        respect_robots: bool = True,
        timeout: float = 10.0,
        user_agent: str | None = None,
    ) -> EditHistoryPage:
        assert title == "Sample Page"
        assert limit == 5
        assert offset == 10
        assert respect_robots is False
        assert timeout == 1.5
        assert user_agent == "grokipedia-py-test"
        return _sample_edit_history()

    monkeypatch.setattr("grokipedia.cli.edit_history", fake_edit_history)

    exit_code = main(
        [
            "edit-history",
            "Sample Page",
            "--limit",
            "5",
            "--offset",
            "10",
            "--no-respect-robots",
            "--timeout",
            "1.5",
            "--user-agent",
            "grokipedia-py-test",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        "EDIT_REQUEST_STATUS_APPROVED\n"
        "EDIT_REQUEST_TYPE_FIX_TYPO\n"
        "2026-02-18T15:30:00Z\n"
        "Overview\n"
        "Fix typo in lead\n"
    )
    assert captured.err == ""


def test_edit_history_command_supports_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "grokipedia.cli.edit_history",
        lambda *args, **kwargs: _sample_edit_history(),
    )

    exit_code = main(["edit-history", "Sample Page", "--json"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"total_count": 1' in captured.out
    assert '"section_title": "Overview"' in captured.out
    assert captured.err == ""


def test_edit_history_command_all_fetches_all_pages(monkeypatch, capsys) -> None:
    calls: list[tuple[int, int]] = []

    def fake_edit_history(
        title: str,
        *,
        limit: int = 25,
        offset: int = 0,
        respect_robots: bool = True,
        timeout: float = 10.0,
        user_agent: str | None = None,
    ) -> EditHistoryPage:
        calls.append((limit, offset))
        assert title == "Sample Page"
        assert respect_robots is True
        assert timeout == 10.0
        assert user_agent is None

        if offset == 2:
            return EditHistoryPage(
                edit_requests=[
                    _sample_edit_history_entry(
                        id="edit-3",
                        user_id="user-3",
                        status="EDIT_REQUEST_STATUS_IMPLEMENTED",
                        type="EDIT_REQUEST_TYPE_ADD_INFORMATION",
                        summary="Add another fact",
                        proposed_content=None,
                        section_title="History",
                        created_at_utc=datetime(
                            2026, 2, 20, 12, 0, tzinfo=timezone.utc
                        ),
                        updated_at_utc=datetime(
                            2026, 2, 20, 12, 5, tzinfo=timezone.utc
                        ),
                        upvote_count=0,
                        downvote_count=0,
                    )
                ],
                total_count=3,
                has_more=False,
            )

        return EditHistoryPage(
            edit_requests=[
                _sample_edit_history_entry(),
                _sample_edit_history_entry(
                    id="edit-2",
                    user_id="user-2",
                    status="EDIT_REQUEST_STATUS_IN_REVIEW",
                    type="EDIT_REQUEST_TYPE_UPDATE_INFORMATION",
                    summary="Clarify background",
                    proposed_content=None,
                    section_title=None,
                    created_at_utc=datetime(2026, 2, 19, 12, 0, tzinfo=timezone.utc),
                    updated_at_utc=datetime(2026, 2, 19, 12, 5, tzinfo=timezone.utc),
                    upvote_count=1,
                    downvote_count=0,
                ),
            ],
            total_count=3,
            has_more=True,
        )

    monkeypatch.setattr("grokipedia.cli.edit_history", fake_edit_history)

    exit_code = main(["edit-history", "Sample Page", "--all", "--limit", "2"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert calls == [(2, 0), (2, 2)]
    assert "Fix typo in lead" in captured.out
    assert "Clarify background" in captured.out
    assert "Add another fact" in captured.out
    assert captured.err == ""


def test_edit_history_command_all_supports_json(monkeypatch, capsys) -> None:
    def fake_edit_history(*args, **kwargs) -> EditHistoryPage:
        offset = kwargs["offset"]
        if offset == 1:
            return EditHistoryPage(
                edit_requests=[],
                total_count=1,
                has_more=False,
            )
        return EditHistoryPage(
            edit_requests=[_sample_edit_history().edit_requests[0]],
            total_count=1,
            has_more=True,
        )

    monkeypatch.setattr("grokipedia.cli.edit_history", fake_edit_history)

    exit_code = main(["edit-history", "Sample Page", "--all", "--json", "--limit", "1"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"total_count": 1' in captured.out
    assert captured.err == ""


def test_edit_history_command_all_requires_positive_limit(capsys) -> None:
    exit_code = main(["edit-history", "Sample Page", "--all", "--limit", "0"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "--limit must be >= 1 when using --all" in captured.err


def test_from_url_command_prints_human_readable_output(monkeypatch, capsys) -> None:
    def fake_from_url(
        url: str,
        *,
        respect_robots: bool = True,
        timeout: float = 10.0,
        user_agent: str | None = None,
    ) -> Page:
        assert url == "https://grokipedia.com/page/Sample_Page"
        assert respect_robots is False
        assert timeout == 3.0
        assert user_agent == "grokipedia-py-test"
        return _sample_page()

    monkeypatch.setattr("grokipedia.cli.from_url", fake_from_url)

    exit_code = main(
        [
            "from-url",
            "https://grokipedia.com/page/Sample_Page",
            "--no-respect-robots",
            "--timeout",
            "3",
            "--user-agent",
            "grokipedia-py-test",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        "Sample Page\nhttps://grokipedia.com/page/Sample_Page\n\nSample intro text.\n"
    )
    assert captured.err == ""


def test_from_url_command_supports_markdown(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "grokipedia.cli.from_url",
        lambda *args, **kwargs: _sample_page(),
    )

    exit_code = main(
        ["from-url", "https://grokipedia.com/page/Sample_Page", "--markdown"]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "# Sample Page\n\nSample intro text.\n"
    assert captured.err == ""


def test_library_errors_return_exit_code_one(monkeypatch, capsys) -> None:
    def fake_page(
        title: str,
        *,
        timeout: float = 10.0,
        user_agent: str | None = None,
    ) -> Page:
        raise PageNotFoundError(f"https://grokipedia.com/page/{title}")

    monkeypatch.setattr("grokipedia.cli.page", fake_page)

    exit_code = main(["page", "Missing Page"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Page not found" in captured.err


def test_invalid_args_return_exit_code_two(capsys) -> None:
    exit_code = main(["search", "--limit", "-1", "hello world"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "error:" in captured.err


def test_page_rejects_json_and_markdown_together(capsys) -> None:
    exit_code = main(["page", "Sample Page", "--json", "--markdown"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "not allowed with argument" in captured.err


def test_keyboard_interrupt_returns_exit_code_130(monkeypatch, capsys) -> None:
    def fake_search(*args, **kwargs) -> list[str]:
        raise KeyboardInterrupt

    monkeypatch.setattr("grokipedia.cli.search", fake_search)

    exit_code = main(["search", "hello world"])

    captured = capsys.readouterr()

    assert exit_code == 130
    assert captured.out == ""
    assert captured.err == ""


def test_python_module_help_works() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    pythonpath = str(root / "src")
    if env.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath

    result = subprocess.run(
        [sys.executable, "-m", "grokipedia", "--help"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage: python -m grokipedia" in result.stdout


def test_console_scripts_include_grokipedia_and_grokipedia_py() -> None:
    scripts = entry_points(group="console_scripts")
    script_names = {entry.name for entry in scripts if entry.module == "grokipedia.cli"}

    assert "grokipedia" in script_names
    assert "grokipedia-py" in script_names


def test_pyproject_declares_dual_console_scripts() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject_text = (root / "pyproject.toml").read_text()

    assert 'name = "grokipedia-py"' in pyproject_text
    assert 'grokipedia = "grokipedia.cli:main"' in pyproject_text
    assert 'grokipedia-py = "grokipedia.cli:main"' in pyproject_text
