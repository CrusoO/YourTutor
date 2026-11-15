"""The loop end to end: construct backward, solve forward, verify, certify a whole box."""

import copy

from app.content.originality import ReferenceIndex
from app.factory.kernel import certificate_is_current
from app.factory.lanes.maths_quadratic import LANE, TEMPLATE
from app.factory.runner import build_item, certify_lane_template, run_item, template_hash

SMALL = copy.deepcopy(TEMPLATE)
SMALL["box"] = {"a": {"choices": [1, 2]}, "r1": {"min": -4, "max": 4}, "r2": {"min": -4, "max": 4}}


def test_backward_construction_then_forward_check():
    ctx, result = run_item(
        LANE, TEMPLATE, {"a": 2, "r1": -3, "r2": 5}, reference_index=ReferenceIndex()
    )
    assert ctx.stem == "Solve the equation 2x^2 - 4x - 30 = 0."
    assert ctx.spec["lhs"] == [-30, -4, 2] and ctx.answer == {"roots": ["-3", "5"], "count": 2}
    assert [o["procedure"] for o in ctx.options] == [
        "correct",
        "sign_error",
        "one_root_only",
        "sum_product_confusion",
    ]
    assert result.stampable and certificate_is_current(ctx.certificate.body)
    assert {m["independence_group"] for m in ctx.certificate.body["methods"]} == {
        "kernel.exact",
        "closed_form",
        "enumeration",
    }


def test_template_certified_over_the_whole_box():
    report = certify_lane_template(LANE, SMALL, reference_index=ReferenceIndex())
    assert report.kind == "exhaustive" and report.size == 2 * 9 * 9 and report.failures == 0
    assert report.ok > 0 and report.refused == []
    assert (
        report.skip_reasons["needs_two_distinct_roots_in_order"] > 0
    )  # ill-posed tuples are counted
    body = report.certificate.body
    assert body["subject"]["template_hash"] == template_hash(LANE, SMALL)
    assert body["outcomes"]["failures"] == "0" and len(body["checker_versions"]) == 17


def test_a_buggy_lane_cannot_be_certified():
    class Buggy(type(LANE)):
        def render(self, template, params):
            ctx = super().render(template, params)
            ctx.witness["split"]["lead"] = 5  # the generator's witness is wrong for every tuple
            return ctx

    report = certify_lane_template(Buggy(), SMALL, reference_index=ReferenceIndex())
    assert report.certificate is None and report.failures == report.ok + report.failures > 0
    assert report.failure_samples[0]["reason"].startswith("wellposed.predicates:")


def test_student_answers():
    ctx = build_item(LANE, TEMPLATE, {"a": 1, "r1": -2, "r2": 3})
    assert LANE.check_student_answer(ctx, "3, -2") and LANE.check_student_answer(ctx, "x=-2, x=3")
    assert not LANE.check_student_answer(ctx, "3") and not LANE.check_student_answer(ctx, "abc")


def test_well_posed_refusals():
    assert (
        LANE.well_posed(TEMPLATE, {"a": 1, "r1": 3, "r2": 3}) == "needs_two_distinct_roots_in_order"
    )
    assert LANE.well_posed(TEMPLATE, {"a": 1, "r1": 0, "r2": 3}) == "zero_root_is_a_different_skill"
    assert LANE.well_posed(TEMPLATE, {"a": 1, "r1": -2, "r2": 3}) is None
