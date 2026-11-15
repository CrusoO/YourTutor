"""The 17 ordered checkers (design 3.1). Each reads an ItemContext and returns a CheckResult.

Real now: schema, rights (original items only), syllabus scope, well-posedness (kernel), units,
methods 1..n with independence groups, allowed-methods trace, key consistency, distractors, leak,
language, originality, dedupe, stamp (mints the kernel certificate; the tier is written later by
the stamp CLI). FAIL-CLOSED STUBS: `facts.lookup` and `diagram.package` fail any item that carries
facts or a diagram (those are excluded from auto-serving until their lanes exist).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from app.factory import kernel
from app.factory.kernel.exact import Reject, canon, chash, is_number_text
from app.factory.kernel.verify import answer_unit_ok, expected_dimension
from app.factory.registry import FAIL, NOT_APPLICABLE, PASS, SKIP, CheckResult, ItemContext

_ID = re.compile(r"^[A-Za-z0-9_.:-]{3,80}$")


class BaseChecker:
    id = ""
    version = "1"
    lanes: frozenset[str] = frozenset()
    FAULTS: tuple[str, ...] = ()

    def ok(self, **evidence: Any) -> CheckResult:
        return CheckResult(self.id, self.version, PASS, "ok", evidence)

    def bad(self, code: str, **evidence: Any) -> CheckResult:
        return CheckResult(self.id, self.version, FAIL, code, evidence)

    def na(self, code: str = NOT_APPLICABLE) -> CheckResult:
        return CheckResult(self.id, self.version, SKIP, code)

    def check(self, ctx: ItemContext) -> CheckResult:  # pragma: no cover - overridden
        raise NotImplementedError


class Schema(BaseChecker):
    id = "schema.strict"

    def check(self, ctx: ItemContext) -> CheckResult:
        if not _ID.match(ctx.item_id or ""):
            return self.bad("bad_item_id")
        if ctx.spec.get("domain") not in kernel.DOMAINS:
            return self.bad("unknown_domain", domain=str(ctx.spec.get("domain")))
        for name in ("spec", "answer", "witness"):
            if not isinstance(getattr(ctx, name), dict) or not getattr(ctx, name):
                return self.bad("empty_" + name)
        if len(ctx.hints) != 3 or not all(isinstance(h, str) and h for h in ctx.hints):
            return self.bad("needs_three_hints")
        if not ctx.stem.strip():
            return self.bad("empty_stem")
        if ctx.options:
            ids = [o.get("id") for o in ctx.options]
            if len(ids) < 3 or len(set(ids)) != len(ids) or ctx.key_option not in ids:
                return self.bad("bad_options")
        try:
            canon([ctx.spec, ctx.answer, ctx.witness])
        except Reject as rej:
            return self.bad(rej.code)  # a float or non-JSON value anywhere
        return self.ok()


class Rights(BaseChecker):
    id = "rights.gate"

    def check(self, ctx: ItemContext) -> CheckResult:
        if ctx.provenance.get("original") is not True:
            return self.bad("factory_items_must_be_original")
        if ctx.provenance.get("source_id"):
            return self.bad(
                "source_register_check_not_wired", source=str(ctx.provenance["source_id"])
            )
        if ctx.llm_involved and not ctx.provenance.get("llm_wording_only"):
            return self.bad("llm_may_only_draft_wording")
        return self.ok()


class SyllabusScope(BaseChecker):
    id = "syllabus.scope"

    def check(self, ctx: ItemContext) -> CheckResult:
        s = ctx.syllabus
        if not isinstance(s.get("grade"), int) or not s.get("chapter_ref") or not s.get("skill_id"):
            return self.bad("syllabus_fields_missing")
        if ctx.known_chapters is not None and s["chapter_ref"] not in ctx.known_chapters:
            return self.bad("unknown_chapter", chapter=str(s["chapter_ref"]))
        if set(s.get("forbidden_content", [])) & set(ctx.content_tags):
            return self.bad("forbidden_content")
        if s.get("number_domain") == "integers":
            leaves: list[str] = []
            _leaves(canon(ctx.answer), leaves)
            if any(is_number_text(x) and "/" in x for x in leaves):
                return self.bad("non_integer_answer_outside_scope")
        return self.ok()


def _leaves(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        for v in value.values():
            _leaves(v, out)
    elif isinstance(value, list):
        for v in value:
            _leaves(v, out)
    elif isinstance(value, str):
        out.append(value)


class WellPosed(BaseChecker):
    id = "wellposed.predicates"
    FAULTS = (
        "sign_flip",
        "wrong_constant",
        "unit_slip",
        "unit_dimension_slip",
        "off_by_one_atom",
        "dropped_root",
    )

    def check(self, ctx: ItemContext) -> CheckResult:
        ctx.verdict = kernel.verify(ctx.spec, ctx.answer, ctx.witness)
        if not ctx.verdict.accepted:
            return self.bad(ctx.verdict.code, detail=ctx.verdict.detail)
        return self.ok(checker_version=ctx.verdict.checker_version)


class Units(BaseChecker):
    id = "units.dimension"
    FAULTS = ("unit_dimension_slip",)

    def check(self, ctx: ItemContext) -> CheckResult:
        if expected_dimension(ctx.spec) is None:
            return self.na()
        ok, code = answer_unit_ok(ctx.spec, ctx.answer)
        return self.ok() if ok else self.bad(code)


class Method1(BaseChecker):
    id = "verify.method_1"
    FAULTS = ("method_wrong_answer",)

    def check(self, ctx: ItemContext) -> CheckResult:
        if not ctx.methods:
            return self.bad("no_independent_method")
        ctx.method_results = []
        return _run_methods(self, ctx, ctx.methods[:1])


class MethodsRest(BaseChecker):
    id = "verify.methods_2n"
    FAULTS = ("single_group",)

    def check(self, ctx: ItemContext) -> CheckResult:
        if len(ctx.method_results) < 1:
            return self.bad("method_1_did_not_run")
        res = _run_methods(self, ctx, ctx.methods[1:])
        if res.status != PASS:
            return res
        groups = {kernel.KERNEL_GROUP} | {m.independence_group for m in ctx.method_results}
        if len(groups) < 2:
            return self.bad("methods_not_independent", groups=sorted(groups))
        return self.ok(groups=sorted(groups))


def _run_methods(chk: BaseChecker, ctx: ItemContext, methods: list[Any]) -> CheckResult:
    want = chash(ctx.answer)
    for m in methods:
        try:
            got = m.solve(ctx.spec)
            if chash(got) != want:
                return chk.bad("method_disagreement", method=m.id)  # never majority-voted
        except Exception as exc:  # noqa: BLE001 - fail closed
            return chk.bad(f"method_error:{type(exc).__name__}", method=m.id)
        ctx.method_results.append(
            kernel.MethodResult(m.id, m.version, m.independence_group, got, m.technique)
        )
    return chk.ok(methods=[m.id for m in methods])


class AllowedMethods(BaseChecker):
    id = "syllabus.allowed_methods"

    def check(self, ctx: ItemContext) -> CheckResult:
        allowed = set(ctx.syllabus.get("allowed_methods", []))
        if not allowed:
            return self.bad("allowed_methods_undeclared")
        used = {m.technique for m in ctx.method_results if m.technique}
        if not used & allowed:
            return self.bad("no_allowed_technique_reproduces_answer", used=sorted(used))
        return self.ok(techniques=sorted(used & allowed))


class KeyConsistency(BaseChecker):
    id = "answer.key_consistency"
    FAULTS = ("swapped_option",)

    def check(self, ctx: ItemContext) -> CheckResult:
        if not ctx.options:
            return self.na()
        want = chash(ctx.answer)
        matching = [o["id"] for o in ctx.options if chash(o.get("value")) == want]
        if matching != [ctx.key_option]:
            return self.bad("key_option_is_not_the_verified_answer", matching=matching)
        return self.ok()


class Distractors(BaseChecker):
    id = "mcq.distractors"
    FAULTS = ("distractor_equals_key", "duplicate_distractor")

    def check(self, ctx: ItemContext) -> CheckResult:
        if not ctx.options:
            return self.na()
        wrong = [o for o in ctx.options if o["id"] != ctx.key_option]
        values = [chash(o.get("value")) for o in wrong]
        if chash(ctx.answer) in values:
            return self.bad("distractor_equals_key")
        if len(set(values)) != len(values):
            return self.bad("duplicate_distractors")
        if any(not o.get("procedure") for o in wrong):
            return self.bad("distractor_without_named_wrong_procedure")
        return self.ok(count=len(wrong))


class Leak(BaseChecker):
    id = "leak.hints"
    FAULTS = ("hint_leaks_key",)

    def check(self, ctx: ItemContext) -> CheckResult:
        from app.content.leak import hint_leaks_answer

        for level, hint in enumerate(ctx.hints[:2], start=1):
            for token in ctx.answer_tokens:
                if hint_leaks_answer(hint, token):
                    return self.bad("hint_reveals_answer", level=level)
        return self.ok()


class Language(BaseChecker):
    id = "language.lint"

    def check(self, ctx: ItemContext) -> CheckResult:
        from app.content.language import lint_item_texts

        errors, _ = lint_item_texts(stem=ctx.stem, hints=ctx.hints)
        return self.bad("lint_errors", errors=errors[:3]) if errors else self.ok()


class Facts(BaseChecker):
    id = "facts.lookup"

    def check(self, ctx: ItemContext) -> CheckResult:
        return self.bad("fact_items_not_auto_servable_yet") if ctx.facts is not None else self.na()


class Diagram(BaseChecker):
    id = "diagram.package"

    def check(self, ctx: ItemContext) -> CheckResult:
        return self.bad("diagram_items_need_engine_qa") if ctx.diagram is not None else self.na()


class Originality(BaseChecker):
    id = "originality.gate"

    def check(self, ctx: ItemContext) -> CheckResult:
        from app.content.originality import OriginalityStatus, item_text, score_text

        if ctx.reference_index is None:
            return self.bad("no_reference_index")  # fail closed: a missing check is not a pass
        text = item_text(ctx.stem, [str(o.get("text", "")) for o in ctx.options])
        score = score_text(text, ctx.reference_index)
        if score.status is not OriginalityStatus.passed:
            return self.bad("too_close_to_reference", reasons=list(score.reasons))
        return self.ok()


class Dedupe(BaseChecker):
    id = "dedupe"

    def check(self, ctx: ItemContext) -> CheckResult:
        from app.content.signatures import structure_signature

        if chash(ctx.spec) in ctx.bank_spec_hashes:
            return self.bad("same_problem_already_in_bank")
        if structure_signature(ctx.stem) in ctx.bank_signatures:
            return self.bad("same_stem_structure_already_in_bank")
        return self.ok()


class Stamp(BaseChecker):
    id = "stamp"

    def check(self, ctx: ItemContext) -> CheckResult:
        try:
            ctx.certificate = kernel.mint_item_certificate(
                ctx.item_id,
                ctx.spec,
                ctx.answer,
                ctx.witness,
                methods=ctx.method_results,
                plugins=ctx.plugin_verdicts,
            )
        except kernel.CertificationRefused as refusal:
            return self.bad("certification_refused", reasons=refusal.reasons)
        return self.ok(certificate_hash=ctx.certificate.hash)


ORDER: tuple[Callable[[], BaseChecker], ...] = (
    Schema, Rights, SyllabusScope, WellPosed, Units, Method1, MethodsRest, AllowedMethods,
    KeyConsistency, Distractors, Leak, Language, Facts, Diagram, Originality, Dedupe, Stamp,
)  # fmt: skip
