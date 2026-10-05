from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import now_utc
from app.auth.sender import EmailOtpSender, MemoryOtpSender, get_otp_sender, set_otp_sender
from app.config import settings
from app.db.models import Base, UserRow
from app.db.session import get_db
from app.main import app

settings.pin_hash_iterations = 1_000
settings.research_module = True


@pytest.fixture(autouse=True)
def _restore_settings() -> Generator[None, None, None]:
    """Tests mutate the global settings singleton; undo it so test order cannot matter."""
    snapshot = settings.model_dump()
    yield
    for name, value in snapshot.items():
        if getattr(settings, name) != value:
            setattr(settings, name, value)


def _sqlite_url() -> str:
    return "sqlite://"


def _try_postgres_url() -> str | None:
    env = os.environ.get("TEST_DATABASE_URL")
    if env:
        return env
    return None


@pytest.fixture(scope="session")
def database_url() -> str:
    return _try_postgres_url() or _sqlite_url()


@pytest.fixture
def engine(database_url: str) -> Generator[Engine, None, None]:
    kwargs: dict = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool
    eng = create_engine(database_url, **kwargs)
    if database_url.startswith("postgresql"):
        with eng.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    from app.registries.seed_db import seed_g0_registry

    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False, future=True)
    with factory() as session:
        seed_g0_registry(session)
        session.commit()
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def sender() -> Generator[MemoryOtpSender, None, None]:
    memory = MemoryOtpSender()
    set_otp_sender(memory)
    yield memory
    set_otp_sender(EmailOtpSender())


@pytest.fixture
def client(engine: Engine, sender: MemoryOtpSender) -> Generator[TestClient, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _get_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
            session.commit()
        except HTTPException:
            session.commit()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_otp_sender] = lambda: sender
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def signup(client: TestClient, sender: MemoryOtpSender, email: str) -> str:
    response = client.post("/auth/request-otp", json={"email": email})
    assert response.status_code == 200, response.text
    code = sender.inbox[email]
    verified = client.post("/auth/verify-otp", json={"email": email, "code": code})
    assert verified.status_code == 200, verified.text
    return verified.json()["access_token"]


def seed_user(db: Session, role: str, email: str) -> UserRow:
    user = UserRow(
        id=uuid.uuid4(),
        role=role,
        email=email,
        locale="en",
        created_at=now_utc(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@dataclass
class World:
    parent_token: str
    parent_id: str
    other_parent_token: str
    student_share_id: str
    student_noshare_id: str
    student_token: str
    teacher_token: str
    class_id: str
    admin_token: str
    comparison_token: str
    comparison_form: str
    comparison_participant_id: str
    consent_share_id: str


@pytest.fixture
def world(client: TestClient, sender: MemoryOtpSender, db: Session) -> World:
    parent_token = signup(client, sender, "parent@example.com")
    other_parent_token = signup(client, sender, "other@example.com")
    created = client.post(
        "/students",
        json={
            "display_name": "Share Kid",
            "grade": 9,
            "board": "bhutan",
        },
        headers=auth_header(parent_token),
    )
    assert created.status_code == 200, created.text
    share_id = created.json()["id"]
    created2 = client.post(
        "/students",
        json={
            "display_name": "Private Kid",
            "grade": 9,
            "board": "seba",
        },
        headers=auth_header(parent_token),
    )
    noshare_id = created2.json()["id"]
    consent = client.post(
        f"/students/{share_id}/consent",
        json={
            "version": "v1",
            "scopes": ["tutoring", "teacher_share", "research_pseudonymised", "ai_processing"],
        },
        headers=auth_header(parent_token),
    )
    assert consent.status_code == 200, consent.text
    client.post(
        f"/students/{noshare_id}/consent",
        json={"version": "v1", "scopes": ["tutoring"]},
        headers=auth_header(parent_token),
    )
    client.post(
        f"/students/{share_id}/pin",
        json={"pin": "1234"},
        headers=auth_header(parent_token),
    )
    pin = client.post(f"/students/{share_id}/pin/verify", json={"pin": "1234"})
    assert pin.status_code == 200, pin.text
    export = client.get("/parents/me/export", headers=auth_header(parent_token))
    parent_id = export.json()["user"]["id"]

    teacher = seed_user(db, "teacher", "teacher@example.com")
    admin = seed_user(db, "admin", "admin@example.com")
    teacher_token = signup(client, sender, teacher.email)
    admin_token = signup(client, sender, admin.email)
    klass = client.post(
        "/classes",
        json={"name": "9A", "board": "bhutan"},
        headers=auth_header(teacher_token),
    )
    assert klass.status_code == 200, klass.text
    class_id = klass.json()["id"]
    client.post(
        f"/classes/{class_id}/members",
        json={"student_id": share_id},
        headers=auth_header(teacher_token),
    )
    client.post(
        f"/classes/{class_id}/members",
        json={"student_id": noshare_id},
        headers=auth_header(teacher_token),
    )
    enrolled = client.post(
        "/study/participants",
        json={
            "site_id": "site-thimphu",
            "group": "comparison",
            "consent_id": consent.json()["id"],
        },
        headers=auth_header(admin_token),
    )
    assert enrolled.status_code == 200, enrolled.text
    comparison_form = enrolled.json()["pretest_form"]
    token = client.post(
        "/checkpoints/cp1/tokens",
        json={
            "participant_id": enrolled.json()["id"],
            "form": comparison_form,
            "consent_id": consent.json()["id"],
        },
        headers=auth_header(admin_token),
    )
    assert token.status_code == 200, token.text
    redeemed = client.post("/checkpoints/redeem", json={"token": token.json()["token"]})
    return World(
        parent_token=parent_token,
        parent_id=parent_id,
        other_parent_token=other_parent_token,
        student_share_id=share_id,
        student_noshare_id=noshare_id,
        student_token=pin.json()["access_token"],
        teacher_token=teacher_token,
        class_id=class_id,
        admin_token=admin_token,
        comparison_token=redeemed.json()["access_token"],
        comparison_form=comparison_form,
        comparison_participant_id=enrolled.json()["id"],
        consent_share_id=consent.json()["id"],
    )
