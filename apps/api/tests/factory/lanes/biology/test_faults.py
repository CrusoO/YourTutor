"""Seeded faults: 100 percent kill rate per class, for the whole pipeline and per named checker."""

import pytest

from app.content.originality import ReferenceIndex
from app.factory.faults import run_fault_injection
from app.factory.lanes.biology.faultset import ALL_FAULTS, LANE_FAULTS, fault_cases
from app.factory.lanes.biology.lane import LANE
from app.factory.lanes.biology.templates import all_templates

from .helpers import first


def _extra_cases():
    """Ratio and probability items are always in the sample, so every class is applied."""
    cases = []
    for model_id, fixed in (
        ("HERED.MONO_RATIO", {"cross": "Hh,Hh", "variant": "phen_ratio"}),
        ("HERED.DI_RATIO", {"cross": "HhGg,HhGg"}),
        ("HERED.DI_RATIO", {"cross": "HhGg,Hhgg"}),
        ("HERED.TEST_CROSS", {"key": "HHGg"}),
        ("HERED.MONO_PROB", {"cross": "Hh,Hh", "variant": "p_rec"}),
        ("HERED.SEX_SEQ", {"variant": "exactly_k", "n": "4", "k": "2"}),
        ("ENV.TEN_PERCENT", {"variant": "level_n", "n": "4"}),
        ("REPRO.FISSION", {"variant": "time_needed", "n": "5"}),
        ("LIFE.RATES", {"variant": "time", "tu": "h"}),
    ):
        ctx = LANE.render(all_templates()[model_id], first(model_id, **fixed))
        ctx.reference_index = ReferenceIndex()
        cases.append(ctx)
    return cases


@pytest.fixture(scope="module")
def report():
    return run_fault_injection(fault_cases(2) + _extra_cases(), ALL_FAULTS)


def test_baseline_items_are_all_accepted(report):
    assert report.baseline_failures == []


def test_every_class_is_applied_often_enough(report):
    assert {f.id for f in ALL_FAULTS} == set(report.classes)
    for name, row in report.classes.items():
        assert row.applied >= 3, f"{name} applied only {row.applied} times"


@pytest.mark.parametrize("fault", [f.id for f in ALL_FAULTS])
def test_kill_rate_is_100_percent(report, fault):
    row = report.classes[fault]
    assert row.killed == row.applied, f"survivors: {row.survivors[:5]}"
    for checker_id, (applied, killed) in row.by_checker.items():
        assert applied == killed, f"{checker_id} missed {applied - killed} {fault} mutants"


def test_report_is_perfect_and_names_every_lane_class(report):
    assert report.perfect and {f.id for f in LANE_FAULTS} <= set(report.classes)
