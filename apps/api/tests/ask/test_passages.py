"""G7 step 1: passages load only with an allowed licence, mapped to a real section."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ask.embed import DIM, cosine, default_embedder
from app.ask.load import upsert_passages, validate_passages
from app.ask.passages import ALLOWED_LICENCES, load_passages
from app.db.models import PassageRow
from app.lessons.sources import approved_source_ids
from app.registries.loaders import load_all_curricula
from app.registries.paths import content_root

SKILLS = {"MATH.ALG.INVERSE_OPERATIONS"}
GOOD = {
    "id": "PSG.T.1",
    "chapter_id": "bhutan_class9",
    "section_key": "s1",
    "skill_ids": ["MATH.ALG.INVERSE_OPERATIONS"],
    "source_type": "authored_notes",
    "licence_status": "owned",
    "source_ref": "NOTE.ALG.INVERSE",
    "text": "An inverse operation undoes another operation.",
}


def _errors(tmp_path: Path, *rows: dict) -> list[str]:
    folder = tmp_path / "passages"
    folder.mkdir(exist_ok=True)
    (folder / "t.yaml").write_text(yaml.safe_dump({"passages": list(rows)}), encoding="utf-8")
    return validate_passages(
        tmp_path, load_all_curricula(), SKILLS, approved_source_ids(content_root())
    )


def test_a_good_passage_validates(tmp_path: Path) -> None:
    assert _errors(tmp_path, GOOD) == []


@pytest.mark.parametrize("licence", ["unknown", "all_rights_reserved", "", "pending"])
def test_a_passage_with_a_licence_that_is_not_allowed_is_refused(
    tmp_path: Path, licence: str
) -> None:
    errors = _errors(tmp_path, {**GOOD, "licence_status": licence})
    assert any("licence.refused" in e for e in errors), errors


def test_the_allowed_licences_are_exactly_the_three_in_the_architecture() -> None:
    assert ALLOWED_LICENCES == {"owned", "licensed", "open_licence_compatible"}


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"chapter_id": "nowhere"}, "chapter.unknown"),
        ({"section_key": "s99"}, "section.unknown"),
        ({"skill_ids": ["MATH.NOPE"]}, "skill.unknown"),
        ({"locale": "xx"}, "locale.unknown"),
        ({"source_ref": "NOTE.MADE.UP"}, "source.unknown"),
        ({"source_type": "scraped_web"}, "source_type.unknown"),
        ({"status": "live"}, "status.unknown"),
    ],
)
def test_a_passage_must_name_a_real_chapter_section_skill_locale_and_source(
    tmp_path: Path, change: dict, code: str
) -> None:
    errors = _errors(tmp_path, {**GOOD, **change})
    assert any(code in e for e in errors), errors


def test_licensed_textbook_text_needs_a_reviewer_and_an_edition(tmp_path: Path) -> None:
    book = {**GOOD, "source_type": "licensed_textbook", "licence_status": "licensed"}
    assert any("reviewer" in e for e in _errors(tmp_path, book))
    ok = {**book, "reviewer": "R. Sharma", "edition_year": 2023}
    assert _errors(tmp_path, ok) == []


def test_duplicate_ids_and_unknown_fields_are_refused(tmp_path: Path) -> None:
    assert any("duplicate" in e for e in _errors(tmp_path, GOOD, GOOD))
    assert any("schema.invalid" in e for e in _errors(tmp_path, {**GOOD, "url": "x"}))


def test_the_content_hash_follows_the_text() -> None:
    root = content_root()
    first = load_passages(root)[0]
    changed = first.model_copy(update={"text": first.text + " More."})
    assert first.content_hash != changed.content_hash and len(first.content_hash) == 64


def test_shipped_passages_are_valid_draft_and_cover_every_live_skill(tmp_path: Path) -> None:
    root = content_root()
    passages = load_passages(root)
    assert passages and all(p.status == "draft" for p in passages)
    skills = {s for p in passages for s in p.skill_ids}
    expected = {p.stem for p in (root / "skills" / "math").glob("*.yaml")}
    assert len(skills) >= len(expected)  # one skill per file


def test_loading_stores_section_book_hash_and_an_embedding(db: Session) -> None:
    n = upsert_passages(db, content_root(), load_all_curricula())
    db.flush()
    rows = db.scalars(select(PassageRow)).all()
    assert n == len(rows) > 0
    row = next(r for r in rows if r.id == "PSG.LIN1.ONE_STEP.1")
    assert row.section_id == "bhutan_class9.s1" and row.book_id == "bhutan_class9"
    assert row.curriculum_id == "bhutan" and len(row.embedding) == DIM
    assert len(row.content_hash) == 64 and row.licence_status == "owned"


def test_the_embedder_is_deterministic_and_ranks_shared_wording_higher() -> None:
    e = default_embedder()
    assert e.embed("subtract 4 from both sides") == e.embed("subtract 4 from both sides")
    q = e.embed("how do I undo adding 5")
    near = e.embed("To undo adding 5, subtract 5.")
    far = e.embed("A word problem needs a story and a letter.")
    assert cosine(q, near) > cosine(q, far)
    assert abs(cosine(q, q) - 1.0) < 1e-9 and e.embed("") == [0.0] * DIM
