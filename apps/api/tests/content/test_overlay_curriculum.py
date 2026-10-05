from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.content.loader import load_path
from app.content.schema import Overlay
from app.content.validator import curricula_for, load_bundle, validate_bundle
from app.db.models import OverlayRow
from app.db.session import session_factory
from app.registries.paths import repo_root

CONTENT = repo_root() / "content"
OVERLAY = {
    "id": "ov",
    "curriculum_id": "bhutan",
    "grade": 9,
    "chapter": "linear_equations",
    "skill_ids": ["MATH.S1"],
    "live": False,
}


def test_overlay_declares_a_curriculum_id() -> None:
    overlay = Overlay.model_validate(OVERLAY)
    assert overlay.curriculum_id == "bhutan"
    assert not hasattr(overlay, "board")


def test_overlay_requires_curriculum_id() -> None:
    data = {key: value for key, value in OVERLAY.items() if key != "curriculum_id"}
    with pytest.raises(ValidationError, match="curriculum_id"):
        Overlay.model_validate(data)


def test_old_board_field_is_rejected_loudly() -> None:
    with pytest.raises(ValidationError, match="board"):
        Overlay.model_validate({**OVERLAY, "board": "bhutan"})


def test_seed_overlay_files_use_curriculum_id_not_board() -> None:
    files = sorted((CONTENT / "overlays").glob("*.yaml")) + sorted(
        (CONTENT / "e2e_mini" / "overlays").glob("*.yaml")
    )
    assert len(files) >= 3
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "board" not in data, path.name
        assert data["curriculum_id"] in {"bhutan", "seba"}, path.name


def test_unknown_curriculum_id_is_a_validation_error() -> None:
    bundle = load_bundle(CONTENT)
    bundle.overlays[0].curriculum_id = "no_such_curriculum"
    report = validate_bundle(bundle, curricula_for(CONTENT))
    assert any("no_such_curriculum" in error for error in report.errors)


def test_known_curriculum_ids_pass_validation() -> None:
    report = validate_bundle(load_bundle(CONTENT), curricula_for(CONTENT))
    assert not [e for e in report.errors if "curriculum" in e]


def test_loader_persists_curriculum_id_on_overlay_rows(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'overlay.db'}"
    load_path(CONTENT, database_url=url)
    with session_factory(url)() as session:
        row = session.get(OverlayRow, "seba_class9")
        assert row is not None
        assert row.curriculum_id == "seba"
        assert not hasattr(row, "board")
