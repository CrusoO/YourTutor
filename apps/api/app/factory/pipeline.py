"""The ordered pipeline. A fail stops the item; later checkers are recorded as not run."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.factory.checkers import ORDER
from app.factory.registry import FAIL, PASS, SKIP, Checker, CheckResult, ItemContext


def default_checkers() -> list[Checker]:
    return [cls() for cls in ORDER]


@dataclass
class PipelineResult:
    results: list[CheckResult] = field(default_factory=list)
    durations_ms: dict[str, int] = field(default_factory=dict)

    @property
    def rejected(self) -> bool:
        return any(r.status == FAIL for r in self.results)

    @property
    def first_failure(self) -> CheckResult | None:
        return next((r for r in self.results if r.status == FAIL), None)

    @property
    def stampable(self) -> bool:
        """Every checker passed or is not applicable, and the stamp step minted a certificate."""
        last = self.results[-1] if self.results else None
        return (
            not self.rejected
            and last is not None
            and last.checker_id == "stamp"
            and last.status == PASS
            and all(
                r.status in (PASS, SKIP) and r.code in ("ok", "not_applicable")
                for r in self.results
            )
        )

    def checker_versions(self) -> dict[str, str]:
        return {r.checker_id: r.version for r in self.results}


def run(
    ctx: ItemContext, checkers: Sequence[Checker] | None = None, *, extra: Sequence[Checker] = ()
) -> PipelineResult:
    """Run the checkers in order. `extra` lane checkers run just before the stamp step."""
    chain = list(checkers if checkers is not None else default_checkers())
    if extra:
        chain[-1:-1] = list(extra)
    out = PipelineResult()
    failed = False
    for checker in chain:
        if failed:
            out.results.append(CheckResult(checker.id, checker.version, SKIP, "not_run"))
            continue
        if checker.lanes and ctx.lane not in checker.lanes:
            out.results.append(CheckResult(checker.id, checker.version, SKIP, "not_applicable"))
            continue
        start = time.monotonic()
        try:
            result = checker.check(ctx)
        except Exception as exc:  # noqa: BLE001 - fail closed
            result = CheckResult(
                checker.id, checker.version, FAIL, f"checker_exception:{type(exc).__name__}"
            )
        out.durations_ms[checker.id] = int((time.monotonic() - start) * 1000)
        out.results.append(result)
        failed = result.status == FAIL
    return out
