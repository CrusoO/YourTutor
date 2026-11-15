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


def build_item(
    lane: Lane, template: Mapping[str, Any], params: Mapping[str, Any], **bank: Any
) -> ItemContext:
    ctx = lane.render(template, params)
    for name, value in bank.items():  # reference_index, bank_signatures, known_chapters, ...
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
