from __future__ import annotations

from urllib.parse import quote, unquote, urlencode, urlparse


def resolve_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ValueError("base_url must not be empty")
    return normalized


def resolve_user_agent(user_agent: str | None, *, default_user_agent: str) -> str:
    return user_agent or default_user_agent


def slug_from_title(title: str) -> str:
    normalized_title = "_".join(title.strip().split())
    if not normalized_title:
        raise ValueError("title must not be empty")
    return normalized_title


def page_url_from_slug(slug: str, *, base_url: str) -> str:
    normalized_slug = slug.strip()
    if not normalized_slug:
        raise ValueError("slug must not be empty")

    encoded_slug = quote(normalized_slug, safe="!$&'()*+,;=:@._~-")
    return f"{resolve_base_url(base_url)}/page/{encoded_slug}"


def edit_history_url_from_slug(
    slug: str,
    *,
    limit: int,
    offset: int,
    base_url: str,
) -> str:
    normalized_slug = slug.strip()
    if not normalized_slug:
        raise ValueError("slug must not be empty")
    if limit < 0:
        raise ValueError("limit must be >= 0")
    if offset < 0:
        raise ValueError("offset must be >= 0")

    query = urlencode(
        {
            "slug": normalized_slug,
            "limit": limit,
            "offset": offset,
        }
    )
    return f"{resolve_base_url(base_url)}/api/list-edit-requests-by-slug?{query}"


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = unquote(parsed.path)
    return f"{scheme}://{netloc}{path}"
