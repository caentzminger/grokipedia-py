from __future__ import annotations

from pathlib import Path

from grokipedia import from_html


def test_parse_hello_world_fixture() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "hello_world_program.html"
    html = fixture_path.read_text(encoding="utf-8")

    page = from_html(
        html,
        source_url="https://grokipedia.com/page/%22Hello,_World!%22_program",
    )

    assert page.title == '"Hello, World!" program'
    assert page.slug == '"Hello,_World!"_program'

    assert page.sections
    overview = page.sections[0]
    assert overview.title == "Overview"
    assert overview.subsections

    subsection = overview.subsections[0]
    assert subsection.title == "In C"
    assert "```c" in subsection.markdown
    assert "Hello, World!" in subsection.markdown

    assert len(page.references) == 1
    assert (
        page.references[0].text
        == "[The C Programming Language](https://grokipedia.com/page/The_C_Programming_Language)"
    )
    assert (
        page.references[0].url
        == "https://grokipedia.com/page/The_C_Programming_Language"
    )
