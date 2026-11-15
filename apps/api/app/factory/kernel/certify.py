"""Template certification: run every tuple of a declared parameter box, or a seeded sample.

Exhaustive when the box has at most 200,000 tuples: the certificate then states an exact fact
("every tuple was built and checked, N accepted, M refused as ill-posed, 0 failed"). Above that
we draw a seeded sample large enough that, with zero failures, the one-sided 95% Clopper-Pearson
upper bound on the failure rate is at most 1e-4 (29,956 draws). Any failure, exception or timeout
means no certificate. The bound is about the declared box and the checkers, not about the world:
it says nothing about how well the stem describes the model (see docs/adr).

Box format: {"name": {"min": int, "max": int, "step": int}} or {"name": {"choices": [...]}}.
`run_tuple(params) -> Outcome`: ok, skip (an ill-posed tuple the template refuses, counted and
reported, never hidden) or fail. An exception is a failure.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.factory.kernel.certificate import (
    Certificate,
    CertificationRefused,
    _mint_template_certificate,
)
from app.factory.kernel.exact import Deadline, Reject, chash

MAX_EXHAUSTIVE = 200_000
TARGET_UPPER = 1e-4
CONFIDENCE = 0.95
MAX_VALUES_PER_PARAM = 100_000


@dataclass(frozen=True)
class Outcome:
    status: str  # "ok" | "skip" | "fail"
    reason: str = ""


OK = Outcome("ok")


def skip(reason: str) -> Outcome:
    return Outcome("skip", reason)


def fail(reason: str) -> Outcome:
    return Outcome("fail", reason)


def param_values(spec: Mapping[str, Any]) -> list[Any]:
    if "choices" in spec:
        values = list(spec["choices"])
    else:
        lo, hi, step = int(spec["min"]), int(spec["max"]), int(spec.get("step", 1))
        if step < 1 or hi < lo:
            raise Reject("bad_box", "empty or backwards range")
        values = list(range(lo, hi + 1, step))
    if (
        not values
        or len(values) > MAX_VALUES_PER_PARAM
        or len(set(map(repr, values))) != len(values)
    ):
        raise Reject("bad_box", "empty, huge or duplicated parameter values")
    return values


def box_axes(box: Mapping[str, Mapping[str, Any]]) -> list[tuple[str, list[Any]]]:
    if not box:
        raise Reject("bad_box", "no parameters")
    return [(name, param_values(box[name])) for name in sorted(box)]


def box_size(box: Mapping[str, Mapping[str, Any]]) -> int:
    return math.prod(len(values) for _, values in box_axes(box))


def _decode(axes: list[tuple[str, list[Any]]], index: int) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, values in reversed(axes):
        index, pos = divmod(index, len(values))
        params[name] = values[pos]
    return dict(sorted(params.items()))


def _binomial_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k >= n else 0.0
    lp, lq, base = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    return sum(
        math.exp(base - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
        for i in range(k + 1)
    )


def clopper_pearson_upper(failures: int, n: int, confidence: float = CONFIDENCE) -> float:
    """One-sided upper bound on the failure probability after `failures` in `n` trials."""
    if not 0 <= failures <= n or n < 1:
        raise ValueError("need 0 <= failures <= n and n >= 1")
    if failures == n:
        return 1.0
    alpha = 1.0 - confidence
    lo, hi = 0.0, 1.0
    for _ in range(100):  # P(X <= failures | p) falls as p rises; find where it equals alpha
        mid = (lo + hi) / 2
        if _binomial_cdf(failures, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi


def required_sample(target: float = TARGET_UPPER, confidence: float = CONFIDENCE) -> int:
    """Draws needed so zero failures give an upper bound of at most `target`."""
    return math.ceil(math.log(1.0 - confidence) / math.log1p(-target))


@dataclass
class BoxReport:
    template_id: str
    kind: str  # "exhaustive" | "sampled"
    size: int
    tested: int
    ok: int = 0
    skipped: int = 0
    failures: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)
    failure_samples: list[dict[str, Any]] = field(default_factory=list)
    upper_bound: float = 0.0
    refused: list[str] = field(default_factory=list)
    certificate: Certificate | None = None


def certify_template(
    template_id: str,
    template_hash: str,
    box: Mapping[str, Mapping[str, Any]],
    run_tuple: Callable[[dict[str, Any]], Outcome],
    *,
    checker_versions: Mapping[str, str],
    seed: int = 0,
    max_exhaustive: int = MAX_EXHAUSTIVE,
    target_upper: float = TARGET_UPPER,
    time_budget_s: float = 600.0,
    fault_injection_report_id: str | None = None,
) -> BoxReport:
    axes = box_axes(box)
    size = math.prod(len(v) for _, v in axes)
    exhaustive = size <= max_exhaustive
    if exhaustive:
        indices: Any = range(size)
    else:
        indices = random.Random(seed).sample(range(size), min(size, required_sample(target_upper)))
    report = BoxReport(template_id, "exhaustive" if exhaustive else "sampled", size, len(indices))
    deadline = Deadline(time_budget_s)
    reasons: Counter[str] = Counter()
    try:
        for index in indices:
            deadline.check()
            params = _decode(axes, index)
            try:
                outcome = run_tuple(params)
            except Exception as exc:  # noqa: BLE001 - a crash is a failure, never a pass
                outcome = fail(f"exception:{type(exc).__name__}")
            if outcome.status == "ok":
                report.ok += 1
            elif outcome.status == "skip":
                report.skipped += 1
                reasons[outcome.reason] += 1
            else:
                report.failures += 1
                if len(report.failure_samples) < 20:
                    report.failure_samples.append({"params": params, "reason": outcome.reason})
    except Reject as rej:
        report.refused.append(rej.code)
    report.skip_reasons = dict(sorted(reasons.items()))
    done = report.ok + report.skipped + report.failures
    if done != report.tested:
        report.refused.append("incomplete_run")
    report.upper_bound = (
        0.0 if exhaustive and not report.failures
        else clopper_pearson_upper(report.failures, max(done, 1))
    )  # fmt: skip
    if report.failures:
        report.refused.append(f"failures:{report.failures}")
    if not report.ok:
        report.refused.append("no_tuple_accepted")
    if not exhaustive and report.upper_bound > target_upper:
        report.refused.append("bound_above_target")
    if report.refused:
        return report
    try:
        report.certificate = _mint_template_certificate(
            template_id,
            template_hash,
            box={
                "axes": [name for name, _ in axes],
                "box_hash": chash({n: dict(box[n]) for n in sorted(box)}),
                "size": size,
                "tested": report.tested,
                "kind": report.kind,
                "seed": None if exhaustive else seed,
            },
            outcomes={
                "ok": report.ok,
                "skipped_ill_posed": report.skipped,
                "skip_reasons": report.skip_reasons,
                "failures": 0,
            },
            error_bound={
                "kind": "exhaustive_zero" if exhaustive else "clopper_pearson_upper",
                "confidence": f"{CONFIDENCE}",
                "upper": "0" if exhaustive else f"{report.upper_bound:.3e}",
                "target": f"{target_upper:.0e}",
            },
            checker_versions=dict(checker_versions),
            fault_injection_report_id=fault_injection_report_id,
        )
    except CertificationRefused as refusal:
        report.refused.extend(refusal.reasons)
    return report
