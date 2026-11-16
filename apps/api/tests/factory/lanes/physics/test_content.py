"""Skill graph, misconceptions, overlays and template files for the physics lane."""

import yaml

from app.content import validator
from app.factory.lanes.physics.content import (
    PREREQS,
    SKILLS,
    misconception_docs,
    skill_docs,
    template_path,
    used_misconceptions,
    write_content,
)
from app.factory.lanes.physics.models import ALL_MODELS
from app.factory.lanes.physics.templates import TEMPLATES


def test_skill_counts_per_chapter_and_prerequisites_reach_class_8_9():
    electricity = [s for s, *_ in SKILLS if s.startswith("PHY.ELEC.")]
    light = [s for s, *_ in SKILLS if s.startswith("PHY.LIGHT.")]
    assert 8 <= len(electricity) <= 15 and 8 <= len(light) <= 15
    docs = {d["id"]: d for d in skill_docs()}
    low = {sid for sid, _, grades, _ in PREREQS}
    for sid in electricity + light:
        seen, stack = set(), [sid]
        while stack:
            cur = stack.pop()
            for p in docs[cur]["prerequisites"]:
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        assert seen & low, f"{sid} has no Class 8-9 prerequisite"
        assert docs[sid]["grade_band"] == [10] and docs[sid]["status"] == "draft"
    assert all(docs[p]["grade_band"] == [8, 9] for p in low)


def test_every_template_skill_is_in_the_graph_and_every_skill_has_a_template():
    ids = {s for s, *_ in SKILLS}
    assert {m.skill for m in ALL_MODELS.values()} == ids
    assert set(TEMPLATES) == set(ALL_MODELS)


def test_every_named_wrong_procedure_has_a_misconception_record():
    docs = {d["id"] for d in misconception_docs()}
    assert set(used_misconceptions()) == docs
    skills = {d["id"] for d in skill_docs()}
    for d in misconception_docs():
        assert d["remedial_skill"] in skills and d["status"] == "draft"


def test_content_validates_and_templates_are_factory_templates(tmp_path):
    counts = write_content(tmp_path)
    assert counts["skills"] == len(SKILLS) + len(PREREQS)
    report = validator.validate_path(tmp_path)
    assert not report.errors, report.errors[:3]
    for tpl in TEMPLATES.values():
        data = yaml.safe_load(template_path(tmp_path, tpl["id"]).read_text(encoding="utf-8"))
        assert data["schema"] == "factory-template/1" and data["lane"] == "physics"
        assert data["syllabus"]["grade"] == 10 and data["syllabus"]["chapter_ref"].startswith(
            "cbse.10.physics."
        )  # noqa: E501


def test_overlays_are_not_live(tmp_path):
    write_content(tmp_path)
    for path in (tmp_path / "overlays").glob("*.yaml"):
        assert yaml.safe_load(path.read_text(encoding="utf-8"))["live"] is False
