"""verify(spec, answer, witness): the one entry point. Never raises; anything odd is a rejection.

Fail closed: an exception, a timeout, an unknown domain or kind, a missing witness, a float or
any malformed input returns `accepted=False`. Acceptance needs the domain checker to run to the end.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.factory.kernel import algebra, genetics, kinematics, stoichiometry, units
from app.factory.kernel.exact import Deadline, Reject

_DOMAINS: dict[str, Callable[[dict, dict, dict, Deadline], dict]] = {
    "algebra": algebra.verify,
    "stoichiometry": stoichiometry.verify,
    "kinematics": kinematics.verify,
    "genetics": genetics.verify,
}
# Bump a version when its checker changes: certificates record these and go stale on a change.
CHECKER_VERSIONS: dict[str, str] = {
    "algebra": "1",
    "stoichiometry": "1",
    "kinematics": "1",
    "genetics": "1",
}
KERNEL_GROUP = "kernel.exact"
DOMAINS = tuple(sorted(_DOMAINS))


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    code: str  # "ok" or a stable rejection code
    detail: str = ""
    domain: str = ""
    checker_version: str = ""
    data: dict[str, Any] = field(default_factory=dict)


def verify(spec: Any, answer: Any, witness: Any, *, timeout_s: float = 30) -> Verdict:
    domain = spec.get("domain", "") if isinstance(spec, dict) else ""
    try:
        if not (isinstance(spec, dict) and isinstance(answer, dict) and isinstance(witness, dict)):
            raise Reject("malformed", "spec, answer and witness must all be objects")
        if domain not in _DOMAINS:
            raise Reject("unknown_domain", str(domain))
        data = _DOMAINS[domain](spec, answer, witness, Deadline(timeout_s))
        return Verdict(True, "ok", "", domain, CHECKER_VERSIONS[domain], data)
    except Reject as rej:
        return Verdict(False, rej.code, rej.detail, domain, CHECKER_VERSIONS.get(domain, ""))
    except Exception as exc:  # noqa: BLE001 - fail closed on anything at all
        return Verdict(False, f"exception:{type(exc).__name__}", str(exc)[:120], domain)


def expected_dimension(spec: Any) -> units.Dim | None:
    """Dimension the answer must have, or None when the domain has no unit."""
    if not isinstance(spec, dict):
        return None
    if spec.get("domain") == "kinematics":
        return kinematics.expected_dim(spec)
    if spec.get("domain") == "stoichiometry":
        return stoichiometry.expected_dim(spec)
    return None


def answer_unit_ok(spec: Any, answer: Any) -> tuple[bool, str]:
    """Unit check on its own: the answer's unit exists and has the right dimension."""
    want = expected_dimension(spec)
    if want is None:
        return True, "no unit for this question"
    try:
        _, got = units.parse_unit(str(answer.get("unit", "")))
    except Reject as rej:
        return False, rej.code
    return (got == want), ("ok" if got == want else "unit_dimension_mismatch")
