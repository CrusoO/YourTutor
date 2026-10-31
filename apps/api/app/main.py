from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.admin import router as admin_router
from app.auth.router import router as auth_router
from app.config import production_flag_errors, production_secret_errors, settings
from app.dev.router import router as dev_router
from app.explain.router import router as explain_router
from app.health import database_ready, ping_redis
from app.metrics.router import router as metrics_router
from app.offline.router import router as offline_router
from app.proxy import (
    client_ip,
    header_ignored_from_loopback,
    note_ignored_header,
    trusted_networks,
)
from app.ratelimit import limiter
from app.registries.startup import validate_startup_config
from app.research.router import router as research_router
from app.video_jobs.router import router as video_jobs_router

logger = logging.getLogger("yourtutor.access")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    validate_startup_config()  # unknown JURISDICTION_PROFILE etc. stops startup
    trusted_networks()  # a bad TRUSTED_PROXIES entry stops startup
    unsafe = production_flag_errors(settings)
    if unsafe:
        raise RuntimeError(
            f"Refusing to start: APP_ENV=production but {', '.join(unsafe)} "
            "is on. These switches are for local development only; turn them off."
        )
    default_secrets = production_secret_errors(settings)
    if default_secrets:
        raise RuntimeError(
            f"Refusing to start: APP_ENV=production but {', '.join(default_secrets)} still has "
            "its development default. Set a real value in the environment."
        )
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
app.include_router(offline_router)
app.include_router(metrics_router)
app.include_router(admin_router)
app.include_router(dev_router)
app.include_router(video_jobs_router)
app.include_router(explain_router)


def access_log_line(method: str, path: str, status: int) -> str:
    """Path only — query strings are never logged."""
    return f"{method} {path} {status}"


@app.middleware("http")
async def rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
    note_ignored_header(request)
    if settings.rate_limit_enabled and request.method != "OPTIONS":
        wait = limiter.check(client_ip(request), request.url.path)
        if wait is not None:
            return JSONResponse(
                {"detail": "too many requests"}, status_code=429, headers={"Retry-After": str(wait)}
            )
    return await call_next(request)


@app.middleware("http")
async def access_log_no_query(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    logger.info(access_log_line(request.method, request.url.path, response.status_code))
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Never show a student or guardian a stack trace; the log has it, keyed by the request id."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    logger.error(
        "unhandled error %s on %s %s", request_id, request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(
        {"detail": "something went wrong", "request_id": request_id},
        status_code=500,
        headers={"X-Request-Id": request_id},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/ready")
async def ready() -> JSONResponse:
    """Ready when the database answers `select 1`; 503 with a plain body when it does not."""
    database = await database_ready()
    redis = await asyncio.to_thread(ping_redis)  # reported only: nothing here needs Redis yet
    body: dict[str, object] = {
        "status": "ok" if database else "unavailable",
        "database": "ok" if database else "down",
        "redis": redis,
        "forwarded_header_ignored": header_ignored_from_loopback(),
    }
    if database:
        body["allow_draft_content"] = settings.allow_draft_content
    return JSONResponse(body, status_code=200 if database else 503)
