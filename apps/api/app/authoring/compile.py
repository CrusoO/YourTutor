"""Deterministic compile: draft file -> Item, Skill and Misconception YAML at tier C, draft.

The same input always gives byte-identical output. Nothing here writes a verification record, and
the items are never labelled machine-checked: they are model-drafted and wait for a person.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.authoring.files import dump_yaml, write_if_changed
from app.authoring.schema import DraftFile, DraftItem
from app.authoring.syllabus import MapTopic

AUTHOR = "model-draft"
DIFFICULTY = {"easy": 0.2, "medium": 0.6, "hard": 0.9}
# Same defaults as the existing maths skills (content/cbse/10/maths/skills/...).
BKT = {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25}
SKILL_SUBJECT = {
    "maths": "math",
    "physics": "physics",
    "chemistry": "chemistry",
    "biology": "biology",
}
PREDICTION = "Before you work it out, what do you think the answer will be, and why?"
OPTION_IDS = ("a", "b", "c", "d")
# `content validate` needs at least 5 distinct practice stems per skill; a topic with fewer
# compiled items is left out (and reported) rather than failing validation for everyone.
MIN_ITEMS_PER_TOPIC = 5
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_SPACE = re.compile(r"\s+")


def skill_id(grade: int, subject: str, topic: str) -> str:
    return f"SK.A.{grade}.{subject}.{topic}"


def item_id(grade: int, subject: str, chapter: str, topic: str, number: int) -> str:
    return f"A.{grade}.{subject}.{chapter}.{topic}.{number:02d}"


def norm_phrase(text: str) -> str:
    return _SPACE.sub(" ", text.strip().lower())


def misconception_id(topic_skill: str, mistake: str) -> str:
    """Stable id: hash of the topic skill and the normalised phrase (so the same words under two
    topics stay two records, each pointing at its own remedial skill)."""
    digest = hashlib.sha256(f"{topic_skill}|{norm_phrase(mistake)}".encode()).hexdigest()
    return f"MC.A.{digest[:12].upper()}"


def shuffled(item_key: str, texts: list[str]) -> list[str]:
    """Deterministic order from a hash of the item id and each option: the correct answer lands
    in every position about equally often, with no pattern an author could drift into."""
    return sorted(texts, key=lambda t: hashlib.sha256(f"{item_key}|{t}".encode()).hexdigest())


def steps_from(explanation: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE.split(explanation.strip()) if p.strip()]
    return parts or [explanation.strip()]


def _sentence_case(text: str) -> str:
    text = text.strip().rstrip(".")
    return text[:1].lower() + text[1:] if text else text


def _title(text: str) -> str:
    text = text.strip().rstrip(".")
    text = text[:1].upper() + text[1:]
    return text if len(text) <= 90 else text[:87].rstrip() + "..."


def _merge_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One rule per misconception id (two options may share an idea); options merge."""
    merged: dict[str, dict[str, Any]] = {}
    for rule in rules:
        if rule["id"] in merged:
            merged[rule["id"]]["when_answer_equals"] = sorted(
                {*merged[rule["id"]]["when_answer_equals"], *rule["when_answer_equals"]}
            )
        else:
            merged[rule["id"]] = rule
    return list(merged.values())


