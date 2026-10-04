"""Stem structure signatures and content hashes."""

from __future__ import annotations

import hashlib
import json
import re

from app.content.schema import Item

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_ONE_X = re.compile(r"(?<![\d.])1x\b")


def structure_signature(stem: str) -> str:
    return _NUM.sub("N", re.sub(r"\s+", " ", stem.strip()))


def has_one_x(text: str) -> bool:
    return bool(_ONE_X.search(text))


def item_content_hash(item: Item) -> str:
    payload = {
        "id": item.id,
        "skill_ids": item.skill_ids,
        "stem": item.stem.en,
        "answer": item.answer.sympy,
        "hints": [(h.level, h.en) for h in item.hints],
        "steps": [s.en for s in item.solution_steps],
        "verify": item.verify
        if isinstance(item.verify, str)
        else (item.verify.model_dump() if item.verify else None),
        "options": [o.id for o in item.options],
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
