"""`content validate` and `content load` read factory content in <board>/<class>/<subject>."""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import func, select

from app.content.factory_roots import content_roots, factory_template_ids, subject_roots
from app.content.loader import load_path
from app.content.templates import load_templates
from app.content.validator import load_bundle, validate_path
from app.db.models import ItemRow, MisconceptionRow, OverlayRow, SkillRow
from app.db.session import session_factory
from tests.content.factory_fixture import OVERLAY, SKILL, build_factory_root, item_files


def _skeleton(tmp_path: Path) -> Path:
    root = tmp_path / "skeleton"
    for name in ("items", "lessons", "overlays", "passages", "skills", "templates"):
        folder = root / "cbse" / "10" / "maths" / name
        folder.mkdir(parents=True)
        (folder / ".gitkeep").write_text("", encoding="utf-8")
    return root


def test_a_root_with_no_factory_content_is_unchanged(tmp_path: Path):
    root = _skeleton(tmp_path)
    assert subject_roots(root) and content_roots(root)[0] == root
    report = validate_path(root)
    assert report.errors == [] and report.warnings == []
    assert report.bundle is not None and report.bundle.items == [] and report.bundle.skills == []
    url = f"sqlite:///{tmp_path / 'skeleton.db'}"
    assert load_path(root, database_url=url).ok


def test_validate_reads_factory_content_and_does_not_demand_a_legacy_template(tmp_path: Path):
    root, subject = build_factory_root(tmp_path, count=6)
    bundle = load_bundle(root)
    assert len(bundle.items) == 6 and len(bundle.skills) == 1 and len(bundle.overlays) == 1
    assert len(bundle.misconceptions) == 3 and bundle.templates == []
    report = validate_path(root)
    assert not any("unknown template" in e for e in report.errors)
    assert report.errors == [], report.errors
    # certified items are not queued for a teacher's stem check; the factory template is noted
    assert report.needs_teacher_check == [] and report.manual_review == []
    assert any("factory-template/1 files are not validated" in w for w in report.warnings)
    assert {i.id for i in bundle.items} == {
        yaml.safe_load(p.read_text(encoding="utf-8"))["id"] for p in item_files(subject)
    }
    assert not any("wrong options name no misconception" in w for w in report.warnings)


def test_a_factory_template_in_the_legacy_templates_folder_is_not_parsed_as_legacy(tmp_path: Path):
    root, subject = build_factory_root(tmp_path, count=6)
    src = subject / "factory" / "templates" / "TPL2.MATHS.QUAD.INT_ROOTS.yaml"
    legacy_folder = subject / "templates"
    legacy_folder.mkdir()
    (legacy_folder / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    assert load_templates(subject) == []  # skipped, not a validation failure
    assert factory_template_ids(root) == {"TPL2.MATHS.QUAD.INT_ROOTS"}


def test_a_factory_item_naming_a_missing_template_file_warns(tmp_path: Path):
    root, subject = build_factory_root(tmp_path, count=6)
    (subject / "factory" / "templates" / "TPL2.MATHS.QUAD.INT_ROOTS.yaml").unlink()
    report = validate_path(root)
    assert report.errors == []
    assert any("no factory-template/1 file" in w for w in report.warnings)


def test_a_hand_edited_item_is_not_certified_and_is_flagged_for_a_teacher(tmp_path: Path):
    root, subject = build_factory_root(tmp_path, count=6)
    path = item_files(subject)[0]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["options"][0]["en"] = "edited after the stamp"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    report = validate_path(root)
    assert report.needs_teacher_check == [data["id"]]  # stamp no longer backs it


def test_a_broken_subject_ledger_is_an_error(tmp_path: Path):
    root, subject = build_factory_root(tmp_path, count=6)
    ledger = subject / "factory" / "ledger.jsonl"
    ledger.write_text(ledger.read_text().replace('"kind":"stamped"', '"kind":"suspended"'))
    report = validate_path(root)
    assert any(e.startswith("factory ledger:") and "cbse/10/maths" in e for e in report.errors)


def test_load_stores_tier_rules_and_overlay_and_is_idempotent(tmp_path: Path):
    root, _ = build_factory_root(tmp_path, count=6)
    url = f"sqlite:///{tmp_path / 'load.db'}"
    for _ in range(2):  # a second load changes nothing and does not fail
        report = load_path(root, database_url=url)
        assert report.ok
        with session_factory(url)() as db:
            rows = db.scalars(select(ItemRow)).all()
            assert len(rows) == 6 and all(r.tier == "A" and r.verification for r in rows)
            assert all(r.misconception_rules for r in rows)
            assert db.scalar(select(func.count()).select_from(SkillRow)) == 1
            assert db.scalar(select(func.count()).select_from(MisconceptionRow)) == 3
            overlay = db.get(OverlayRow, OVERLAY)
            assert overlay is not None and overlay.skill_ids == [SKILL] and overlay.live is False


def test_a_suspension_in_the_subject_ledger_is_applied_on_load(tmp_path: Path):
    from app.content.ledger import Ledger

    root, subject = build_factory_root(tmp_path, count=6)
    victim = yaml.safe_load(item_files(subject)[0].read_text(encoding="utf-8"))["id"]
    Ledger(subject / "factory" / "ledger.jsonl").append(
        "suspended", victim, "h", {"reason": "audit"}, ts="2026-11-16T00:00:00+00:00"
    )
    url = f"sqlite:///{tmp_path / 'sus.db'}"
    load_path(root, database_url=url)
    with session_factory(url)() as db:
        row = db.get(ItemRow, victim)
        assert row is not None and row.suspended_at is not None
