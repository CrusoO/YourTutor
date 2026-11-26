# ruff: noqa: E501
"""Write the lane skills, misconceptions, templates and overlays as YAML.

    python -m app.factory.lanes.maths_c12.emit --root ../../content/cbse/12/maths

Stamped items are NOT written here: only the factory CLI (`python -m app.factory stamp`) writes items.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from app.factory.lanes.maths_c12 import catalog
from app.factory.lanes.maths_c12.core import MODELS
from app.factory.lanes.maths_c12.template import all_templates


def _dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def render_files() -> dict[str, str]:
    """relative path (posix) -> file text"""
    files: dict[str, str] = {}
    chapter_of_skill = {s.skill_id: s.chapter for s in MODELS.values()}
    owner: dict[str, str] = {}
    for sk in catalog.skill_records():
        folder = (
            catalog.CHAPTERS[chapter_of_skill[sk["id"]]]["key"]
            if sk["id"] in chapter_of_skill
            else "prerequisites_earlier_grades"
        )
        files[f"skills/{folder}/{catalog._slug(sk['id'])}.yaml"] = _dump(sk)
        for mc in sk["misconceptions"]:
            owner.setdefault(mc, sk["id"])
    for mc, skill in sorted(owner.items()):
        title, why = catalog.humanize(mc)
        files[f"misconceptions/{catalog._slug(mc)}.yaml"] = _dump(
            {
                "id": mc,
                "title": {"en": title},
                "explanation": {"en": why},
                "remedial_skill": skill,
                "status": "draft",
            }
        )
    for t in all_templates():
        files[f"templates/{catalog._slug(t['short'])}.yaml"] = _dump(t)
    for ov in catalog.overlay_records():
        files[f"overlays/{catalog._slug(ov['id'])}.yaml"] = _dump(ov)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.factory.lanes.maths_c12.emit")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    files = render_files()
    for rel, text in sorted(files.items()):
        path = args.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(files)} files under {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
