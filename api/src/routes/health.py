from __future__ import annotations

import httpx
from fastapi import APIRouter

from config import settings

router = APIRouter()

_HEALTH_TIMEOUT = 3.0


@router.get("/health")
async def health() -> dict:
    checks: dict[str, str] = {}

    if settings.searxng_base_url:
        url = f"{settings.searxng_base_url.rstrip('/')}/healthz"
        try:
            async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT) as client:
                resp = await client.get(url)
            checks["searxng"] = "ok" if resp.status_code < 500 else "degraded"
        except Exception:
            checks["searxng"] = "unreachable"
    else:
        checks["searxng"] = "not configured"

    overall = "ok" if all(v in ("ok", "not configured") for v in checks.values()) else "degraded"
    return {"status": overall, "service": "skill-web-fetch", **checks}
