from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import subprocess
import sys

import grokipedia
from grokipedia.cli import main
from grokipedia.models import Page, PageMetadata


def _sample_page() -> Page:
    return Page(
        url="https://grokipedia.com/page/Smoke_Test",
        slug="Smoke_Test",
        title="Smoke Test",
        intro_text="Smoke intro.",
        infobox=[],
        lead_figure=None,
        sections=[],
        references=[],
        links=[],
        metadata=PageMetadata(
            status_code=200,
            fetched_at_utc=datetime(2026, 3, 7, tzinfo=timezone.utc),
            canonical_url="https://grokipedia.com/page/Smoke_Test",
            description="Smoke test page",
            keywords=["smoke"],
        ),
    )


def main_smoke() -> int:
    assert grokipedia.__all__
    with redirect_stdout(io.StringIO()):
        assert main(["--help"]) == 0

    page = _sample_page()
    assert page.to_json()
    assert page.markdown == "# Smoke Test\n\nSmoke intro."

    result = subprocess.run(
        [sys.executable, "-m", "grokipedia", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout
    return 0


raise SystemExit(main_smoke())
