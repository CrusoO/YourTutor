from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def loc(en: str) -> dict[str, str]:
    return {
        "en": en,
        "ne": "<Nepali — to be filled by reviewer>",
        "as": "<Assamese — to be filled by reviewer>",
    }


def minimal_skill(skill_id: str = "MATH.S1", prereqs: list[str] | None = None) -> dict:
    return {
        "id": skill_id,
        "title": loc("Skill"),
        "grade_band": [9],
        "subject": "math",
        "prerequisites": prereqs or [],
        "related": [],
        "misconceptions": [],
        "bkt": {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
        "status": "draft",
    }


def minimal_item(
    item_id: str = "ITEM.1",
    *,
    skill: str = "MATH.S1",
    pool: str = "practice",
    answer: str = "5",
    last_step: str | None = None,
    hint1: str = "What undoes the operation?",
    status: str = "draft",
    stem: str | None = None,
) -> dict:
    stem_en = stem or f"[{item_id}] Solve for x: x + 7 = 12"
    return {
        "id": item_id,
        "skill_ids": [skill],
        "difficulty": 0.3,
        "type": "expression",
        "pool": pool,
        "role": "procedure",
        "stem": loc(stem_en),
        "answer": {"sympy": answer, "accept": [answer]},
        "solution_steps": [loc("Subtract 7."), loc(last_step or f"x = {answer}")],
        "hints": [
            {"level": 1, **loc(f"{hint1} ({item_id})")},
            {"level": 2, **loc(f"Undo the added number on {item_id}.")},
            {"level": 3, **loc("Subtract 7, then read x.")},
        ],
        "prediction_prompt": loc("Will x be smaller than 12?"),
        "misconception_rules": [],
        "reviewed_by": None,
        "status": status,
    }


_PRACTICE_STEMS = (
    "Solve for x: x + {n} = {m}",
    "Find x if x - {n} = {m}",
    "Solve: x + {n} = {m}",
    "x + {n} = {m}. Solve for x.",
    "Compute x in x - {n} = {m}.",
)


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    write_yaml(tmp_path / "skills" / "s1.yaml", minimal_skill())
    for index in range(5):
        stem = _PRACTICE_STEMS[index].format(n=7 + index, m=12 + index)
        write_yaml(
            tmp_path / "items" / f"p{index}.yaml",
            minimal_item(f"ITEM.P{index}", pool="practice", stem=stem),
        )
    for index in range(3):
        write_yaml(
            tmp_path / "items" / f"d{index}.yaml",
            minimal_item(f"ITEM.D{index}", pool="diagnostic"),
        )
    write_yaml(
        tmp_path / "misconceptions" / "m1.yaml",
        {
            "id": "MC.1",
            "title": loc("Wrong inverse"),
            "explanation": loc("Undo by doing the opposite."),
            "remedial_skill": "MATH.S1",
            "status": "draft",
        },
    )
    write_yaml(
        tmp_path / "overlays" / "ov.yaml",
        {
            "id": "ov1",
            "curriculum_id": "bhutan",
            "grade": 9,
            "chapter": "linear_equations",
            "skill_ids": ["MATH.S1"],
            "live": False,
        },
    )
    write_yaml(
        tmp_path / "glossary" / "en-ne.yaml",
        {"language": "ne", "terms": {"equation": "<Nepali — to be filled by reviewer>"}},
    )
    return tmp_path
