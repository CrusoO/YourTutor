# ruff: noqa: E501
"""End to end on a small box per template: certify, then the certificate is current."""

import copy

import pytest

from app.content.originality import ReferenceIndex
from app.factory.kernel import certificate_is_current
from app.factory.lanes.maths.lane import LANE
from app.factory.runner import certify_lane_template

from .support import TEMPLATES, tuples


def small(template):
    """A box built from two known-good tuples: at least those two are accepted."""
    picks = tuples(template, 2)
    box = {}
    for name in template["box"]:
        values = []
        for p in picks:
            if p[name] not in values:
                values.append(p[name])
        box[name] = {"choices": values}
    out = copy.deepcopy(template)
    out["box"] = box
    return out


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["short"])
def test_template_certifies_on_a_small_box(template):
    t = small(template)
    report = certify_lane_template(LANE, t, reference_index=ReferenceIndex())
    assert report.kind == "exhaustive" and report.failures == 0 and report.ok >= 1, (
        report.failure_samples
    )
    assert report.certificate is not None and certificate_is_current(report.certificate.body)
    groups = {m for m in report.certificate.body["checker_versions"]}
    assert len(groups) == 17
