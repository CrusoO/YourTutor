from __future__ import annotations

from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[3] / "content" / "e2e_mini"
NE = "<Nepali — to be filled by reviewer>"
AS = "<Assamese — to be filled by reviewer>"


def loc(en: str) -> dict[str, str]:
    return {"en": en, "ne": NE, "as": AS}


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def hints_for(stem: str, ans: str) -> list[dict]:
    if "=" in stem:
        return [
            {"level": 1, **loc("What undoes the step?")},
            {"level": 2, **loc("Undo the same operation on each side.")},
            {"level": 3, **loc(f"x = {ans}")},
        ]
    return [
        {"level": 1, **loc("What operation is shown?")},
        {"level": 2, **loc("Work from left to right.")},
        {"level": 3, **loc(f"Answer: {ans}")},
    ]


skills = ["MATH.E2E.ONE", "MATH.E2E.TWO", "MATH.E2E.INT"]
for sid in skills:
    dump(
        root / "skills" / f"{sid.replace('.', '_').lower()}.yaml",
        {
            "id": sid,
            "title": loc("E2E skill"),
            "grade_band": [9],
            "subject": "math",
            "prerequisites": [],
            "related": [],
            "misconceptions": [],
            "bkt": {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            "status": "draft",
        },
    )

for i, (sid, stem, ans) in enumerate(
    [
        ("MATH.E2E.ONE", "Solve for x: x + 2 = 7", "5"),
        ("MATH.E2E.ONE", "Solve for x: x + 3 = 8", "5"),
        ("MATH.E2E.TWO", "Solve for x: 2x + 1 = 9", "4"),
        ("MATH.E2E.TWO", "Solve for x: 2x + 2 = 10", "4"),
        ("MATH.E2E.INT", "Compute: 10 - 4.", "6"),
        ("MATH.E2E.INT", "Compute: 11 - 6.", "5"),
    ],
    1,
):
    dump(
        root / "items" / f"item_e2e_d_{i:02d}.yaml",
        {
            "id": f"ITEM.E2E.D.{i:02d}",
            "skill_ids": [sid],
            "difficulty": 0.3,
            "type": "expression",
            "pool": "diagnostic",
            "role": "procedure",
            "stem": loc(stem),
            "answer": {"sympy": ans, "accept": [ans]},
            "solution_steps": [loc(f"x = {ans}")],
            "hints": hints_for(stem, ans),
            "prediction_prompt": loc("Guess?"),
            "misconception_rules": [],
            "status": "draft",
        },
    )

for i, (sid, stem, ans) in enumerate(
    [
        ("MATH.E2E.ONE", "Solve for x: x + 1 = 4", "3"),
        ("MATH.E2E.TWO", "Solve for x: x + 5 = 9", "4"),
    ],
    1,
):
    dump(
        root / "items" / f"item_e2e_c_{i:02d}.yaml",
        {
            "id": f"ITEM.E2E.C.{i:02d}",
            "skill_ids": [sid],
            "difficulty": 0.3,
            "type": "expression",
            "pool": "checkpoint",
            "role": "procedure",
            "stem": loc(stem),
            "answer": {"sympy": ans, "accept": [ans]},
            "solution_steps": [loc(f"x = {ans}")],
            "hints": hints_for(stem, ans),
            "prediction_prompt": loc("Guess?"),
            "misconception_rules": [],
            "status": "draft",
        },
    )

for i, (sid, stem, ans) in enumerate(
    [
        ("MATH.E2E.ONE", "Solve for x: x + 4 = 10", "6"),
        ("MATH.E2E.TWO", "Solve for x: 2x + 4 = 12", "4"),
        ("MATH.E2E.INT", "Compute: 9 - 2.", "7"),
    ],
    1,
):
    dump(
        root / "items" / f"item_e2e_p_{i:02d}.yaml",
        {
            "id": f"ITEM.E2E.P.{i:02d}",
            "skill_ids": [sid],
            "difficulty": 0.3,
            "type": "expression",
            "pool": "practice",
            "role": "procedure",
            "stem": loc(stem),
            "answer": {"sympy": ans, "accept": [ans]},
            "solution_steps": [loc(f"x = {ans}")],
            "hints": hints_for(stem, ans),
            "prediction_prompt": loc("Will x be small?"),
            "misconception_rules": [],
            "status": "draft",
        },
    )

dump(
    root / "overlays" / "mini.yaml",
    {
        "id": "OV.E2E.MINI",
        "curriculum_id": "bhutan",
        "grade": 9,
        "chapter": "e2e_mini",
        "skill_ids": skills,
        "live": False,
    },
)
dump(
    root / "checkpoints" / "e2e_mini.yaml",
    {
        "id": "CP.E2E.MINI.FORMS",
        "checkpoint_id": "CP.E2E.MINI",
        "A": ["ITEM.E2E.C.01"],
        "B": ["ITEM.E2E.C.02"],
        "match_map": {"ITEM.E2E.C.01": "ITEM.E2E.C.02"},
    },
)
print(f"Wrote e2e mini under {root}")
