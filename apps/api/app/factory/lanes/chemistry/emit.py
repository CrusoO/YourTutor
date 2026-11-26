"""Write the chemistry lane's skills, misconceptions, templates and overlays as YAML.

    python -m app.factory.lanes.chemistry.emit --root ../../content/cbse/10/chemistry

Stamped items are NOT written here: only the factory CLI (`python -m app.factory stamp`) writes
items, because only the stamp step may set a tier. The curriculum entry is a separate block of text
(`catalog.curriculum_block`) that is appended once to the curriculum file by hand.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path
from typing import Any

import yaml

from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import chash
from app.factory.lanes.chemistry import catalog
from app.factory.lanes.chemistry.core import distinct_wrong
from app.factory.lanes.chemistry.lane import LANE
from app.factory.lanes.chemistry.misconceptions import TEXT, remedial_skill

MAX_TUPLES_PER_TEMPLATE = 4000


def _dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def _slug(identifier: str) -> str:
    return identifier.lower().replace(".", "_")


def used_misconceptions() -> dict[str, set[str]]:
    """skill id -> misconception ids that appear as an offered wrong option of some item."""
    used: dict[str, set[str]] = {}
    for tpl in catalog.template_records():
        axes = box_axes(tpl["box"])
        count = 0
        for combo in itertools.product(*[v for _, v in axes]):
            count += 1
            if count > MAX_TUPLES_PER_TEMPLATE:
                break
            params = {n: c for (n, _), c in zip(axes, combo, strict=True)}
            built = LANE._build(tpl, params)
            if isinstance(built, str):
                continue
            for mc, _, _ in distinct_wrong(built.answer, built.key_text, built.wrong, chash):
                used.setdefault(tpl["skill_id"], set()).add(mc)
    return used


def render_files() -> dict[str, str]:
    files: dict[str, str] = {}
    owner = catalog.chapter_of_skill()
    used = used_misconceptions()
    for sid, title, source in catalog.PREREQS:
        files[f"skills/{_slug(sid)}.yaml"] = _dump(
            {"id": sid, "title": {"en": title}, "grade_band": [8, 9], "subject": "chemistry",
             "prerequisites": [], "misconceptions": [], "bkt": catalog.BKT, "status": "draft"}
        )  # fmt: skip
        _ = source
    for sid, title, prereqs in catalog.SKILLS:
        files[f"skills/{_slug(sid)}.yaml"] = _dump(
            {"id": sid, "title": {"en": title}, "grade_band": [10], "subject": "chemistry",
             "prerequisites": prereqs, "misconceptions": sorted(used.get(sid, set())),
             "bkt": catalog.BKT, "status": "draft"}
        )  # fmt: skip
    every = sorted({mc for mcs in used.values() for mc in mcs})
    for mc in every:
        title, explanation = TEXT[mc]
        files[f"misconceptions/{_slug(mc)}.yaml"] = _dump(
            {"id": mc, "title": {"en": title}, "explanation": {"en": explanation},
             "remedial_skill": remedial_skill(mc), "status": "draft"}
        )  # fmt: skip
    for tpl in catalog.template_records():
        files[f"templates/{_slug(tpl['id'])}.yaml"] = _dump(tpl)
    for ov in catalog.overlay_records():
        files[f"overlays/{_slug(ov['id'])}.yaml"] = _dump(ov)
    _ = owner
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.factory.lanes.chemistry.emit")
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
