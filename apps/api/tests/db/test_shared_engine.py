from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import session as session_module


def test_get_db_reuses_one_engine_for_every_request() -> None:
    first = session_module.shared_factory()
    second = session_module.shared_factory()
    assert first is second
    assert session_module.session_factory() is first
    gen_a, gen_b = session_module.get_db(), session_module.get_db()
    a, b = next(gen_a), next(gen_b)
    try:
        assert isinstance(a, Session) and a.get_bind() is b.get_bind()
    finally:
        gen_a.close()
        gen_b.close()


def test_the_shared_engine_pings_and_has_a_pool() -> None:
    bind = session_module.shared_factory().kw["bind"]
    assert bind.pool._pre_ping is True
    assert bind.pool.size() == 10


def test_an_explicit_url_still_gets_its_own_engine() -> None:
    other = session_module.session_factory("sqlite://")
    assert other is not session_module.shared_factory()
