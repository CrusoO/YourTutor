"""Every implemented checker must reject every seeded fault class (kill rate 100 percent)."""

import pytest

from app.factory.faults import FAULTS, run_fault_injection
from app.factory.pipeline import default_checkers

from .corpus import corpus

REQUIRED = {
    "sign_flip",
    "wrong_constant",
    "unit_slip",
    "off_by_one_atom",
    "dropped_root",
    "swapped_option",
}


@pytest.fixture(scope="module")
def report():
    return run_fault_injection(corpus())


def test_baseline_items_are_all_accepted(report):
    assert report.baseline_failures == []


def test_required_fault_classes_are_covered_and_applied_often(report):
    assert REQUIRED <= set(report.classes)
    for name, row in report.classes.items():
        assert row.applied >= 5, (
            f"{name} applied only {row.applied} times: the kill rate would mean little"
        )


@pytest.mark.parametrize("fault", [f.id for f in FAULTS])
def test_kill_rate_is_100_percent(report, fault):
    row = report.classes[fault]
    assert row.killed == row.applied, f"survivors: {row.survivors[:5]}"
    for checker_id, (applied, killed) in row.by_checker.items():
        assert applied == killed, f"{checker_id} missed {applied - killed} {fault} mutants"


def test_every_claimed_fault_is_a_known_class_and_declared_by_its_checker():
    claims = {c.id: set(c.FAULTS) for c in default_checkers()}
    for fault in FAULTS:
        for checker_id in fault.catchers:
            assert fault.id in claims[checker_id], f"{checker_id} does not declare {fault.id}"
    known = {f.id for f in FAULTS}
    assert all(c <= known for c in claims.values())


def test_report_is_perfect_and_has_a_stable_id(report):
    assert report.perfect
    assert (
        report.report_id.startswith("FI-")
        and report.report_id == run_fault_injection(corpus()).report_id
    )
    assert "sign_flip" in report.render()


def test_the_harness_notices_a_blind_checker():
    from app.factory import faults

    class Blind:  # a checker that accepts everything must show up as survivors
        id, version, lanes, FAULTS = "wellposed.predicates", "1", frozenset(), ()

    fault = faults.Fault("sign_flip", "x", faults.sign_flip, ("wellposed.predicates",))
    original = faults.default_checkers

    class Pass:
        id = "wellposed.predicates"
        version = "1"
        lanes = frozenset()  # type: ignore[var-annotated]
        FAULTS = ()  # type: ignore[var-annotated]

        def check(self, ctx):
            from app.factory.registry import CheckResult

            return CheckResult(self.id, "1", "pass")

    faults.default_checkers = lambda: [Pass()]  # type: ignore[assignment,list-item]
    try:
        rep = faults.run_fault_injection(corpus()[:1], [fault])
    finally:
        faults.default_checkers = original
    assert rep.classes["sign_flip"].by_checker["wellposed.predicates"][1] == 0 and not rep.perfect
