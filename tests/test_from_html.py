from __future__ import annotations

import json

from grokipedia import from_html
from grokipedia.models import Page


def test_from_html_parses_without_network() -> None:
    html = """
    <html>
      <head>
        <meta property='og:url' content='https://grokipedia.com/page/sample' />
      </head>
      <body>
        <article class='text-[16px]'>
          <h1 id='sample'>Sample Page</h1>
          <p>This is a sample intro with <a href='/page/Example'>Example</a>.</p>
          <h2 id='overview'>Overview</h2>
          <p>This is body content.</p>
        </article>
      </body>
    </html>
    """

    page = from_html(html, source_url="https://grokipedia.com/page/sample")

    assert page.url == "https://grokipedia.com/page/sample"
    assert page.slug == "sample"
    assert page.title == "Sample Page"
    assert page.intro_text == "This is a sample intro with Example."
    assert page.infobox == []
    assert page.lead_figure is None
    assert page.metadata.keywords is None
    assert page.sections[0].title == "Overview"
    assert page.links == ["https://grokipedia.com/page/Example"]


def test_from_html_parses_span_tts_content_blocks() -> None:
    html = """
    <html>
      <body>
        <article class='text-[16px]'>
          <h1 id='acme'>Acme</h1>
          <span data-tts-block='true'>Acme is a company.</span>
          <h2 id='overview'>Overview</h2>
          <h3 id='details'>Details</h3>
          <span data-tts-block='true'>Acme builds rockets and tools.</span>
          <h2 id='references'>References</h2>
          <ol>
            <li><a href='https://example.com'>https://example.com</a></li>
          </ol>
        </article>
      </body>
    </html>
    """

    page = from_html(html, source_url="https://grokipedia.com/page/acme")

    assert page.intro_text == "Acme is a company."
    assert page.sections[0].title == "Overview"
    assert page.sections[0].subsections[0].title == "Details"
    assert page.sections[0].subsections[0].text == "Acme builds rockets and tools."
    assert page.links == ["https://example.com"]


def test_from_html_parses_infobox_lead_figure_and_keywords() -> None:
    html = """
    <html>
      <head>
        <meta name='keywords' content='Epstein, Jeff Epstein' />
      </head>
      <body>
        <article class='text-[16px]'>
          <h1 id='jeffrey-epstein'>Jeffrey Epstein</h1>
          <span data-tts-block='true'>Jeffrey Epstein was an American financier.</span>
          <figure>
            <img src='/_next/image?url=https%3A%2F%2Fassets.grokipedia.com%2Fwiki%2Fimages%2Fexample.jpg&w=1200&q=75' alt='Jeffrey Epstein' />
            <figcaption>Jeffrey Epstein</figcaption>
          </figure>
          <div>
            <dt>Birth Date</dt>
            <dd>January 20, 1953</dd>
            <dt>Birth Place</dt>
            <dd>Brooklyn, New York City, U.S.</dd>
          </div>
          <h2 id='overview'>Overview</h2>
          <span data-tts-block='true'>Overview body.</span>
        </article>
      </body>
    </html>
    """

    page = from_html(
        html,
        source_url="https://grokipedia.com/page/Jeffrey_Epstein",
    )

    assert page.intro_text == "Jeffrey Epstein was an American financier."

    assert len(page.infobox) == 2
    assert page.infobox[0].label == "Birth Date"
    assert page.infobox[0].value == "January 20, 1953"
    assert page.infobox[1].label == "Birth Place"
    assert page.infobox[1].value == "Brooklyn, New York City, U.S."

    assert page.lead_figure is not None
    assert (
        page.lead_figure.image_url
        == "https://assets.grokipedia.com/wiki/images/example.jpg"
    )
    assert page.lead_figure.caption == "Jeffrey Epstein"
    assert page.lead_figure.alt_text == "Jeffrey Epstein"

    assert page.metadata.keywords == ["Epstein", "Jeff Epstein"]
    assert page.links == []


def test_from_html_parses_inline_subsection_media_indexed() -> None:
    html = """
    <html>
      <body>
        <article class='text-[16px]'>
          <h1 id='sample'>Sample Page</h1>
          <span data-tts-block='true'>Sample intro.</span>
          <h2 id='overview'>Overview</h2>
          <h3 id='details'>Details</h3>
          <span data-tts-block='true'>Details text.</span>
          <figure>
            <img src='https://assets.grokipedia.com/wiki/images/details-1.jpg' alt='Detail 1' />
            <figcaption>Detail image one</figcaption>
          </figure>
          <figure>
            <img src='/_next/image?url=https%3A%2F%2Fassets.grokipedia.com%2Fwiki%2Fimages%2Fdetails-2.jpg&w=1200&q=75' alt='Detail 2' />
            <figcaption>Detail image two</figcaption>
          </figure>
        </article>
      </body>
    </html>
    """

    page = from_html(html, source_url="https://grokipedia.com/page/sample")

    subsection = page.sections[0].subsections[0]
    assert subsection.title == "Details"
    assert len(subsection.media) == 2
    assert subsection.media[0].index == 1
    assert subsection.media[0].image_url.endswith("details-1.jpg")
    assert subsection.media[1].index == 2
    assert subsection.media[1].image_url.endswith("details-2.jpg")


