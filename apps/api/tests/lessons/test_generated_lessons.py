"""Owner-default rule: a worked-example lesson generated from verified solution traces, with
once-reviewed wording, is servable under the calculation-checked tier. Anything else still needs
approved status."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from app.config import settings
from app.lessons import generated
from app.lessons.loader import lesson_errors, servable
from app.lessons.schema import Lesson
from tests.legacy_content import LEGACY_CONTENT_ROOT

SEED = yaml.safe_load(
    (LEGACY_CONTENT_ROOT / "lessons" / "two_step_balancing.yaml").read_text(encoding="utf-8")
)
REAL_BACKED = generated.backed_item_ids
GEN = {
    "kind": "worked_example_trace",
    "trace_item_ids": ["ITM.A", "ITM.B"],
    "wording_template_id": "WORDING.WORKED.1",
    "wording_reviewed_by": "owner",
}


def lesson(**over: object) -> Lesson:
    data = copy.deepcopy(SEED)
    data["beats"] = [b for b in data["beats"] if b["kind"] != "explore"]
    data["generated"] = {**GEN, **over}
    return Lesson.model_validate(data)


@pytest.fixture(autouse=True)
def _backed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        generated, "backed_item_ids", lambda root=None: frozenset({"ITM.A", "ITM.B"})
    )
    settings.allow_draft_content = False
    settings.serve_tier_a_unreviewed = True


def test_generated_lesson_with_backed_trace_and_reviewed_wording_is_servable() -> None:
    assert servable(lesson()) is True


def test_a_plain_draft_lesson_is_not_servable() -> None:
    plain = Lesson.model_validate(SEED)
    assert servable(plain) is False


def test_the_owner_switch_off_means_not_servable() -> None:
    settings.serve_tier_a_unreviewed = False
    assert servable(lesson()) is False


def test_wording_must_have_been_reviewed() -> None:
    assert servable(lesson(wording_reviewed_by="")) is False
    assert servable(lesson(wording_reviewed_by="   ")) is False


def test_every_trace_item_must_be_backed() -> None:
    assert servable(lesson(trace_item_ids=["ITM.A", "ITM.X"])) is False


def test_a_hand_built_widget_lesson_is_never_generated() -> None:
    data = copy.deepcopy(SEED)
    data["generated"] = GEN
    assert any(b["kind"] == "explore" for b in data["beats"])
    assert servable(Lesson.model_validate(data)) is False


def test_approved_still_serves_without_any_trace() -> None:
    approved = Lesson.model_validate({**SEED, "status": "approved"})
    assert servable(approved) is True


def test_the_trace_must_belong_to_the_lessons_skill(tmp_path: Path) -> None:
    data = copy.deepcopy(SEED)
    data["generated"] = GEN
    (tmp_path / "lessons").mkdir()
    (tmp_path / "lessons" / "g.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    errors = lesson_errors(
        tmp_path, {data["skill_id"]}, item_skills={"ITM.A": data["skill_id"], "ITM.B": "OTHER"}
    )
    assert any("ITM.B" in e and "trace" in e for e in errors)
    errors = lesson_errors(tmp_path, {data["skill_id"]}, item_skills={"ITM.A": data["skill_id"]})
    assert any("ITM.B" in e and "unknown" in e for e in errors)


def test_backed_ids_come_from_the_ledger_and_item_files(tmp_path: Path) -> None:
    from tests.content.factory_fixture import build_factory_root

    root, _subject = build_factory_root(tmp_path, count=3)
    generated._CACHE.clear()
    ids = REAL_BACKED(root)
    assert len(ids) == 3 and all(i.startswith("TPL2.MATHS") for i in ids)
    for path in (root / "cbse" / "10" / "maths" / "items" / "factory" / "maths").glob("*.yaml"):
        path.write_text(
            path.read_text(encoding="utf-8").replace("Solve", "Resolve"), encoding="utf-8"
        )
    generated._CACHE.clear()
    assert REAL_BACKED(root) == frozenset()  # edited after the stamp: not backed
