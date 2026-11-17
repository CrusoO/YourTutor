"""Plugin interfaces: Checker, Method, Lane, plus the context a checker reads.

Lanes (maths, physics, chemistry, biology) add Methods, Checkers and a Lane object through the
registry. They never touch kernel files. Everything a plugin returns is DATA: a CheckResult can
reject, but only the kernel can mint the certificate that the stamp step needs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.factory.kernel import Certificate, MethodResult, Verdict

PASS, FAIL, SKIP = "pass", "fail", "skip"
NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class CheckResult:
    checker_id: str
    version: str
    status: str  # pass | fail | skip
    code: str = "ok"  # stable machine code; "not_applicable" or "not_run" for a skip
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ItemContext:
    """One item draft as the checker stack sees it. Everything is plain data except `methods`."""

    item_id: str
    lane: str
    spec: dict[str, Any]
    answer: dict[str, Any]
    witness: dict[str, Any]
    stem: str = ""
    skill_ids: list[str] = field(default_factory=list)  # defaults to [syllabus["skill_id"]]
    difficulty: float = 0.5
    role: str = "apply"
    steps: list[str] = field(default_factory=list)  # worked solution, without the final line
    prediction: str = ""
    hints: list[str] = field(default_factory=list)
    options: list[dict[str, Any]] = field(default_factory=list)  # {id, value, procedure}
    key_option: str | None = None
    # Numeric and expression items (no options): the type to stamp, the answer string the learner
    # types (must parse through app.content.math_parse), extra accepted spellings, an optional
    # `verify` spec for the schema, and the named wrong answers: {text, procedure}.
    item_type: str = ""  # "" or "mcq" with options; "numeric" | "expression" without
    answer_text: str = ""
    accept: list[str] = field(default_factory=list)
    verify: Any = None
    wrong_answers: list[dict[str, Any]] = field(default_factory=list)
    answer_tokens: list[str] = field(default_factory=list)  # strings a hint must not reveal
    provenance: dict[str, Any] = field(default_factory=dict)
    syllabus: dict[str, Any] = field(default_factory=dict)
    content_tags: list[str] = field(default_factory=list)
    llm_involved: bool = False
    facts: dict[str, Any] | None = None  # fact-graph items: held out of auto-serving
    diagram: dict[str, Any] | None = None  # diagram items: held out of auto-serving
    methods: list[Method] = field(default_factory=list)
    plugin_verdicts: list[Any] = field(default_factory=list)
    # Bank-level inputs supplied by the caller
    known_chapters: set[str] | None = None
    reference_index: Any = None  # app.content.originality.ReferenceIndex
    bank_stems: set[str] = field(default_factory=set)  # checkers.stem_identity() of bank stems
    bank_spec_hashes: set[str] = field(default_factory=set)
    # Filled in by the pipeline
    verdict: Verdict | None = None
    method_results: list[MethodResult] = field(default_factory=list)
    certificate: Certificate | None = None


@runtime_checkable
class Method(Protocol):
    """An independent computation of the answer FROM THE SPEC ALONE (never from the witness).

    Two methods in one independence group count once: use a different formulation, library or
    algorithm, not a second copy of the same code.
    """

    id: str
    version: str
    independence_group: str
    technique: str  # a syllabus technique id (allowed_methods vocabulary), or ""

    def solve(self, spec: Mapping[str, Any]) -> Any: ...


@runtime_checkable
class Checker(Protocol):
    id: str
    version: str
    lanes: frozenset[str]  # empty = every lane
    FAULTS: tuple[str, ...]  # fault classes this checker must reject on its own (faults.py)

    def check(self, ctx: ItemContext) -> CheckResult: ...


@runtime_checkable
class Lane(Protocol):
    """What a subject lane implements. See apps/api/app/factory/lanes/maths_quadratic.py."""

    name: str
    domain: str  # kernel domain: algebra | stoichiometry | kinematics | genetics

    def box(self, template: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
        """Declared parameter box for certification."""
        ...

    def well_posed(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
        """None if the tuple makes a good item, else a reason (counted as skipped, not hidden)."""
        ...

    def render(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> ItemContext: ...

    def check_student_answer(self, item: ItemContext, response: str) -> bool: ...


class Registry:
    def __init__(self) -> None:
        self.checkers: dict[str, Checker] = {}
        self.methods: dict[str, Method] = {}
        self.lanes: dict[str, Lane] = {}

    def register_checker(self, checker: Checker) -> Checker:
        self.checkers[checker.id] = checker
        return checker

    def register_method(self, method: Method) -> Method:
        self.methods[method.id] = method
        return method

    def register_lane(self, lane: Lane) -> Lane:
        self.lanes[lane.name] = lane
        return lane


REGISTRY = Registry()


def register_lane(lane: Lane) -> Lane:
    return REGISTRY.register_lane(lane)


def register_checker(checker: Checker) -> Checker:
    return REGISTRY.register_checker(checker)


def register_method(method: Method) -> Method:
    return REGISTRY.register_method(method)


MethodFactory = Callable[[], Sequence[Method]]
