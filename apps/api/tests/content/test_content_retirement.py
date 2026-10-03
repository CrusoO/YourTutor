from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.auth.security import now_utc
from app.content.gate import RETIRED_STATUS
from app.content.loader import PruneBlockedError, load_path
from app.content.packs import item_row_offline_pack_eligible
from app.db.models import ItemRow, MasteryRow, SkillRow, StudentRow
from app.orchestrator.policy import _pick_item, _similar_item
from app.player.runtime import load_catalog
from app.db.session import session_factory
from tests.conftest import World, auth_header
from tests.content.conftest import _PRACTICE_STEMS, minimal_item, minimal_skill, write_yaml
from tests.orchestrator.conftest import catalog_item, make_learner, make_session


def _write_skill_with_practice(content_root: Path, skill_id: str, prefix: str) -> None:
    write_yaml(content_root / "skills" / f"{prefix}.yaml", minimal_skill(skill_id))
    for index in range(5):
        n, m = 20 + index, 35 + index
        stem = f"S2-{index}: " + _PRACTICE_STEMS[index].format(n=n, m=m)
        write_yaml(
            content_root / "items" / f"{prefix}_p{index}.yaml",
            minimal_item(
                f"ITEM.{prefix.upper()}.P{index}",
                skill=skill_id,
                pool="practice",
                status="approved",
                stem=stem,
                answer=str(m - n),
            ),
        )


def _add_student(db_url: str) -> uuid.UUID:
    from app.db.models import UserRow

    factory = session_factory(db_url)
    with factory() as session:
        user = UserRow(
            id=uuid.uuid4(),
            role="parent",
            email=f"p-{uuid.uuid4().hex}@example.com",
            locale="en",
            created_at=now_utc(),
        )
        session.add(user)
        student_id = uuid.uuid4()
        from app.registries.seed_db import seed_g0_registry

        seed_g0_registry(session)
        session.add(
            StudentRow(
                id=student_id,
                parent_id=user.id,
                display_name="Test",
                grade=9,
                board="bhutan",
                curriculum_id="bhutan",
                book_id="bhutan_class9",
                context_key={
                    "curriculum_id": "bhutan",
                    "book_id": "bhutan_class9",
                    "chapter_id": "bhutan_class9",
                },
                home_language="en",
                exam_language="en",
                timezone="Asia/Thimphu",
                created_at=now_utc(),
            )
        )
        session.commit()
        return student_id


def test_reload_without_skill_retires_and_keeps_mastery(content_root: Path, tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'retire.db'}"
    _write_skill_with_practice(content_root, "MATH.S2", "s2")
    load_path(content_root, database_url=url)
    student_id = _add_student(url)
    factory = session_factory(url)
    with factory() as session:
        session.add(
            MasteryRow(
                student_id=student_id,
                skill_id="MATH.S2",
                p_known=0.4,
                last_updated=now_utc(),
            )
        )
        session.commit()
    (content_root / "skills" / "s2.yaml").unlink()
    for index in range(5):
        (content_root / "items" / f"s2_p{index}.yaml").unlink()
    load_path(content_root, database_url=url)
    with factory() as session:
        skill = session.get(SkillRow, "MATH.S2")
        assert skill is not None
        assert skill.status == RETIRED_STATUS
        mastery = session.get(MasteryRow, (student_id, "MATH.S2"))
        assert mastery is not None
        assert mastery.p_known == 0.4


def test_retired_items_excluded_from_selection_and_similar(content_root: Path, tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'sel.db'}"
    load_path(content_root, database_url=url)
    factory = session_factory(url)
    with factory() as session:
        session.query(ItemRow).filter(ItemRow.id == "ITEM.P0").update(
            {ItemRow.status: RETIRED_STATUS}
        )
        session.commit()
        catalog = load_catalog(session, allow_draft=False)
    ids = {row.id for row in catalog}
    assert "ITEM.P0" not in ids
    state = make_session(*catalog, allow_draft=False)
    picked = _pick_item(state, "MATH.S1", p_known=0.3)
    assert picked is not None
    assert picked.id != "ITEM.P0"
    retired = catalog_item("ITEM.P0", status=RETIRED_STATUS)
    live = catalog_item("ITEM.P1")
    alt = catalog_item("ITEM.P2", answer="6")
    state = make_session(retired, live, alt, allow_draft=False)
    state.similar_from_item_id = live.id
    state.current_item_id = live.id
    state.shown_item_ids = [live.id]
    similar = _similar_item(make_learner(), state)
    assert similar.item_id != retired.id


