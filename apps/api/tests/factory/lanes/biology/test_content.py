"""Skill graph, misconceptions, overlays and template files for the biology lane."""

import re

import yaml

from app.content import validator
from app.factory.lanes.biology.common import NO_BOARD_WORDS
from app.factory.lanes.biology.content import (
    PREREQS,
    _usage,
    misconception_docs,
    overlay_docs,
    skill_docs,
    template_path,
    used_misconceptions,
    write_content,
)
from app.factory.lanes.biology.models import ALL_MODELS, MISC
from app.factory.lanes.biology.templates import all_templates


def test_skill_counts_per_chapter_and_prerequisites_reach_class_8_9():
    docs = {d["id"]: d for d in skill_docs()}
    low = {sid for sid, _, _ in PREREQS}
    by_chapter: dict[str, list[str]] = {}
    for model in ALL_MODELS.values():
        by_chapter.setdefault(model.chapter, []).append(model.skill)
    assert {c: len(v) for c, v in by_chapter.items()} == {
        "cbse.10.biology.heredity": 9,
        "cbse.10.biology.environment": 4,
        "cbse.10.biology.reproduction": 3,
        "cbse.10.biology.life_processes": 2,
    }
    for skills in by_chapter.values():
        for sid in skills:
            seen, stack = set(), [sid]
            while stack:
                for p in docs[stack.pop()]["prerequisites"]:
                    if p not in seen:
                        seen.add(p)
                        stack.append(p)
            assert seen & low, f"{sid} has no Class 8-9 prerequisite"
            assert docs[sid]["grade_band"] == [10] and docs[sid]["status"] == "draft"
            assert docs[sid]["subject"] == "biology"
    assert all(docs[p]["grade_band"] == [8, 9] for p in low)


def test_every_template_skill_is_in_the_graph_and_every_skill_has_a_template():
    ids = {d["id"] for d in skill_docs() if d["grade_band"] == [10]}
    assert {m.skill for m in ALL_MODELS.values()} == ids
    assert set(all_templates()) == set(ALL_MODELS)


def test_every_named_wrong_procedure_has_a_record_and_every_used_one_is_declared():
    docs = {d["id"] for d in misconception_docs()}
    assert set(used_misconceptions()) == docs
    declared = {f"BIO.MC.{area}.{name}" for area, table in MISC.items() for name in table}
    # a wrong procedure that is a candidate but never among the three chosen has no record
    assert docs <= declared, f"used but undeclared: {sorted(docs - declared)}"
    skills = {d["id"] for d in skill_docs()}
    for d in misconception_docs():
        assert d["remedial_skill"] in skills and d["status"] == "draft"
    for sid, mcs in ((d["id"], d["misconceptions"]) for d in skill_docs()):
        assert set(mcs) <= docs
    assert _usage()


def test_no_board_or_publisher_names_in_student_text():
    texts = [d["title"]["en"] for d in skill_docs()]
    texts += [m["title"]["en"] + " " + m["explanation"]["en"] for m in misconception_docs()]
    pattern = re.compile("|".join(rf"\b{w}\b" for w in NO_BOARD_WORDS), re.I)
    assert not [t for t in texts if pattern.search(t)]


def test_content_validates_and_templates_are_factory_templates(tmp_path):
    counts = write_content(tmp_path)
    assert counts["skills"] == 27 and counts["templates"] == 18 and counts["overlays"] == 4
    report = validator.validate_path(tmp_path)
    assert not report.errors, report.errors[:3]
    for tpl in all_templates().values():
        data = yaml.safe_load(template_path(tmp_path, tpl["id"]).read_text(encoding="utf-8"))
        assert data["schema"] == "factory-template/1" and data["lane"] == "biology"
        assert data["syllabus"]["grade"] == 10
        assert data["syllabus"]["chapter_ref"].startswith("cbse.10.biology.")
        assert "free_text" in data["syllabus"]["forbidden_content"]


def test_overlays_are_not_live():
    docs = overlay_docs()
    assert len(docs) == 4
    for doc in docs:
        assert doc["live"] is False and doc["grade"] == 10 and doc["skill_ids"]
