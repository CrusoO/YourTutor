"""Authoring pipeline: schema, syllabus map, compile, lint, report and CLI. Pure and fast."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.authoring.__main__ import main
from app.authoring.compile import compile_draft, item_id, misconception_id, shuffled, skill_id
from app.authoring.files import read_draft
from app.authoring.hooks import NUMERIC_RECHECKS, Recheck
from app.authoring.lint import jaccard, lint_paths, near_duplicates, tokens
from app.authoring.report import build_report
from app.authoring.schema import DraftFile
from app.authoring.syllabus import SyllabusMap, duplicate_keys, load_map
from app.content.schema import Item, Misconception, Overlay, Skill
from app.content.validator import validate_path

FIXTURE = Path(__file__).parent / "fixtures" / "content"
BIO = "authoring/drafts/10/biology/heredity_and_evolution.yaml"
PHY = "authoring/drafts/9/physics/motion.yaml"


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(FIXTURE, target)
    return target


def _edit(root: Path, rel: str, change: Any) -> Path:
    path = root / rel
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _codes(root: Path, rel: str | None = None) -> set[str]:
    run = lint_paths(root, [root / rel] if rel else None)
    return {f.code for f in run.findings}


def _draft(root: Path, rel: str) -> DraftFile:
    draft, errors = read_draft(root / rel)
    assert draft is not None, errors
    return draft


# --- schema -------------------------------------------------------------------------------


def test_fixture_drafts_parse() -> None:
    for rel in (BIO, PHY):
        draft, errors = read_draft(FIXTURE / rel)
        assert errors == [] and draft is not None


def test_unknown_key_is_an_error(root: Path) -> None:
    path = _edit(root, BIO, lambda d: d["items"][0].update({"tier": "A"}))
    draft, errors = read_draft(path)
    assert draft is None and any("tier" in e for e in errors)


@pytest.mark.parametrize(
    "change",
    [
        lambda i: i.update({"wrong": i["wrong"][:2]}),
        lambda i: i.update({"hints": i["hints"][:2]}),
        lambda i: i.update({"difficulty": "extreme"}),
        lambda i: i.update({"unit": "m"}),
    ],
)
def test_structural_mistakes_fail_the_schema(root: Path, change: Any) -> None:
    path = _edit(root, BIO, lambda d: change(d["items"][0]))
    draft, errors = read_draft(path)
    assert draft is None and errors


# --- syllabus map -------------------------------------------------------------------------


def test_map_loads_and_rejects_duplicates(root: Path) -> None:
    smap = load_map(root, 10, "biology")
    assert smap.chapters[0].key == "heredity_and_evolution"
    raw = yaml.safe_load((root / "syllabus/cbse/10/biology.yaml").read_text(encoding="utf-8"))
    raw["chapters"][0]["topics"].append(dict(raw["chapters"][0]["topics"][0]))
    dup = SyllabusMap.model_validate(raw)
    assert any("duplicate topic key" in e for e in duplicate_keys(dup))
    raw["chapters"].append(dict(raw["chapters"][0]))
    assert any(
        "duplicate chapter key" in e for e in duplicate_keys(SyllabusMap.model_validate(raw))
    )


def test_missing_map_is_a_value_error(root: Path) -> None:
    with pytest.raises(ValueError, match="no syllabus map"):
        load_map(root, 12, "maths")


def test_real_syllabus_maps_have_unique_keys() -> None:
    real = Path(__file__).resolve().parents[4] / "content"
    maps = sorted((real / "syllabus" / "cbse").glob("*/*.yaml"))
    assert len(maps) == 16
    for path in maps:
        load_map(real, int(path.parent.name), path.stem)


# --- compile ------------------------------------------------------------------------------


def _compile_all(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for rel in (BIO, PHY):
        draft = _draft(root, rel)
        topics = {
            t.key: t
            for c in load_map(root, draft.class_, draft.subject).chapters
            if c.key == draft.chapter
            for t in c.topics
        }
        files.update(compile_draft(draft, topics).files)
    return files


def test_compile_is_byte_identical_twice(root: Path) -> None:
    assert _compile_all(root) == _compile_all(root)


def test_compiled_files_load_as_real_models(root: Path) -> None:
    files = _compile_all(root)
    kinds = Counter(rel.split("/")[3] for rel in files)
    assert kinds == {"items": 11, "skills": 2, "misconceptions": 18, "overlays": 2}
    for rel, text in files.items():
        data = yaml.safe_load(text)
        if "/items/authored/" in rel:
            item = Item.model_validate(data)
            assert item.tier is not None and item.tier.value == "C"
            assert item.status.value == "draft"
            assert item.verification is None  # only the factory may write one
            assert item.provenance is not None and item.provenance.original
            assert item.provenance.author == "model-draft"
            assert sorted(h.level for h in item.hints) == [1, 2, 3]
        elif "/skills/authored/" in rel:
            skill = Skill.model_validate(data)
            assert skill.bkt.p_guess == 0.25
        elif "/overlays/authored/" in rel:
            overlay = Overlay.model_validate(data)
            assert overlay.id.endswith(".authored") and overlay.live is False
            assert overlay.skill_ids and overlay.grade in (9, 10)
        else:
            assert Misconception.model_validate(data).id.startswith("MC.A.")


def test_item_shape_ids_and_diagram_note(root: Path) -> None:
    files = _compile_all(root)
    key = "cbse/10/biology/items/authored/heredity_and_evolution/variation_and_inheritance.03.yaml"
    data = yaml.safe_load(files[key])
    assert data["id"] == item_id(
        10, "biology", "heredity_and_evolution", "variation_and_inheritance", 3
    )
    assert data["skill_ids"] == [skill_id(10, "biology", "variation_and_inheritance")]
    assert data["diagram_note"].startswith("A field of plants")
    assert data["solution_steps"][-1]["en"] == f"The correct option is {data['answer']['sympy']}."
    assert {r["when_answer_equals"][0] for r in data["misconception_rules"]} == (
        {"a", "b", "c", "d"} - {data["answer"]["sympy"]}
    )
    numeric = yaml.safe_load(
        files["cbse/9/physics/items/authored/motion/speed_and_velocity.01.yaml"]
    )
    assert numeric["type"] == "numeric" and "options" not in numeric
    assert numeric["answer"]["sympy"] == "15"
    assert numeric["solution_steps"][-1]["en"] == "Answer = 15"


def test_shuffle_is_deterministic_and_unbiased() -> None:
    assert shuffled("x", ["a", "b", "c", "d"]) == shuffled("x", ["a", "b", "c", "d"])
    positions = Counter(
        shuffled(f"A.10.biology.c.t.{n:02d}", ["right", "w1", "w2", "w3"]).index("right")
        for n in range(400)
    )
    assert set(positions) == {0, 1, 2, 3}
    assert min(positions.values()) > 60  # about 100 each


def test_misconception_id_is_stable_and_normalised() -> None:
    a = misconception_id("SK.A.10.biology.t", "Thinks  X is Y")
    assert a == misconception_id("SK.A.10.biology.t", "thinks x is y")
    assert a != misconception_id("SK.A.10.biology.u", "thinks x is y")
    assert a.startswith("MC.A.") and len(a) == len("MC.A.") + 12


def test_topic_under_five_items_is_left_out(root: Path) -> None:
    draft = _draft(root, PHY)
    topics = {t.key: t for c in load_map(root, 9, "physics").chapters for t in c.topics}
    out = compile_draft(draft, topics)
    assert out.short_topics and "describing_motion" in out.short_topics[0]
    assert not any("describing_motion" in rel and "/items/" in rel for rel in out.files)
    skipped = compile_draft(draft, topics, skip={0})  # one numeric item failed lint
    assert skipped.items == 0 and len(skipped.short_topics) == 2


def test_compiled_set_passes_content_validate(root: Path) -> None:
    assert main(["compile", "--content-root", str(root)]) == 0
    report = validate_path(root)
    assert report.errors == []
    assert len(report.bundle.items) == 11  # type: ignore[union-attr]


def test_cli_compile_is_idempotent_and_cleans(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["compile", "--content-root", str(root), "--json"]) == 0
    before = {p: p.read_bytes() for p in (root / "cbse").rglob("*.yaml")}
    capsys.readouterr()
    assert main(["compile", "--content-root", str(root), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["files_changed"] == 0
    assert before == {p: p.read_bytes() for p in (root / "cbse").rglob("*.yaml")}
    stale = root / "cbse/10/biology/items/authored/old.yaml"
    stale.write_text("id: x\n", encoding="utf-8")
    assert main(["compile", "--content-root", str(root), "--clean", "--dry-run"]) == 0
    assert stale.exists()
    assert main(["compile", "--content-root", str(root), "--clean"]) == 0
    assert not stale.exists()


# --- lint ---------------------------------------------------------------------------------


def test_fixtures_lint_without_errors(root: Path) -> None:
    run = lint_paths(root)
    assert run.error_count == 0
    assert {f.code for f in run.findings} >= {"topic_count", "low_confidence"}
    assert "OK" in run.to_text() or "WARN" in run.to_text()


@pytest.mark.parametrize(
    ("code", "change"),
    [
        ("stem_length", lambda i: i.update({"stem": "Too short?"})),
        ("banned_name", lambda i: i.update({"stem": i["stem"] + " As in the textbook."})),
        ("banned_name", lambda i: i["wrong"][0].update({"mistake": "copies the Arihant guide"})),
        ("bad_phrase", lambda i: i["wrong"][0].update({"text": "All of the above"})),
        ("options_not_distinct", lambda i: i["wrong"][0].update({"text": i["correct"] + "."})),
        ("hint_leak", lambda i: i["hints"].__setitem__(2, "The answer is eye colour here.")),
        ("same_mistake", lambda i: i["wrong"][1].update({"mistake": i["wrong"][0]["mistake"]})),
        ("explanation_length", lambda i: i.update({"explanation": "One sentence only."})),
    ],
)
def test_mcq_lint_rules(root: Path, code: str, change: Any) -> None:
    _edit(root, BIO, lambda d: change(d["items"][0]))
    assert code in _codes(root, BIO)


def test_blocking_rules_exclude_the_item_from_compile(root: Path) -> None:
    _edit(root, BIO, lambda d: d["items"][0].update({"stem": "Too short?"}))
    run = lint_paths(root, [root / BIO])
    assert run.files[0].bad_items() == {0}
    assert main(["compile", "--content-root", str(root)]) == 1
    assert not (
        root
        / "cbse/10/biology/items/authored/heredity_and_evolution/variation_and_inheritance.01.yaml"
    ).exists()


@pytest.mark.parametrize(
    ("code", "change"),
    [
        ("numeric_parse", lambda i: i.update({"correct": "about 15"})),
        ("numeric_parse", lambda i: i.update({"correct": "1/4"})),
        ("numeric_precision", lambda i: i.update({"correct": "15.123"})),
        ("hint_leak", lambda i: i["hints"].__setitem__(0, "Expect a result near 15.0 km/h.")),
    ],
)
def test_numeric_lint_rules(root: Path, code: str, change: Any) -> None:
    _edit(root, PHY, lambda d: change(d["items"][0]))
    assert code in _codes(root, PHY)


def test_syllabus_rules(root: Path) -> None:
    _edit(root, BIO, lambda d: d["items"][0].update({"topic": "no_such_topic"}))
    assert "unknown_topic" in _codes(root, BIO)
    _edit(root, BIO, lambda d: d.update({"chapter": "other"}))
    assert {"unknown_chapter", "path_mismatch"} <= _codes(root, BIO)


def test_class_ten_computed_topic_is_refused(root: Path) -> None:
    _edit(root, BIO, lambda d: d["items"][0].update({"topic": "mendels_experiments"}))
    assert "computed_topic" in _codes(root, BIO)


def test_diagram_topics_need_diagram_notes(root: Path) -> None:
    def strip(d: dict[str, Any]) -> None:
        for item in d["items"]:
            item["diagram"] = None

    _edit(root, BIO, strip)
    assert "diagram_missing" in _codes(root, BIO)


def test_near_duplicate_stems(root: Path) -> None:
    _edit(
        root, BIO, lambda d: d["items"][1].update({"stem": d["items"][0]["stem"] + " Choose one."})
    )
    run = lint_paths(root, [root / BIO])
    found = [f for f in run.findings if f.code == "near_duplicate"]
    assert found and found[0].item == 1
    assert jaccard(tokens("a b c d"), tokens("a b c d")) == 1.0
    pairs = near_duplicates([("f", 0, "s", "one two three"), ("f", 1, "t", "one two three")])
    assert pairs == []  # different scopes are not compared


def test_formula_stems_that_differ_in_a_sign_or_number_are_not_duplicates() -> None:
    same_words = "Solve dy/dx {} with y(0) = 1. Find y(1), rounded to 3 decimal places."
    entries = [
        ("f", 0, "s", same_words.format("= 2y")),
        ("f", 1, "s", same_words.format("+ 2y = 0")),
        ("f", 2, "s", same_words.format("= 2y")),
    ]
    assert [(a, b) for a, b, _ in near_duplicates(entries)] == [(0, 2)]  # only the true copy


def test_validator_language_rules_are_applied_to_drafts(root: Path) -> None:
    def stem_with_brace(d: dict[str, Any]) -> None:
        d["items"][0]["stem"] = (
            "Which element of the set {x} belongs to the product with the set B?"
        )

    _edit(root, BIO, stem_with_brace)
    assert "language" in _codes(root, BIO)

    def doubled_word(d: dict[str, Any]) -> None:
        d["items"][0]["hints"][0] = "Time spent standing still still counts."

    _edit(root, BIO, doubled_word)
    assert "language" in _codes(root, BIO)


def test_a_stem_used_twice_across_classes_is_an_error(root: Path) -> None:
    stem = _draft(root, BIO).items[0].stem

    def copy_stem(d: dict[str, Any]) -> None:
        d["items"][0]["stem"] = stem

    _edit(root, PHY, copy_stem)
    run = lint_paths(root)
    assert any(f.code == "duplicate_stem" for f in run.findings)


def test_schema_error_reports_and_exit_code(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (root / "authoring/drafts/9/physics/motion.yaml").write_text("items: []\n", encoding="utf-8")
    assert main(["lint", "--content-root", str(root)]) == 1
    assert "schema" in capsys.readouterr().out


def test_lint_json_and_out_file(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "report.txt"
    assert main(["lint", "--content-root", str(root), "--json", "--out", str(out)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["errors"] == 0 and data["files"] == 2
    assert out.is_file()


def test_numeric_recheck_hook_is_unused_and_never_stamps(root: Path) -> None:
    assert NUMERIC_RECHECKS == []

    def disagree(*, stem: str, correct: str, unit: str) -> Recheck | None:
        return Recheck(agrees=False, method="test", detail=f"{correct} {unit}")

    run = lint_paths(root, [root / PHY], rechecks=[disagree])
    assert any(f.code == "numeric_recheck" and f.severity == "error" for f in run.findings)

    def agree(*, stem: str, correct: str, unit: str) -> Recheck | None:
        return Recheck(agrees=True, method="test")

    info = lint_paths(root, [root / PHY], rechecks=[agree])
    assert info.error_count == 0
    assert all("verification" not in text for text in _compile_all(root).values())


# --- report -------------------------------------------------------------------------------


def test_report_counts(root: Path) -> None:
    report = build_report(root).to_json()
    assert report["items"] == 12
    assert report["low_confidence"] == 1
    assert report["topics_complete"] == 1  # the biology topic has 6
    assert (
        "10/biology/heredity_and_evolution/mendels_experiments"
        not in report["topics_without_drafts"]
    )
    assert report["topics_with_drafts"] == 3
    text = build_report(root).to_text()
    assert "variation_and_inheritance: 6/6" in text and "computed topic" in text


def test_report_cli(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", "--content-root", str(root), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["target_per_topic"] == 6


def test_validator_checks_authored_hints_against_option_text(root: Path) -> None:
    """The option letter is not the answer for a shuffled draft: a hint that happens to contain
    the key letter as a word (the article "a") must not be called a leak."""
    assert main(["compile", "--content-root", str(root)]) == 0
    folder = root / "cbse/10/biology/items/authored/heredity_and_evolution"
    for path in sorted(folder.glob("variation_and_inheritance.*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        key = data["answer"]["sympy"]
        data["hints"][0]["en"] = f"Think about {key} different idea and compare the options."
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    errors = validate_path(root).errors
    assert not [e for e in errors if "leaks" in e]


def test_validator_accepts_chemistry_notation_in_authored_items(root: Path) -> None:
    """Chemistry notation like (aq) is not a template leftover in an authored item."""
    assert main(["compile", "--content-root", str(root)]) == 0
    folder = root / "cbse/10/biology/items/authored/heredity_and_evolution"
    for path in sorted(folder.glob("variation_and_inheritance.*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["stem"]["en"] = data["stem"]["en"] + " Think of NaCl (aq) in water."
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert not [e for e in validate_path(root).errors if "parenthesised" in e]
