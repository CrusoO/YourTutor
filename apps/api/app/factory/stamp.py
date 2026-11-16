"""The stamp step: the ONLY writer of a verification record and of tier A.

It runs after the whole pipeline passed and the kernel minted the certificate. It builds the Item
(multiple choice, option letters shuffled so ids do not reveal the key), computes the item content
hash, writes the vrec/1 record with the honest label, and appends the record hash to the ledger.
A hand-written tier or record is worthless: the loader accepts only record hashes found in the
ledger.
"""

from __future__ import annotations

import random
from typing import Any

from app.content.ledger import Ledger
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content.verification import CALCULATION_CHECKED, LABEL_TIER, VREC_SCHEMA, record_hash
from app.factory.kernel import KERNEL_VERSION, constants_hash
from app.factory.kernel.exact import chash
from app.factory.pipeline import PipelineResult
from app.factory.registry import ItemContext

GENERATOR_VERSION = "factory-1"
LETTERS = "abcdefgh"


class StampRefused(Exception):  # noqa: N818
    pass


def _text(value: str) -> dict[str, str]:
    return {"en": value}


def build_item(ctx: ItemContext, template_id: str, template_hash: str) -> dict[str, Any]:
    """The item as a plain dict (no tier, no verification yet)."""
    if not ctx.options or ctx.key_option is None:
        raise StampRefused("only multiple-choice items can be stamped in this version")
    if len(ctx.options) > len(LETTERS):
        raise StampRefused("too many options")
    order = list(ctx.options)
    random.Random(chash(ctx.item_id)).shuffle(order)
    letters = {opt["id"]: LETTERS[i] for i, opt in enumerate(order)}
    key = letters[ctx.key_option]
    skills = ctx.skill_ids or [str(ctx.syllabus.get("skill_id", ""))]
    return {
        "id": ctx.item_id,
        "skill_ids": skills,
        "difficulty": ctx.difficulty,
        "type": "mcq",
        "pool": "practice",
        "role": ctx.role,
        "stem": _text(ctx.stem),
        "options": [{"id": letters[o["id"]], "en": str(o["text"])} for o in order],
        "answer": {"sympy": key, "accept": []},
        "solution_steps": [_text(s) for s in [*ctx.steps, f"The correct option is {key}."]],
        "hints": [{"level": i, "en": h} for i, h in enumerate(ctx.hints, start=1)],
        "prediction_prompt": _text(ctx.prediction or "What do you expect the answer to be?"),
        "status": "draft",
        "template_id": template_id,
        "generator_version": GENERATOR_VERSION,
        "template_hash": template_hash,
        "provenance": {"original": True, "author": "app.factory"},
    }


def stamp(
    ctx: ItemContext,
    result: PipelineResult,
    *,
    template_id: str,
    template_hash: str,
    ledger: Ledger,
    ts: str,
    git_sha: str = "",
) -> dict[str, Any]:
    """Return the item dict with tier A and its verification record; log the stamp."""
    if not result.stampable or ctx.certificate is None:
        raise StampRefused(
            "the pipeline did not pass: "
            + (result.first_failure.code if result.first_failure else "no certificate")
        )
    draft = build_item(ctx, template_id, template_hash)
    item_hash = item_content_hash(Item.model_validate(draft))
    cert = ctx.certificate.body
    record: dict[str, Any] = {
        "schema": VREC_SCHEMA,
        "item_hash": item_hash,
        "template_hash": template_hash,
        "certificate_hash": ctx.certificate.hash,
        "label": CALCULATION_CHECKED,
        "tier": LABEL_TIER[CALCULATION_CHECKED],
        "lane": ctx.lane,
        "chapter_ref": str(ctx.syllabus.get("chapter_ref", "")),
        "methods_agreeing": [m["id"] for m in cert["methods"]],
        "checks": [
            {"id": r.checker_id, "v": r.version, "status": r.status} for r in result.results
        ],
        "generated_by": {
            "tool": "app.factory",
            "generator_version": GENERATOR_VERSION,
            "kernel_version": KERNEL_VERSION,
            "constants_hash": constants_hash(),
            "git_sha": git_sha,
        },
        "llm_involved": ctx.llm_involved,
        "stamped_at": ts,
    }
    record["record_hash"] = record_hash(record)
    final = {**draft, "tier": "A", "verification": record}
    Item.model_validate(final)  # the schema refuses anything but the honest labels
    ledger.append(
        "stamped",
        ctx.item_id,
        item_hash,
        {
            "record_hash": record["record_hash"],
            "certificate_hash": record["certificate_hash"],
            "template_id": template_id,
            "template_hash": template_hash,
            "lane": ctx.lane,
            "chapter_ref": record["chapter_ref"],
            "label": CALCULATION_CHECKED,
        },
        ts=ts,
    )
    return final
