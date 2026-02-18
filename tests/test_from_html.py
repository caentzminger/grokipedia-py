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
    assert page.lede_markdown == "This is a sample lede."
    assert page.sections[0].title == "Overview"
