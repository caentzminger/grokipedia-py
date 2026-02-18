from __future__ import annotations

import json

from grokipedia import from_html


def test_from_html_parses_without_network() -> None:
    html = """
    <html>
      <head>
        <meta property='og:url' content='https://grokipedia.com/page/sample' />
      </head>
      <body>
        <article class='text-[16px]'>
          <h1 id='sample'>Sample Page</h1>
          <p>This is a sample lede.</p>
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
    assert page.lede_text == "This is a sample lede."
    assert page.infobox == []
    assert page.lead_media is None
    assert page.sections[0].title == "Overview"


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

    assert page.lede_text == "Acme is a company."
    assert page.sections[0].title == "Overview"
    assert page.sections[0].subsections[0].title == "Details"
    assert page.sections[0].subsections[0].text == "Acme builds rockets and tools."


def test_from_html_parses_infobox_and_lead_media() -> None:
    html = """
    <html>
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

    assert page.lede_text == "Jeffrey Epstein was an American financier."

    assert len(page.infobox) == 2
    assert page.infobox[0].label == "Birth Date"
    assert page.infobox[0].value == "January 20, 1953"
    assert page.infobox[1].label == "Birth Place"
    assert page.infobox[1].value == "Brooklyn, New York City, U.S."

    assert page.lead_media is not None
    assert (
        page.lead_media.image_url
        == "https://assets.grokipedia.com/wiki/images/example.jpg"
    )
    assert page.lead_media.caption == "Jeffrey Epstein"
    assert page.lead_media.alt_text == "Jeffrey Epstein"


def test_page_to_json_serializes_nested_content() -> None:
    html = """
    <html>
      <body>
        <article class='text-[16px]'>
          <h1 id='sample'>Sample Page</h1>
          <p>This is a sample lede.</p>
          <h2 id='overview'>Overview</h2>
          <p>This is body content.</p>
        </article>
      </body>
    </html>
    """

    page = from_html(html, source_url="https://grokipedia.com/page/sample")
    payload = json.loads(page.to_json())

    assert payload["title"] == "Sample Page"
    assert payload["sections"][0]["title"] == "Overview"
    assert payload["metadata"]["fetched_at_utc"].endswith("Z")
