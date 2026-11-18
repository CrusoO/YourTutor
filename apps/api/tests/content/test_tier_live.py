"""A chapter whose items are all servable by tier counts as live under the serving gate."""

from types import SimpleNamespace

import pytest

from app.content import gate
from app.content.gate import overlay_is_live_for_serving, tier_live_gaps


def row(skill: str, pool: str, role: str, ok: bool = True) -> SimpleNamespace:
    return SimpleNamespace(primary_skill=skill, pool=pool, role=role, ok=ok)


@pytest.fixture(autouse=True)
def _gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "row_is_servable", lambda r, **_: r.ok)


def full(skill: str) -> list[SimpleNamespace]:
    rows = [row(skill, "practice", "procedure") for _ in range(2)]
    rows += [row(skill, "practice", role) for role in ("explain", "apply", "transfer")]
    return [*rows, row(skill, "diagnostic", "recall")]


def test_a_covered_chapter_has_no_gaps() -> None:
    assert tier_live_gaps(["S1"], full("S1"), allow_draft=False) == []


def test_missing_diagnostic_or_role_is_not_a_gap() -> None:
    rows = [r for r in full("S1") if r.pool != "diagnostic"]
    rows.append(row("S1", "practice", "procedure"))  # roles may be all alike
    assert tier_live_gaps(["S1"], rows, allow_draft=False) == []


def test_unservable_rows_do_not_count() -> None:
    rows = [row("S1", r.pool, r.role, ok=False) for r in full("S1")]
    assert len(tier_live_gaps(["S1"], rows, allow_draft=False)) == 1


def test_live_needs_the_owner_switch() -> None:
    rows = full("S1")
    kw = {"allow_draft": False}
    assert (
        overlay_is_live_for_serving(False, ["S1"], rows, serve_tier_a_unreviewed=False, **kw)
        is False
    )
    assert (
        overlay_is_live_for_serving(False, ["S1"], rows, serve_tier_a_unreviewed=True, **kw) is True
    )


def test_every_skill_must_be_covered_and_empty_overlay_is_never_live() -> None:
    rows = full("S1")
    assert not overlay_is_live_for_serving(
        False, ["S1", "S2"], rows, allow_draft=False, serve_tier_a_unreviewed=True
    )
    assert not overlay_is_live_for_serving(
        False, [], rows, allow_draft=False, serve_tier_a_unreviewed=True
    )


def test_flag_in_overlay_or_development_still_wins() -> None:
    assert overlay_is_live_for_serving(
        True, ["S1"], [], allow_draft=False, serve_tier_a_unreviewed=False
    )
    assert overlay_is_live_for_serving(
        False, ["S1"], [], allow_draft=True, serve_tier_a_unreviewed=False
    )


def test_chapters_use_the_tier_rule_only_with_the_owner_switch(db) -> None:  # type: ignore[no-untyped-def]
    from app.config import settings
    from app.db.models import OverlayRow
    from app.learner.chapters import _is_live

    class Items(list):  # a stand-in for the items query
        pass

    overlay = OverlayRow(
        id="OV.T", curriculum_id="cbse", grade=10, chapter="c", skill_ids=["S1"], live=False,
        section_map={},
    )  # fmt: skip
    settings.allow_draft_content = False
    settings.serve_tier_a_unreviewed = False
    assert _is_live(db, overlay) is False
    settings.serve_tier_a_unreviewed = True
    assert _is_live(db, overlay) is False  # no items loaded: nothing covers the skill
    overlay.live = True
    assert _is_live(db, overlay) is True
