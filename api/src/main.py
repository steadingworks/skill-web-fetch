"""skill-web-fetch FastAPI application."""

from __future__ import annotations

import json
import logging
import time

from fastapi import FastAPI, Request

from config import settings
from routes.fetch import router as fetch_router
from routes.health import router as health_router
from routes.search import router as search_router


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


handler = logging.StreamHandler()
handler.setFormatter(_JsonFormatter())
logging.basicConfig(level=settings.log_level.upper(), handlers=[handler])

logger = logging.getLogger("skill-web-fetch")

app = FastAPI(title="skill-web-fetch", docs_url="/docs", redoc_url=None)

app.include_router(health_router)
app.include_router(fetch_router)
app.include_router(search_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    logger.info(
        json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        })
    )
    return response
