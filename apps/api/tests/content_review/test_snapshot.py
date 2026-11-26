"""The build-time review snapshot: same items and hashes as the YAML, the rule for choosing it,
and the fallback. The module-scoped real-content test parses the whole content folder once (about
15 seconds); everything else uses a few tiny files."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from app.config import settings
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content_review import service, snapshot
from app.registries.paths import content_root as real_content_root
from tests.content.conftest import content_root, loc, minimal_item, write_yaml  # noqa: F401


@pytest.fixture(autouse=True)
def _fresh() -> None:
    service.clear_items_cache()
    settings.reviewer_desk_enabled = True


@pytest.fixture
def snap_file(content_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:  # noqa: F811
    path = tmp_path_factory.mktemp("snap") / "snap.json.gz"
    snapshot.write(path, snapshot.build(content_root))
    settings.review_snapshot_path = str(path)
    return path


# ---- the committed snapshot against the real content (parses all the YAML once) ----


@pytest.fixture(scope="module")
def real_yaml() -> snapshot.ReviewData:
    # a module-scoped fixture runs outside the per-test settings restore: put BOTH flags back as
    # they were, or the desk stays on for every test that runs after this module
    desk_before = settings.reviewer_desk_enabled
    snapshot_before = settings.review_snapshot_enabled
    settings.reviewer_desk_enabled = True
    settings.review_snapshot_enabled = False
    try:
        service.clear_items_cache()
        return service.load_review_data(real_content_root())
    finally:
        settings.reviewer_desk_enabled = desk_before
        settings.review_snapshot_enabled = snapshot_before
        service.clear_items_cache()


def test_the_committed_snapshot_is_up_to_date(real_yaml: snapshot.ReviewData) -> None:
    committed = snapshot.read(snapshot.SNAPSHOT_PATH)
    assert committed is not None, "run: PYTHONPATH=. python scripts/write_review_snapshot.py"
    hint = "content or Item schema changed: PYTHONPATH=. python scripts/write_review_snapshot.py"
    assert committed["source_signature"] == snapshot.source_signature(real_content_root()), hint
    assert committed["items"] == [
        i.model_dump(mode="json", by_alias=True) for i in real_yaml.items
    ], hint
    assert committed["labels"] == dict(sorted(real_yaml.labels.items())), hint
    assert committed["explanations"] == dict(sorted(real_yaml.explanations.items())), hint
    assert committed["item_chapter"] == dict(sorted(real_yaml.item_chapter.items())), hint
    assert committed["chapters"] == {
        k: real_yaml.chapters[k].as_dict() for k in sorted(real_yaml.chapters)
    }, hint


def test_every_item_has_the_identical_content_hash_from_the_snapshot_and_the_yaml(
    real_yaml: snapshot.ReviewData,
) -> None:
    committed = snapshot.read(snapshot.SNAPSHOT_PATH)
    assert committed is not None
    from_snapshot = snapshot.to_review_data(committed)
    assert len(from_snapshot.items) == len(real_yaml.items) > 1000
    assert [i.id for i in from_snapshot.items] == [i.id for i in real_yaml.items]
    for mine, theirs in zip(from_snapshot.items, real_yaml.items, strict=True):
        assert item_content_hash(mine) == item_content_hash(theirs), mine.id
        assert mine == theirs, mine.id
    assert from_snapshot.labels == real_yaml.labels
    assert from_snapshot.explanations == real_yaml.explanations
    assert from_snapshot.chapters == real_yaml.chapters
    assert from_snapshot.item_chapter == real_yaml.item_chapter


def test_snapshot_hindi_matches_what_the_yaml_card_would_show(
    real_yaml: snapshot.ReviewData,
) -> None:
    committed = snapshot.read(snapshot.SNAPSHOT_PATH)
    assert committed is not None
    hindi = committed["hindi"]
    for item in real_yaml.items[:5] + real_yaml.items[-5:]:
        want = service.hindi_texts(real_content_root(), item.id)
        assert hindi.get(item.id, {"stem": None, "options": {}}) == want, item.id


def test_every_real_item_maps_to_a_chapter(real_yaml: snapshot.ReviewData) -> None:
    assert snapshot.UNMAPPED_ID not in real_yaml.chapters
    grades = {c.grade for c in real_yaml.chapters.values()}
    assert grades == {10}  # no class 9, 11 or 12 content yet: nothing is invented
    assert {c.subject for c in real_yaml.chapters.values()} == {
        "maths",
        "physics",
        "biology",
        "chemistry",
    }


def test_the_snapshot_is_small() -> None:
    assert snapshot.SNAPSHOT_PATH.stat().st_size < 1_000_000


# ---- build and render ----


def test_the_build_is_deterministic(content_root: Path) -> None:  # noqa: F811
    first = snapshot.render(snapshot.build(content_root))
    second = snapshot.render(snapshot.build(content_root))
    assert first == second
    data = snapshot.build(content_root)
    assert [i["id"] for i in data["items"]] == sorted(i["id"] for i in data["items"])
    assert "created" not in str(data.keys())


def test_the_source_signature_ignores_line_endings_and_changes_with_content(
    content_root: Path,  # noqa: F811
) -> None:
    path = content_root / "items" / "p0.yaml"
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    path.write_bytes(raw)
    before = snapshot.source_signature(content_root)
    path.write_bytes(raw.replace(b"\n", b"\r\n"))
    assert snapshot.source_signature(content_root) == before
    path.write_bytes(raw.replace(b"Solve", b"Work out"))
    assert snapshot.source_signature(content_root) != before


# ---- choosing between the snapshot and the YAML ----


def test_a_matching_snapshot_is_used(content_root: Path, snap_file: Path) -> None:  # noqa: F811
    data = service.load_review_data(content_root)
    assert data.source == "snapshot"
    assert data.hindi is not None
    items, labels = service.load_items(content_root)
    assert [i.id for i in items][:2] == ["ITEM.D0", "ITEM.D1"]
    assert labels == {"MC.1": "Wrong inverse"}
    assert data.explanations == {"MC.1": "Undo by doing the opposite."}


def test_the_yaml_path_and_the_snapshot_path_give_the_same_wrong_options(
    content_root: Path,  # noqa: F811
    snap_file: Path,
) -> None:
    from_snapshot = service.load_review_data(content_root)
    assert from_snapshot.source == "snapshot"
    settings.review_snapshot_enabled = False
    service.clear_items_cache()
    from_yaml = service.load_review_data(content_root)
    assert from_yaml.source == "yaml"
    assert from_yaml.explanations == from_snapshot.explanations
    for mine, theirs in zip(from_snapshot.items, from_yaml.items, strict=True):
        assert service._wrong_options(
            mine, from_snapshot.labels, from_snapshot.explanations
        ) == service._wrong_options(theirs, from_yaml.labels, from_yaml.explanations)


def test_a_missing_explanation_adds_nothing_and_does_not_fail() -> None:
    item = minimal_item("ITEM.W", stem="Q")
    item.update(
        type="mcq",
        answer={"sympy": "yes", "accept": ["yes"]},
        options=[{"id": "yes", **loc("Yes")}, {"id": "no", **loc("No")}],
        misconception_rules=[{"id": "MC.1", "when_answer_equals": ["no"]}],
    )
    parsed = Item.model_validate(item)
    assert service._wrong_options(parsed, {"MC.1": "T"}, {})[0]["explanation"] == ""
    assert service._wrong_options(parsed, {"MC.1": "T"})[0]["explanation"] == ""


def _as_version_1(snap_file: Path) -> dict:
    new = json.loads(gzip.decompress(snap_file.read_bytes()))
    old = {k: v for k, v in new.items() if k != "explanations"}
    old["version"] = 1
    return old


def test_an_older_snapshot_is_stale_and_the_yaml_path_is_used(
    content_root: Path,  # noqa: F811
    snap_file: Path,
) -> None:
    old = _as_version_1(snap_file)
    snap_file.write_bytes(gzip.compress(json.dumps(old).encode("utf-8")))
    assert snapshot.read(snap_file) is None
    data = service.load_review_data(content_root)
    assert data.source == "yaml"
    assert data.explanations == {"MC.1": "Undo by doing the opposite."}


def test_item_hashes_equal_the_previous_snapshot_format(
    content_root: Path,  # noqa: F811
    snap_file: Path,
) -> None:
    """The format change touched the misconception data only: the same items load from a version 1
    payload and from the new one, with identical content hashes."""
    new = json.loads(gzip.decompress(snap_file.read_bytes()))
    old = _as_version_1(snap_file)
    old["explanations"] = {}  # to_review_data needs the key; the items are what is compared
    a = snapshot.to_review_data(new)
    b = snapshot.to_review_data(old)
    assert [item_content_hash(i) for i in a.items] == [item_content_hash(i) for i in b.items]


def test_a_stale_snapshot_is_ignored_when_the_yaml_is_there(
    content_root: Path,  # noqa: F811
    snap_file: Path,
) -> None:
    write_yaml(content_root / "items" / "new.yaml", minimal_item("ITEM.NEW"))
    data = service.load_review_data(content_root)
    assert data.source == "yaml"
    assert "ITEM.NEW" in {i.id for i in data.items}
    # edit an item the snapshot already holds: the hash must come from the file, not the snapshot
    path = content_root / "items" / "p1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("Find x", "Work out x"), "utf-8")
    again = service.load_review_data(content_root)
    assert again.source == "yaml"


def test_with_no_content_folder_the_snapshot_is_authoritative(
    content_root: Path,  # noqa: F811
    snap_file: Path,
    tmp_path: Path,
) -> None:
    yaml_items, _ = service.load_items(content_root)
    service.clear_items_cache()
    gone = tmp_path / "does-not-exist"
    data = service.load_review_data(gone)
    assert data.source == "snapshot"
    assert [item_content_hash(i) for i in data.items] == [item_content_hash(i) for i in yaml_items]


def test_no_snapshot_means_the_yaml_path_and_its_cache(
    content_root: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    settings.review_snapshot_path = str(tmp_path / "missing.json.gz")
    first = service.load_review_data(content_root)
    assert first.source == "yaml"
    assert service.load_review_data(content_root) is first  # PR 120 per-process cache
    # an unreadable or wrong-version file is the same as none
    bad = tmp_path / "bad.json.gz"
    bad.write_bytes(b"not gzip")
    settings.review_snapshot_path = str(bad)
    service.clear_items_cache()
    assert service.load_review_data(content_root).source == "yaml"
    assert service.load_review_data(tmp_path / "nowhere").items == []


def test_the_snapshot_is_not_used_with_the_desk_off_or_when_switched_off(
    content_root: Path,  # noqa: F811
    snap_file: Path,
) -> None:
    settings.reviewer_desk_enabled = False
    assert service.load_review_data(content_root).source == "yaml"
    settings.reviewer_desk_enabled = True
    settings.review_snapshot_enabled = False
    assert service.load_review_data(content_root).source == "yaml"


# ---- chapters ----


def test_chapters_come_from_the_curriculum_then_the_overlay_then_unmapped(
    content_root: Path,  # noqa: F811
) -> None:
    write_yaml(
        content_root / "curricula" / "c1" / "curriculum.yaml",
        {
            "id": "c1",
            "books": [
                {
                    "id": "c1.9.maths",
                    "grade": 9,
                    "subject": "maths",
                    "chapters": [
                        {"id": "c1.9.maths.lin", "overlay_id": "ov1", "titles": {"en": "Lines"}}
                    ],
                }
            ],
        },
    )
    write_yaml(content_root / "skills" / "s2.yaml", {**_skill("MATH.S2")})
    write_yaml(
        content_root / "overlays" / "ov2.yaml",
        {
            "id": "c1.10.science.heat",
            "curriculum_id": "c1",
            "grade": 10,
            "chapter": "heat_and_light",
            "skill_ids": ["MATH.S2"],
            "live": False,
        },
    )
    write_yaml(content_root / "items" / "s2.yaml", minimal_item("ITEM.S2", skill="MATH.S2"))
    write_yaml(content_root / "items" / "s3.yaml", minimal_item("ITEM.S3", skill="MATH.NONE"))
    data = service.load_review_data(content_root)
    assert data.item_chapter["ITEM.P0"] == "ov1"
    first = data.chapters["ov1"]
    assert (first.grade, first.subject, first.title, first.in_curriculum) == (
        9,
        "maths",
        "Lines",
        True,
    )
    second = data.chapters["c1.10.science.heat"]
    assert (second.grade, second.subject, second.title, second.in_curriculum) == (
        10,
        "science",
        "Heat and light",
        False,
    )
    assert data.item_chapter["ITEM.S3"] == snapshot.UNMAPPED_ID
    assert data.chapters[snapshot.UNMAPPED_ID].grade is None


def _skill(skill_id: str) -> dict:
    from tests.content.conftest import minimal_skill

    return minimal_skill(skill_id)
