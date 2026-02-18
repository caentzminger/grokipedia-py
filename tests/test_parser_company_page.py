from __future__ import annotations

from pathlib import Path

from grokipedia import from_html


def test_parse_company_page_fixture() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "company_page_13065923.html"
    html = fixture_path.read_text(encoding="utf-8")

    page = from_html(html, source_url="https://grokipedia.com/page/13065923")

    assert page.title == "13065923"
    assert page.slug == "13065923"
    assert page.intro_text is not None
    assert "Harris Professional Solutions Limited" in page.intro_text

    section_titles = [section.title for section in page.sections]
    assert section_titles == ["Overview", "History", "References"]

    assert page.sections[0].subsections
    assert page.sections[0].subsections[0].title == "Company Profile"

    assert page.metadata.fact_check_label == "Fact-checked by Grok last month"
    assert page.metadata.canonical_url == "https://grokipedia.com/page/13065923"
    assert page.metadata.description == "Harris Professional Solutions Limited overview"

    assert len(page.references) == 2
    assert page.references[0].index == 1
    assert (
        page.references[0].url
        == "https://find-and-update.company-information.service.gov.uk/company/13065923"
    )
