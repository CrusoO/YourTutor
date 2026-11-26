"""Seeded faults: 100 percent kill rate per class, for the whole pipeline and per named checker."""

import pytest

from app.content.originality import ReferenceIndex
from app.factory.faults import run_fault_injection
from app.factory.lanes.physics_c12.faultset import ALL_FAULTS, LANE_FAULTS, fault_cases
from app.factory.lanes.physics_c12.lane import LANE
from app.factory.lanes.physics_c12.templates import TEMPLATES

from .helpers import first


def _extra_cases():
    cases = []
    for model_id, variant in (
        ("EF.COULOMB", "F_from_q1_q2_r"),
        ("DUAL.PHOTOELECTRIC", "Kj_from_f_phi"),
        ("MAG.B_FIELD", "Bw_from_I_r"),
        ("EM_WAVE", "lam_from_f"),
    ):
        model_id = {"EM_WAVE": "EMW.EM_WAVE"}.get(model_id, model_id)
        ctx = LANE.render(TEMPLATES[model_id], first(model_id, variant=variant))
        ctx.reference_index = ReferenceIndex()
        cases.append(ctx)
    return cases


@pytest.fixture(scope="module")
def report():
    return run_fault_injection(fault_cases("all", 1) + _extra_cases(), ALL_FAULTS)


def test_baseline_items_are_all_accepted(report):
    assert report.baseline_failures == []


def test_every_class_is_applied(report):
    classes = set(report.classes)
    assert {"unit_slip", "wrong_constant", "sign_flip", "swapped_option"} <= classes
    for name in ("dropped_factor", "wrong_sig_figs"):
        assert any(c.startswith(name) for c in classes)
    for name, row in report.classes.items():
        assert row.applied >= 3, f"{name} applied only {row.applied} times"


@pytest.mark.parametrize("fault", [f.id for f in ALL_FAULTS])
def test_kill_rate_is_100_percent(report, fault):
    row = report.classes[fault]
    assert row.killed == row.applied, f"survivors: {row.survivors[:5]}"
    for checker_id, (applied, killed) in row.by_checker.items():
        assert applied == killed, f"{checker_id} missed {applied - killed} {fault} mutants"


def test_report_is_perfect(report):
    assert report.perfect and {f.id for f in LANE_FAULTS} <= set(report.classes)
