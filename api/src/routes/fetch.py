"""GET /v1/fetch — fetch a URL and return clean extracted content.

Fetches the URL via httpx, extracts readable content from HTML using BeautifulSoup,
and returns either markdown or plain text. Non-HTML responses are returned as-is.

Error mapping:
  400 — invalid URL scheme (non http/https)
  401 — token invalid or expired
  403 — token scope insufficient
  502 — upstream HTTP error or connection failure
  504 — upstream timeout
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Annotated

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_jwt

router = APIRouter()
logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 20.0
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB cap on raw response
_MAX_CHARS = 50_000
_NOISE_TAGS = frozenset({
    "script", "style", "nav", "footer", "header",
    "aside", "form", "iframe", "noscript", "svg",
})


class Format(str, Enum):
    markdown = "markdown"
    text = "text"


@router.get("/v1/fetch")
async def fetch(
    url: Annotated[str, Query(description="URL to fetch (http/https only)")],
    format: Format = Format.markdown,
    _: dict = Depends(require_jwt),
) -> dict:
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must use http or https scheme",
        )

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_FETCH_TIMEOUT,
            headers={"User-Agent": "skill-web-fetch/1.0"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.TimeoutException:
        logger.error(json.dumps({
            "event": "upstream_timeout",
            "upstream": url,
            "timeout_seconds": _FETCH_TIMEOUT,
        }))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream timed out",
        )
    except httpx.HTTPStatusError as exc:
        logger.error(json.dumps({
            "event": "upstream_http_error",
            "upstream": url,
            "upstream_status": exc.response.status_code,
        }))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream returned HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        logger.error(json.dumps({
            "event": "upstream_request_error",
            "upstream": url,
            "error": type(exc).__name__,
        }))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Request failed: {type(exc).__name__}",
        )

    raw = resp.content[:_MAX_BYTES]
    content_type = resp.headers.get("content-type", "")

    if "html" not in content_type:
        return {
            "url": str(resp.url),
            "format": "text",
            "content": raw.decode("utf-8", errors="replace")[:_MAX_CHARS],
        }

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    root = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find(id="content")
        or soup.find(id="main")
        or soup.body
        or soup
    )

    if format == Format.text:
        content = root.get_text(separator="\n", strip=True)[:_MAX_CHARS]
    else:
        content = _to_markdown(root)[:_MAX_CHARS]

    return {"url": str(resp.url), "format": format, "content": content}


def _to_markdown(node) -> str:
    """Convert a BeautifulSoup node tree to approximate Markdown."""
    parts: list[str] = []

    def walk(n) -> None:
        if isinstance(n, NavigableString):
            text = str(n)
            if text.strip():
                parts.append(text)
            return
        if not isinstance(n, Tag):
            return

        name = n.name
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            parts.append(f"\n{'#' * int(name[1])} ")
            for c in n.children:
                walk(c)
            parts.append("\n")
        elif name == "p":
            parts.append("\n")
            for c in n.children:
                walk(c)
            parts.append("\n")
        elif name in {"strong", "b"}:
            parts.append("**")
            for c in n.children:
                walk(c)
            parts.append("**")
        elif name in {"em", "i"}:
            parts.append("_")
            for c in n.children:
                walk(c)
            parts.append("_")
        elif name == "a":
            parts.append("[")
            for c in n.children:
                walk(c)
            parts.append(f"]({n.get('href', '')})")
        elif name == "li":
            parts.append("\n- ")
            for c in n.children:
                walk(c)
        elif name == "code":
            parts.append("`")
            for c in n.children:
                walk(c)
            parts.append("`")
        elif name == "pre":
            parts.append("\n```\n")
            for c in n.children:
                walk(c)
            parts.append("\n```\n")
        elif name == "blockquote":
            parts.append("\n> ")
            for c in n.children:
                walk(c)
            parts.append("\n")
        elif name == "br":
            parts.append("\n")
        elif name == "hr":
            parts.append("\n---\n")
        else:
            for c in n.children:
                walk(c)

    walk(node)
    return "".join(parts)
