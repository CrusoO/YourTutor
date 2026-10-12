"""UI-1: nothing a visitor types into the composer is stored or logged.

The composer matches typed text against topic titles in the browser and drops it. These tests prove
the server side of that promise: a unique marker, sent everywhere typed text could plausibly reach
(query strings, bodies, headers, the finder-rules and guest endpoints), never appears in the log
lines or in any text or JSON column of any table.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, String, Text, cast, select
from sqlalchemy.orm import Session

from app.db.models import Base
from tests.conftest import auth_header

MARKER = "zq-marker-8f31c2"


def _everywhere(client: TestClient) -> None:
    """Send the marker through the routes a browser could reach with it."""
    client.get("/context/options", params={"q": MARKER, "topic": MARKER})
    client.get("/context/finder-rules", params={"language": "en", "q": MARKER, "text": MARKER})
    client.get("/health", params={"q": MARKER}, headers={"X-Typed": MARKER})
    # A guest start refuses unknown fields (422); the refusal must not echo or keep them.
    client.post(
        "/guest/start",
        json={"curriculum_id": "bhutan", "grade": 9, "typed": MARKER, "note": MARKER},
    )
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    headers = auth_header(guest["token"])
    client.get("/students/me/today", params={"q": MARKER}, headers=headers)
    client.get(
        f"/students/{guest['student_id']}/chapters", params={"search": MARKER}, headers=headers
    )


def test_the_access_log_never_carries_typed_text(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        _everywhere(client)
    # Only the server's own loggers: the test client's httpx logger prints the URL it requested.
    server = [r for r in caplog.records if not r.name.startswith(("httpx", "httpcore"))]
    assert MARKER not in " | ".join(r.getMessage() for r in server)
    lines = [r.getMessage() for r in server if r.name == "yourtutor.access"]
    assert lines, "the access log should have recorded the requests"
    assert all("?" not in line for line in lines)  # path only: no query string


def test_no_table_holds_typed_text(client: TestClient, db: Session) -> None:
    _everywhere(client)
    db.expire_all()
    hits: list[str] = []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if not isinstance(column.type, (String, Text, JSON)):
                continue
            found = db.execute(
                select(table).where(cast(column, String).ilike(f"%{MARKER}%")).limit(1)
            ).first()
            if found:
                hits.append(f"{table.name}.{column.name}")
    assert hits == []
