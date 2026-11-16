"""Write the lane's skills, misconceptions, templates and overlays as YAML.

    python -m app.factory.lanes.maths.emit --root ../../content/cbse/10/maths

Stamped items are NOT written here: only the factory CLI (`python -m app.factory stamp`) writes
items, because only the stamp step may set a tier.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from app.factory.lanes.maths import catalog
from app.factory.lanes.maths.misconceptions import TEXT


def _dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def _slug(identifier: str) -> str:
    return identifier.lower().replace(".", "_")


def render_files() -> dict[str, str]:
    """relative path (posix) -> file text"""
    files: dict[str, str] = {}
    templates = catalog.all_templates()
    chapter_of_skill = {t["skill_id"]: t["syllabus"]["chapter_ref"] for t in templates}
    skills = catalog.skill_records()
    owner: dict[str, str] = {}
    for sk in skills:
        folder = (
            catalog.CHAPTERS[chapter_of_skill[sk["id"]]]["key"]
            if sk["id"] in chapter_of_skill
            else "prerequisites_class_8_9"
        )
        files[f"skills/{folder}/{_slug(sk['id'])}.yaml"] = _dump(sk)
        for mc in sk["misconceptions"]:
            owner.setdefault(mc, sk["id"])
    for mc, skill in sorted(owner.items()):
        title, explanation = TEXT[mc]
        files[f"misconceptions/{_slug(mc)}.yaml"] = _dump(
            {
                "id": mc,
                "title": {"en": title},
                "explanation": {"en": explanation},
                "remedial_skill": skill,
                "status": "draft",
            }
        )
    for t in templates:
        files[f"templates/{_slug(t['short'])}.yaml"] = _dump(t)
    for ov in catalog.overlay_records():
        files[f"overlays/{_slug(ov['id'])}.yaml"] = _dump(ov)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.factory.lanes.maths.emit")
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
