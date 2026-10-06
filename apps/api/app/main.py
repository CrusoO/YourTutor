from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.auth.admin import router as admin_router
from app.auth.router import router as auth_router
from app.config import settings
from app.dev.router import router as dev_router
from app.registries.startup import validate_startup_config
from app.research.router import router as research_router

logger = logging.getLogger("yourtutor.access")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    validate_startup_config()  # unknown JURISDICTION_PROFILE etc. stops startup
    yield


_LOCAL_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)


def allowed_origins(extra: str) -> list[str]:
    """Local origins plus explicit extras (e.g. a PC's LAN address for phone preview)."""
    origins = list(_LOCAL_ORIGINS)
    for raw in extra.split(","):
        origin = raw.strip()
        if not origin:
            continue
        if "*" in origin:
            raise ValueError("CORS_EXTRA_ORIGINS: a wildcard origin is not allowed")
        origins.append(origin)
    return origins


app = FastAPI(title="YourTutor API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(settings.cors_extra_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(research_router)
app.include_router(admin_router)
app.include_router(dev_router)


def access_log_line(method: str, path: str, status: int) -> str:
    """Path only — query strings are never logged."""
    return f"{method} {path} {status}"


@app.middleware("http")
async def access_log_no_query(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    logger.info(access_log_line(request.method, request.url.path, response.status_code))
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/ready")
def ready() -> dict[str, object]:
    return {
        "status": "ok",
        "allow_draft_content": settings.allow_draft_content,
    }
