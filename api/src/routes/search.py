"""GET /v1/search — web search proxy via SearXNG.

Returns 503 with a clear message if WEBFETCH_SEARXNG_BASE_URL is not configured.
This is not an error state — search is an optional capability.

Error mapping:
  401 — token invalid or expired
  403 — token scope insufficient
  502 — search backend error or connection failure
  503 — search backend not configured
  504 — search backend timeout
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_jwt
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

_SEARCH_TIMEOUT = 15.0


@router.get("/v1/search")
async def search(
    q: Annotated[str, Query(description="Search query")],
    limit: int = Query(default=10, ge=1, le=50),
    _: dict = Depends(require_jwt),
) -> dict:
    if not settings.searxng_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search backend not configured. Set WEBFETCH_SEARXNG_BASE_URL.",
        )

    searxng_url = f"{settings.searxng_base_url.rstrip('/')}/search"
    try:
        async with httpx.AsyncClient(timeout=_SEARCH_TIMEOUT) as client:
            resp = await client.get(
                searxng_url,
                params={
                    "q": q,
                    "format": "json",
                    "categories": "general",
                    "language": "en",
                },
            )
            resp.raise_for_status()
    except httpx.TimeoutException:
        logger.error(json.dumps({
            "event": "upstream_timeout",
            "upstream": searxng_url,
            "timeout_seconds": _SEARCH_TIMEOUT,
        }))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Search backend timed out",
        )
    except httpx.HTTPStatusError as exc:
        logger.error(json.dumps({
            "event": "upstream_http_error",
            "upstream": searxng_url,
            "upstream_status": exc.response.status_code,
        }))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search backend returned HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        logger.error(json.dumps({
            "event": "upstream_request_error",
            "upstream": searxng_url,
            "error": type(exc).__name__,
        }))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search request failed: {type(exc).__name__}",
        )

    data = resp.json()
    results = data.get("results", [])[:limit]
    return {
        "query": q,
        "results": [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": r.get("content"),
                "engine": r.get("engine"),
            }
            for r in results
        ],
    }