def test_retired_items_not_in_offline_pack(content_root: Path, tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'pack.db'}"
    load_path(content_root, database_url=url)
    factory = session_factory(url)
    with factory() as session:
        row = session.get(ItemRow, "ITEM.P0")
        assert row is not None
        row.status = "approved"
        assert item_row_offline_pack_eligible(row, allow_draft=False)
        row.status = RETIRED_STATUS
        assert not item_row_offline_pack_eligible(row, allow_draft=False)


def test_prune_refuses_when_mastery_exists(content_root: Path, tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'prune-no.db'}"
    _write_skill_with_practice(content_root, "MATH.S2", "s2")
    load_path(content_root, database_url=url)
    student_id = _add_student(url)
    factory = session_factory(url)
    with factory() as session:
        session.add(
            MasteryRow(
                student_id=student_id,
                skill_id="MATH.S2",
                p_known=0.2,
                last_updated=now_utc(),
            )
        )
        session.commit()
    (content_root / "skills" / "s2.yaml").unlink()
    for index in range(5):
        (content_root / "items" / f"s2_p{index}.yaml").unlink()
    with pytest.raises(PruneBlockedError):
        load_path(content_root, database_url=url, prune=True)
    with factory() as session:
        skill = session.get(SkillRow, "MATH.S2")
        assert skill is not None
        assert session.get(MasteryRow, (student_id, "MATH.S2")) is not None


def test_prune_succeeds_on_clean_db(content_root: Path, tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'prune-yes.db'}"
    _write_skill_with_practice(content_root, "MATH.S2", "s2")
    load_path(content_root, database_url=url)
    (content_root / "skills" / "s2.yaml").unlink()
    for index in range(5):
        (content_root / "items" / f"s2_p{index}.yaml").unlink()
    load_path(content_root, database_url=url, prune=True)
    factory = session_factory(url)
    with factory() as session:
        assert session.get(SkillRow, "MATH.S2") is None
        assert session.get(ItemRow, "ITEM.S2") is None


def test_admin_replay_resolves_retired_item(client: TestClient, world: World, db) -> None:
    from app.db.models import EventRow, SessionRow

    db.add(
        ItemRow(
            id="ITEM.REPLAY",
            skill_ids=["MATH.S1"],
            primary_skill="MATH.S1",
            difficulty=0.3,
            type="expression",
            pool="practice",
            stem={"en": "Retired stem", "ne": None, "as": None},
            verify=None,
            options=[],
            answer={"sympy": "5", "accept": ["5"]},
            solution_steps=[],
            hints=[],
            prediction_prompt={"en": "", "ne": None, "as": None},
            misconception_rules=[],
            status=RETIRED_STATUS,
            reviewed_by=None,
        )
    )
    session = SessionRow(
        id=uuid.uuid4(),
        student_id=uuid.UUID(world.student_share_id),
        started_at=now_utc(),
        type="practice",
        active_ms=0,
        last_active_at=now_utc(),
        plan={},
    )
    db.add(session)
    db.flush()
    db.add(
        EventRow(
            session_id=session.id,
            item_id="ITEM.REPLAY",
            event_type="answer",
            payload={"response": "5"},
            correct=True,
            created_at=now_utc(),
            state_before="practice",
            state_after="explain_back",
            rule_id="R08",
        )
    )
    db.commit()
    ok = client.get(
        f"/admin/sessions/{session.id}/replay",
        headers=auth_header(world.admin_token),
    )
    assert ok.status_code == 200
    ev = ok.json()["events"][0]
    assert ev["item"]["id"] == "ITEM.REPLAY"
    assert ev["item"]["status"] == RETIRED_STATUS
    assert ev["item"]["stem_en"] == "Retired stem"
