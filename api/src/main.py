"""skill-web-fetch FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from config import settings
from routes.fetch import router as fetch_router
from routes.health import router as health_router
from routes.search import router as search_router

logging.basicConfig(level=settings.log_level.upper())

app = FastAPI(title="skill-web-fetch", docs_url="/docs", redoc_url=None)

app.include_router(health_router)
app.include_router(fetch_router)
app.include_router(search_router)
