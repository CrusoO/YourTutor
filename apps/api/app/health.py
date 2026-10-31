"""Readiness: can this API reach its database? (/health stays a plain liveness answer.)

`/ready` runs `select 1` with a short timeout. A failure is reported as 503 with a plain body; the
cause (wrong password, host down) goes to the log, never to the caller. Redis is pinged and
reported, but nothing in the app uses it yet, so it never fails readiness.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

from app.config import settings
from app.db.session import database_url

logger = logging.getLogger("yourtutor.access")
DB_TIMEOUT_SECONDS = 2.0
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ready")


def check_database(url: str | None = None) -> bool:
    """True when `select 1` succeeds. Connecting is bounded by the driver's own timeout."""
    engine = None
    try:
        target = database_url(url)
        args = (
            {"connect_timeout": int(DB_TIMEOUT_SECONDS)} if target.startswith("postgresql") else {}
        )
        engine = create_engine(target, future=True, connect_args=args)
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        logger.warning("readiness: database check failed (%s)", type(exc).__name__)
        return False
    finally:
        if engine is not None:
            engine.dispose()


def ping_redis(url: str | None = None) -> str:
    """ "ok" when the Redis at REDIS_URL answers PING, otherwise "down"."""
    parsed = urlparse(url or settings.redis_url)
    try:
        with socket.create_connection(
            (parsed.hostname or "127.0.0.1", parsed.port or 6379), 1.0
        ) as s:
            s.settimeout(1.0)
            s.sendall(b"PING\r\n")
            return "ok" if s.recv(16).startswith(b"+PONG") else "down"
    except OSError:
        return "down"


async def database_ready() -> bool:
    """check_database with an overall deadline, so a hung connection cannot hang the probe."""
    loop = asyncio.get_running_loop()
    pending = loop.run_in_executor(_POOL, check_database)
    done, _ = await asyncio.wait({pending}, timeout=DB_TIMEOUT_SECONDS + 0.5)
    if not done:
        logger.warning("readiness: database check timed out")
        return False
    return pending.result()