def test_from_html_parses_embedded_markdown_subsection_media() -> None:
    html = """
    <html>
      <body>
        <article class='text-[16px]'>
          <h1 id='sample'>Sample Page</h1>
          <span data-tts-block='true'>Sample intro.</span>
          <h2 id='overview'>Overview</h2>
          <h3 id='details'>Details</h3>
          <span data-tts-block='true'>Details text.</span>
        </article>
        <script>
          self.__next_f.push([1,"\n## Overview\n\n### Details\n\n![Embedded detail](https://assets.grokipedia.com/wiki/images/details-embedded.jpg)\n*Embedded detail caption*\n\n![Paren detail](https://assets.grokipedia.com/wiki/images/details-(2026).jpg)\n*Paren detail caption*\n"]);
        </script>
      </body>
    </html>
    """

    page = from_html(html, source_url="https://grokipedia.com/page/sample")

    subsection = page.sections[0].subsections[0]
    assert subsection.title == "Details"
    assert len(subsection.media) == 2
    assert subsection.media[0].index == 1
    assert subsection.media[0].image_url.endswith("details-embedded.jpg")
    assert subsection.media[0].alt_text == "Embedded detail"
    assert subsection.media[0].caption == "Embedded detail caption"
    assert subsection.media[1].index == 2
    assert subsection.media[1].image_url.endswith("details-(2026).jpg")
    assert subsection.media[1].alt_text == "Paren detail"
    assert subsection.media[1].caption == "Paren detail caption"


def test_page_markdown_renders_structured_content() -> None:
    html = """
    <html>
      <body>
        <article class='text-[16px]'>
          <h1 id='sample'>Sample Page</h1>
          <p>Sample intro text.</p>
          <div>
            <dt>Founded</dt>
            <dd>2020</dd>
          </div>
          <figure>
            <img src='https://assets.grokipedia.com/wiki/images/lead.jpg' alt='Lead image' />
            <figcaption>Lead caption</figcaption>
          </figure>
          <h2 id='overview'>Overview</h2>
          <p>Overview body text.</p>
          <h3 id='details'>Details</h3>
          <p>Details body text.</p>
          <figure>
            <img src='https://assets.grokipedia.com/wiki/images/detail.jpg' alt='Detail image' />
            <figcaption>Detail caption</figcaption>
          </figure>
        </article>
      </body>
    </html>
    """

    page = from_html(html, source_url="https://grokipedia.com/page/sample")
    markdown = page.markdown

    assert "# Sample Page" in markdown
    assert "Sample intro text." in markdown
    assert "## Infobox" in markdown
    assert "- **Founded:** 2020" in markdown
    assert (
        "![Lead image](https://assets.grokipedia.com/wiki/images/lead.jpg)" in markdown
    )
    assert "## Overview" in markdown
    assert "### Details" in markdown
    assert (
        "![Detail image](https://assets.grokipedia.com/wiki/images/detail.jpg)"
        in markdown
    )


def test_page_to_json_wraps_to_dict() -> None:
    html = """
    <html>
      <body>
        <article class='text-[16px]'>
          <h1 id='sample'>Sample Page</h1>
          <p>This is a sample intro.</p>
          <h2 id='overview'>Overview</h2>
          <p>This is body content.</p>
        </article>
      </body>
    </html>
    """

    page = from_html(html, source_url="https://grokipedia.com/page/sample")

    payload_from_json = json.loads(page.to_json())
    payload_from_dict = page.to_dict()

    assert payload_from_json == payload_from_dict
    assert payload_from_dict["title"] == "Sample Page"
    assert payload_from_dict["sections"][0]["title"] == "Overview"
    assert payload_from_dict["links"] == []
    assert payload_from_dict["metadata"]["fetched_at_utc"].endswith("Z")


def test_page_from_dict_round_trip() -> None:
    page = from_html(
        """
        <html>
          <body>
            <article class='text-[16px]'>
              <h1 id='sample'>Sample Page</h1>
              <p>Intro content.</p>
              <h2 id='overview'>Overview</h2>
              <p>Body content.</p>
            </article>
          </body>
        </html>
        """,
        source_url="https://grokipedia.com/page/sample",
    )

    payload = page.to_dict()
    restored = Page.from_dict(payload)

    assert restored.to_dict() == payload
    assert restored.metadata.fetched_at_utc.tzinfo is not None


def test_page_from_json_round_trip() -> None:
    page = from_html(
        """
        <html>
          <body>
            <article class='text-[16px]'>
              <h1 id='sample'>Sample Page</h1>
              <p>Intro content.</p>
              <h2 id='overview'>Overview</h2>
              <p>Body content.</p>
            </article>
          </body>
        </html>
        """,
        source_url="https://grokipedia.com/page/sample",
    )

    payload = page.to_json()
    restored = Page.from_json(payload)

    assert restored.to_dict() == page.to_dict()


def test_page_from_json_rejects_non_object_payload() -> None:
    try:
        Page.from_json("[]")
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-object payload")