def compile_item(
    draft: DraftFile, item: DraftItem, number: int
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """One draft item -> (Item dict, {misconception id: Misconception dict})."""
    sid = skill_id(draft.class_, draft.subject, item.topic)
    iid = item_id(draft.class_, draft.subject, draft.chapter, item.topic, number)
    out: dict[str, Any] = {
        "id": iid,
        "skill_ids": [sid],
        "difficulty": DIFFICULTY[item.difficulty],
        "pool": "practice",
        "role": item.role,
        "stem": {"en": item.stem.strip()},
        "hints": [{"level": i + 1, "en": h.strip()} for i, h in enumerate(item.hints)],
        "prediction_prompt": {"en": PREDICTION},
        "status": "draft",
        "provenance": {"original": True, "author": AUTHOR},
        "type": item.type,
    }
    misconceptions: dict[str, dict[str, Any]] = {}
    steps = steps_from(item.explanation)
    if item.type == "mcq":
        correct = item.correct.strip()
        texts = [correct, *(w.text.strip() for w in item.wrong)]
        ordered = shuffled(iid, texts)
        out["options"] = [{"id": OPTION_IDS[i], "en": t} for i, t in enumerate(ordered)]
        key = OPTION_IDS[ordered.index(correct)]
        out["answer"] = {"sympy": key, "accept": []}
        rules = []
        for wrong in item.wrong:
            mid = misconception_id(sid, wrong.mistake)
            letter = OPTION_IDS[ordered.index(wrong.text.strip())]
            rules.append({"id": mid, "when_answer_equals": [letter]})
            misconceptions[mid] = {
                "id": mid,
                "title": {"en": _title(wrong.mistake)},
                "explanation": {"en": f"A common wrong idea: {_sentence_case(wrong.mistake)}."},
                "remedial_skill": sid,
                "status": "draft",
            }
        out["misconception_rules"] = _merge_rules(rules)
        steps.append(f"The correct option is {key}.")
    else:
        answer = item.correct.strip()
        out["answer"] = {"sympy": answer, "accept": []}
        if item.unit.strip():
            steps.append(f"The unit of the answer is {item.unit.strip()}.")
        steps.append(f"Answer = {answer}")  # the content validator wants an equation-like end
    out["solution_steps"] = [{"en": s} for s in steps]
    out["tier"] = "C"
    if item.diagram:
        out["diagram_note"] = item.diagram.strip()
    return out, misconceptions


def compile_skill(
    draft: DraftFile, topic: MapTopic, misconception_ids: list[str]
) -> dict[str, Any]:
    return {
        "id": skill_id(draft.class_, draft.subject, topic.key),
        "title": {"en": topic.title},
        "grade_band": [draft.class_],
        "subject": SKILL_SUBJECT[draft.subject],
        "prerequisites": [],
        "related": [],
        "misconceptions": sorted(misconception_ids),
        "bkt": dict(BKT),
        "status": "draft",
    }


@dataclass
class Compiled:
    """Everything one draft file compiles to: path relative to the content root -> YAML text."""

    files: dict[str, str] = field(default_factory=dict)
    items: int = 0
    skills: int = 0
    misconceptions: int = 0
    short_topics: list[str] = field(default_factory=list)


def compile_draft(
    draft: DraftFile, topics: dict[str, MapTopic], skip: set[int] | None = None
) -> Compiled:
    """Compile a validated draft file. `skip` holds 0-based item positions left out (they failed
    lint); numbering follows the position within the topic, so it is stable when others are
    skipped."""
    skip = skip or set()
    base = Path("cbse") / str(draft.class_) / draft.subject
    result = Compiled()
    per_topic: dict[str, list[int]] = {}
    for position, item in enumerate(draft.items):
        per_topic.setdefault(item.topic, []).append(position)
    all_mcs: dict[str, dict[str, Any]] = {}
    for topic_key, positions in per_topic.items():
        built: list[tuple[str, dict[str, Any]]] = []
        mcs_here: dict[str, dict[str, Any]] = {}
        for number, position in enumerate(positions, start=1):
            if position in skip:
                continue
            data, mcs = compile_item(draft, draft.items[position], number)
            rel = base / "items" / "authored" / draft.chapter / f"{topic_key}.{number:02d}.yaml"
            built.append((rel.as_posix(), data))
            mcs_here.update(mcs)
        if len(built) < MIN_ITEMS_PER_TOPIC:
            result.short_topics.append(
                f"{draft.class_}/{draft.subject}/{draft.chapter}/{topic_key}: {len(built)} items"
            )
            continue
        for rel_path, data in built:
            result.files[rel_path] = dump_yaml(data)
        result.items += len(built)
        all_mcs.update(mcs_here)
        skill = compile_skill(draft, topics[topic_key], sorted(mcs_here))
        result.files[(base / "skills" / "authored" / f"{topic_key}.yaml").as_posix()] = dump_yaml(
            skill
        )
        result.skills += 1
    for mid, data in sorted(all_mcs.items()):
        result.files[(base / "misconceptions" / "authored" / f"{mid}.yaml").as_posix()] = dump_yaml(
            data
        )
    result.misconceptions = len(all_mcs)
    return result


def write_compiled(content_root: Path, compiled: Compiled) -> int:
    """Write the files; returns how many changed on disk."""
    return sum(write_if_changed(content_root / rel, text) for rel, text in compiled.files.items())


def authored_files(content_root: Path) -> set[str]:
    """Every file currently under an `authored` folder of cbse content (for `--clean`)."""
    found: set[str] = set()
    base = content_root / "cbse"
    if base.is_dir():
        for path in base.rglob("*.yaml"):
            if "authored" in path.relative_to(base).parts:
                found.add(path.relative_to(content_root).as_posix())
    return found
