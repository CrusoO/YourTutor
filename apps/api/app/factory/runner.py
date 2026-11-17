"""Glue: certify a lane template over its whole parameter box with the full checker stack."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.factory import kernel
from app.factory.kernel.certify import MAX_EXHAUSTIVE
from app.factory.kernel.exact import chash
from app.factory.pipeline import PipelineResult, default_checkers, run
from app.factory.registry import ItemContext, Lane


def template_hash(lane: Lane, template: Mapping[str, Any]) -> str:
    return chash({"lane": lane.name, "template": dict(template)})


def apply_variant(ctx: ItemContext, template: Mapping[str, Any]) -> ItemContext:
    """Apply a derived template's variant (see `app.factory.variants`) to a rendered item.

    A plain template has no `variant` and nothing changes. A variant changes only where the item
    is used (its pool, an id suffix so it never collides with a practice item) and, for
    `explain`, the framing: a classmate's wrong answer is quoted and the learner picks the correct
    one. The key and every checked number are untouched, so the whole checker stack still proves
    them; no wording about a reason is added that nothing could check.
    """
    variant = template.get("variant")
    if not variant:
        return ctx
    from app.factory.variants import KINDS

    spec = KINDS[str(variant)]
    ctx.pool = spec["pool"]
    ctx.item_id = f"{ctx.item_id}.{spec['suffix'].lower()}"
    if spec.get("role"):
        ctx.role = spec["role"]
    if variant == "explain":
        wrong = _first_wrong_text(ctx)
        if wrong is None:
            raise ValueError("explain variant needs an item with a named wrong answer")
        ctx.stem = (
            f"{ctx.stem} A classmate says the answer is {wrong}. "
            "Work it out yourself and choose the correct answer."
        )
    return ctx


def _first_wrong_text(ctx: ItemContext) -> str | None:
    for option in ctx.options:
        if (
            option.get("procedure") not in (None, "", "correct")
            and option.get("id") != ctx.key_option
        ):
            return str(option.get("text") or "").strip() or None
    for wrong in ctx.wrong_answers:
        if str(wrong.get("text", "")).strip():
            return str(wrong["text"]).strip()
    return None


def build_item(
    lane: Lane, template: Mapping[str, Any], params: Mapping[str, Any], **bank: Any
) -> ItemContext:
    ctx = apply_variant(lane.render(template, params), template)
    for name, value in bank.items():  # reference_index, bank_stems, known_chapters, ...
        setattr(ctx, name, value)
    return ctx


def run_item(
    lane: Lane, template: Mapping[str, Any], params: Mapping[str, Any], **bank: Any
) -> tuple[ItemContext, PipelineResult]:
    ctx = build_item(lane, template, params, **bank)
    return ctx, run(ctx)


def certify_lane_template(
    lane: Lane,
    template: Mapping[str, Any],
    *,
    seed: int = 0,
    max_exhaustive: int = MAX_EXHAUSTIVE,
    **bank: Any,
) -> kernel.BoxReport:
    """Every tuple: lane well-posed predicate (skip), render, full pipeline (stampable or fail)."""
    versions: dict[str, str] = {c.id: c.version for c in default_checkers()}

    def run_tuple(params: dict[str, Any]) -> kernel.Outcome:
        reason = lane.well_posed(template, params)
        if reason:
            return kernel.skip(reason)
        _, result = run_item(lane, template, params, **bank)
        if result.stampable:
            return kernel.OK
        failure = result.first_failure
        return kernel.fail(f"{failure.checker_id}:{failure.code}" if failure else "not_stampable")

    return kernel.certify_template(
        str(template["id"]),
        template_hash(lane, template),
        lane.box(template),
        run_tuple,
        checker_versions=versions,
        seed=seed,
        max_exhaustive=max_exhaustive,
    )
