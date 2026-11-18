"""Matched checkpoint forms are built from stamped checkpoint items, never typed by hand."""

from pathlib import Path

import yaml

from app.content.schema import CheckpointForms
from app.content.validator import load_bundle
from app.factory.forms import build_forms


def _item(
    root: Path, item_id: str, skill: str, difficulty: float, pool: str = "checkpoint"
) -> None:
    path = root / "items" / "factory" / "x" / f"{item_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"id": item_id, "skill_ids": [skill], "difficulty": difficulty, "pool": pool,
            "verification": {"schema": "vrec/1"}}  # fmt: skip
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _overlay(root: Path, skills: list[str]) -> None:
    path = root / "overlays" / "o.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"id": "cbse.10.maths.ap", "skill_ids": skills}), encoding="utf-8"
    )


def test_pairs_are_same_skill_adjacent_difficulty_and_forms_are_disjoint(tmp_path: Path) -> None:
    skills = [f"S{i}" for i in range(6)]
    _overlay(tmp_path, skills)
    for s in skills:
        for k, d in enumerate((0.2, 0.25, 0.6, 0.65)):
            _item(tmp_path, f"{s}.{k}", s, d)
    _item(tmp_path, "P.1", "S0", 0.3, pool="practice")  # not a checkpoint item
    forms = build_forms(tmp_path, minimum=10)
    assert len(forms) == 1
    form = forms[0]
    assert len(form["A"]) == len(form["B"]) >= 10
    assert not set(form["A"]) & set(form["B"]) and "P.1" not in form["A"] + form["B"]
    assert set(form["match_map"]) == set(form["A"])
    by_id = {p.stem: yaml.safe_load(p.read_text()) for p in (tmp_path / "items").rglob("*.yaml")}
    for a, b in form["match_map"].items():
        assert by_id[a]["skill_ids"] == by_id[b]["skill_ids"]
        assert abs(by_id[a]["difficulty"] - by_id[b]["difficulty"]) <= 0.1
    CheckpointForms.model_validate(form)


def test_a_chapter_without_enough_pairs_gets_no_form(tmp_path: Path) -> None:
    _overlay(tmp_path, ["S0"])
    for k in range(4):
        _item(tmp_path, f"S0.{k}", "S0", 0.2 + k / 100)
    assert build_forms(tmp_path, minimum=10) == []


def test_forms_in_a_subject_folder_are_loaded_by_the_bundle(tmp_path: Path) -> None:
    subject = tmp_path / "cbse" / "10" / "maths"
    (subject / "skills").mkdir(parents=True)
    (subject / "checkpoints").mkdir()
    (subject / "checkpoints" / "f.yaml").write_text(
        yaml.safe_dump({"id": "F", "checkpoint_id": "CP", "A": ["a"], "B": ["b"],
                        "match_map": {"a": "b"}}),
        encoding="utf-8",
    )  # fmt: skip
    assert [f.id for f in load_bundle(tmp_path).checkpoint_forms] == ["F"]


def test_forms_command_writes_a_loadable_file(tmp_path: Path) -> None:
    from app.factory.cli import main

    skills = [f"S{i}" for i in range(6)]
    _overlay(tmp_path, skills)
    for s in skills:
        for k, d in enumerate((0.2, 0.25, 0.6, 0.65)):
            _item(tmp_path, f"{s}.{k}", s, d)
    assert main(["--root", str(tmp_path), "forms"]) == 0
    written = list((tmp_path / "checkpoints").glob("*.yaml"))
    assert [p.name for p in written] == ["cp.cbse.10.maths.ap.yaml"]
    CheckpointForms.model_validate(yaml.safe_load(written[0].read_text(encoding="utf-8")))
