from __future__ import annotations

from urllib.parse import quote, unquote, urlparse


def resolve_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ValueError("base_url must not be empty")
    return normalized


def resolve_user_agent(user_agent: str | None, *, default_user_agent: str) -> str:
    return user_agent or default_user_agent


def page_url_from_slug(slug: str, *, base_url: str) -> str:
    normalized_slug = slug.strip()
    if not normalized_slug:
        raise ValueError("slug must not be empty")

    encoded_slug = quote(normalized_slug, safe="!$&'()*+,;=:@._~-")
    return f"{resolve_base_url(base_url)}/page/{encoded_slug}"


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = unquote(parsed.path)
    return f"{scheme}://{netloc}{path}"
