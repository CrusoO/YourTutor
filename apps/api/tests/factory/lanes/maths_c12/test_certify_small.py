# ruff: noqa: E501
"""End to end on a small box per template: certify, then the certificate is current."""

import copy

import pytest

from app.content.originality import ReferenceIndex
from app.factory.kernel import certificate_is_current
from app.factory.lanes.maths_c12.lane import LANE
from app.factory.runner import certify_lane_template

from .support import TEMPLATES, tuples


def small(template):
    picks = tuples(template, 2)
    out = copy.deepcopy(template)
    out["box"] = {
        name: {"choices": list(dict.fromkeys(p[name] for p in picks))} for name in template["box"]
    }
    return out


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["short"])
def test_template_certifies_on_a_small_box(template):
    report = certify_lane_template(LANE, small(template), reference_index=ReferenceIndex())
    assert report.kind == "exhaustive" and report.failures == 0 and report.ok >= 1, (
        report.failure_samples
    )
    assert report.certificate is not None and certificate_is_current(report.certificate.body)
