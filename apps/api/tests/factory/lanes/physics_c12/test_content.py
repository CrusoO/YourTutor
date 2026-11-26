"""Skill graph, misconceptions, overlays, templates and the curriculum entry of the lane."""

import yaml

from app.content import validator
from app.factory.lanes.physics_c12.content import (
    PREREQS,
    curriculum_entry,
    misconception_docs,
    skill_docs,
    template_path,
    used_misconceptions,
    write_content,
)
from app.factory.lanes.physics_c12.kit import CHAPTERS, chapter_id
from app.factory.lanes.physics_c12.models import ALL_MODELS
from app.factory.lanes.physics_c12.templates import TEMPLATES


def test_every_model_has_one_skill_and_prerequisites_reach_lower_classes():
    docs = {d["id"]: d for d in skill_docs()}
    assert {m.skill for m in ALL_MODELS.values()} <= set(docs)
    low = {sid for sid, _, _ in PREREQS}
    for model in ALL_MODELS.values():
        seen, stack = set(), [model.skill]
        while stack:
            for p in docs[stack.pop()]["prerequisites"]:
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        assert seen & low, f"{model.skill} has no earlier-class prerequisite"
        assert docs[model.skill]["grade_band"] == [12] and docs[model.skill]["status"] == "draft"


def test_every_named_wrong_procedure_has_a_misconception_record():
    docs = {d["id"] for d in misconception_docs()}
    assert set(used_misconceptions()) == docs
    skills = {d["id"] for d in skill_docs()}
    for d in misconception_docs():
        assert d["remedial_skill"] in skills and d["status"] == "draft"
        assert d["title"]["en"] and d["explanation"]["en"].startswith("You")


def test_content_validates_and_templates_are_factory_templates(tmp_path):
    counts = write_content(tmp_path)
    assert counts["skills"] == len(PREREQS) + len(ALL_MODELS) and counts["overlays"] == 14
    report = validator.validate_path(tmp_path)
    assert not report.errors, report.errors[:3]
    for tpl in TEMPLATES.values():
        data = yaml.safe_load(template_path(tmp_path, tpl["id"]).read_text(encoding="utf-8"))
        assert data["schema"] == "factory-template/1" and data["lane"] == "physics_c12"
        assert data["syllabus"]["grade"] == 12
        assert data["syllabus"]["chapter_ref"].startswith("cbse.12.physics.")


def test_overlays_are_not_live_and_list_their_skills(tmp_path):
    write_content(tmp_path)
    seen = set()
    for path in (tmp_path / "overlays").glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["live"] is False and data["grade"] == 12 and data["skill_ids"]
        seen |= set(data["skill_ids"])
    assert seen == {m.skill for m in ALL_MODELS.values()}


def test_curriculum_entry_lists_every_chapter_once():
    entry = yaml.safe_load(curriculum_entry())[0]
    assert entry["id"] == "cbse.12.physics" and entry["grade"] == 12
    assert [c["id"] for c in entry["chapters"]] == [chapter_id(a) for a in CHAPTERS]
    assert entry["default_chapter_id"] == entry["chapters"][0]["id"]
