# ruff: noqa: E501
"""Fault injection over the Class 12 maths lane: every seeded fault class must be killed."""

import pytest

from app.factory.lanes.maths_c12.faults import LANE_FAULTS, run_lane_fault_injection


@pytest.fixture(scope="module")
def report():
    return run_lane_fault_injection(per_template=2)


def test_baseline_items_all_accepted(report):
    assert report.baseline_failures == []


@pytest.mark.parametrize("fault", [f.id for f in LANE_FAULTS])
def test_kill_rate_is_100_percent(report, fault):
    row = report.classes[fault]
    assert row.applied >= 3, f"{fault} applied only {row.applied} times"
    assert row.killed == row.applied, f"survivors: {row.survivors[:5]}"
    for checker_id, (applied, killed) in row.by_checker.items():
        assert applied == killed, f"{checker_id} missed {applied - killed} {fault} mutants"


def test_report_is_perfect(report):
    assert report.perfect and report.report_id.startswith("FI-")
