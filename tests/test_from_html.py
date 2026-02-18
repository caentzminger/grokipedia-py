from __future__ import annotations

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
