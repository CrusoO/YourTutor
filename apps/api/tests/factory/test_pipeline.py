import copy

import pytest

from app.content.originality import ReferenceIndex
from app.factory.checkers import ORDER, stem_identity
from app.factory.kernel.exact import chash
from app.factory.pipeline import default_checkers, run
from app.factory.registry import FAIL, PASS, REGISTRY, SKIP, Checker, Lane, Method

from .corpus import corpus, quadratic

ORDER_IDS = [
    "schema.strict", "rights.gate", "syllabus.scope", "wellposed.predicates", "units.dimension",
    "verify.method_1", "verify.methods_2n", "syllabus.allowed_methods", "answer.key_consistency",
    "mcq.distractors", "leak.hints", "language.lint", "facts.lookup", "diagram.package",
    "originality.gate", "dedupe", "stamp",
]  # fmt: skip


def test_seventeen_checkers_in_the_designed_order():
    checkers = default_checkers()
    assert [c.id for c in checkers] == ORDER_IDS and len(ORDER) == 17
    assert all(isinstance(c, Checker) for c in checkers)


def test_good_items_are_stampable_in_every_domain():
    for ctx in corpus():
        result = run(ctx)
        assert result.stampable, (ctx.item_id, result.first_failure)
        assert ctx.certificate is not None and len(result.results) == 17


def test_not_applicable_checks_are_skips_with_a_reason():
    result = run(quadratic(1, -2, 3))
    by_id = {r.checker_id: r for r in result.results}
    assert (
        by_id["units.dimension"].status == SKIP
        and by_id["units.dimension"].code == "not_applicable"
    )
    assert by_id["facts.lookup"].code == "not_applicable" == by_id["diagram.package"].code
    assert by_id["stamp"].status == PASS


def test_first_failure_stops_the_item():
    ctx = quadratic(1, -2, 3)
    ctx.answer = {"roots": ["1"], "count": 1}
    result = run(ctx)
    assert result.first_failure.checker_id == "wellposed.predicates"
    tail = [r for r in result.results if r.code == "not_run"]
    assert (
        tail and tail[-1].checker_id == "stamp" and not result.stampable and ctx.certificate is None
    )


@pytest.mark.parametrize(
    ("mutate", "checker", "code"),
    [
        (lambda c: setattr(c, "item_id", "x"), "schema.strict", "bad_item_id"),
        (lambda c: setattr(c, "hints", ["only one"]), "schema.strict", "needs_three_hints"),
        (
            lambda c: setattr(c, "provenance", {"original": False}),
            "rights.gate",
            "factory_items_must_be_original",
        ),
        (
            lambda c: setattr(c, "provenance", {"original": True, "source_id": "S"}),
            "rights.gate",
            "source_register_check_not_wired",
        ),
        (lambda c: setattr(c, "llm_involved", True), "rights.gate", "llm_may_only_draft_wording"),
        (lambda c: c.syllabus.pop("chapter_ref"), "syllabus.scope", "syllabus_fields_missing"),
        (lambda c: setattr(c, "known_chapters", {"other"}), "syllabus.scope", "unknown_chapter"),
        (
            lambda c: (
                c.syllabus.update(forbidden_content=["calculus"])
                or c.content_tags.append("calculus")
            ),
            "syllabus.scope",
            "forbidden_content",
        ),
        (
            lambda c: c.syllabus.update(allowed_methods=["completing_square"]),
            "syllabus.allowed_methods",
            "no_allowed_technique_reproduces_answer",
        ),
        (
            lambda c: c.syllabus.update(allowed_methods=[]),
            "syllabus.allowed_methods",
            "allowed_methods_undeclared",
        ),
        (lambda c: setattr(c, "methods", []), "verify.method_1", "no_independent_method"),
        (
            lambda c: setattr(c, "facts", {"nodes": ["F.1"]}),
            "facts.lookup",
            "fact_items_not_auto_servable_yet",
        ),
        (
            lambda c: setattr(c, "diagram", {"figure": "x"}),
            "diagram.package",
            "diagram_items_need_engine_qa",
        ),
        (lambda c: setattr(c, "reference_index", None), "originality.gate", "no_reference_index"),
        (
            lambda c: setattr(c, "stem", "Solve it {x} and and again."),
            "language.lint",
            "lint_errors",
        ),
        (
            lambda c: c.options[1].update(procedure=""),
            "mcq.distractors",
            "distractor_without_named_wrong_procedure",
        ),
    ],
)
def test_each_gate_fails_closed(mutate, checker, code):
    ctx = quadratic(1, -2, 3)
    mutate(ctx)
    result = run(ctx)
    failure = result.first_failure
    assert failure is not None and (failure.checker_id, failure.code) == (checker, code), failure
    assert not result.stampable


def test_syllabus_number_domain_blocks_fractions():
    ctx = quadratic(2, 1, 3)  # roots 1 and 3, integers: fine
    assert run(ctx).stampable
    ctx = quadratic(2, 1, 3)
    ctx.syllabus["number_domain"] = "integers"
    ctx.answer = {"roots": ["1/2"], "count": 1}  # not our concern: scope runs before well-posedness
    assert run(ctx).first_failure.code == "non_integer_answer_outside_scope"


def test_dedupe_rejects_a_repeat_of_the_same_problem():
    first = quadratic(1, -2, 3)
    twin = quadratic(1, -2, 3)
    twin.bank_spec_hashes = {chash(first.spec)}
    assert run(twin).first_failure.code == "same_problem_already_in_bank"
    sib = quadratic(1, -2, 4)
    sib.bank_stems = {stem_identity(sib.stem.upper() + "  ")}
    assert run(sib).first_failure.code == "same_stem_already_in_bank"
    assert run(quadratic(1, -2, 4)).stampable  # a different stem of the same shape is fine


def test_originality_blocks_copied_text():
    ctx = quadratic(1, -2, 3)
    idx = ReferenceIndex()
    idx.add_text(ctx.stem + "\n" + "\n".join(str(o["text"]) for o in ctx.options))
    ctx.reference_index = idx
    assert run(ctx).first_failure.code == "too_close_to_reference"


def test_checker_exception_fails_closed():
    class Boom:
        id, version, lanes, FAULTS = "boom", "1", frozenset(), ()

        def check(self, ctx):
            raise RuntimeError("x")

    result = run(quadratic(1, -2, 3), [Boom()])
    assert (
        result.results[0].status == FAIL
        and result.results[0].code == "checker_exception:RuntimeError"
    )


def test_lane_checker_runs_before_the_stamp_and_can_veto():
    class Veto:
        id, version, lanes, FAULTS = "lane.veto", "1", frozenset({"maths"}), ()

        def check(self, ctx):
            from app.factory.registry import CheckResult

            return CheckResult(self.id, self.version, FAIL, "lane_says_no")

    result = run(quadratic(1, -2, 3), extra=[Veto()])
    assert result.first_failure.checker_id == "lane.veto" and not result.stampable
    other = copy.deepcopy(quadratic(1, -2, 3))
    other.lane = "physics"
    assert run(other, extra=[Veto()]).stampable  # lane filter respected


def test_registry_and_protocols():
    from app.factory.lanes.maths_quadratic import LANE
    from app.factory.lanes.reference import QuadraticFormula

    assert REGISTRY.lanes["maths"] is LANE and isinstance(LANE, Lane)
    assert isinstance(QuadraticFormula(), Method)
