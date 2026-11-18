"""Plain-language lint for hints, step explanations and misconception messages.

Owner rule: what a learner reads after a wrong answer must be simple, everyday language (about
Class 7). Thresholds and the jargon list live in `config/plain_language.yaml`.

Rules (id, severity):
- PL.SENTENCE_LONG, PL.READING_LEVEL, PL.JARGON: warnings, reported as counts.
- PL.MC_NOT_EVERYDAY: a misconception message that does not say what the learner did.
- PL.HINT_STATES_ANSWER: error, hint 1 or 2 gives the final answer away (hint 3 is the full
  method, so a hint 3 that does is the warning PL.HINT3_STATES_ANSWER).
- PL.MC_NOT_OWN: error, a factory item's wrong option names a misconception that is not one of
  the skill's own. Hand-authored items (the legacy pack) only get the warning
  PL.MC_NOT_OWN_HAND_AUTHORED: they are reported, never edited by this rule.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from app.content.leak import hint_leaks_answer
from app.content.schema import Item, ItemType, Misconception, Skill

ERROR_RULES = frozenset({"PL.HINT_STATES_ANSWER", "PL.MC_NOT_OWN"})
_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+(?=[A-Z])|\n+")
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
_VOWEL_GROUP = re.compile(r"[aeiouy]+")


@dataclass(frozen=True)
class PlainRules:
    max_sentence_words: int
    max_grade_level: float
    min_words_for_grade: int
    explain_window: int
    explain_markers: tuple[str, ...]
    jargon: tuple[str, ...]
    misconception_openers: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    rule: str
    owner: str  # item id or misconception id
    text: str
    detail: str = ""
    score: float = 0.0  # how bad: used to pick the worst examples

    @property
    def is_error(self) -> bool:
        return self.rule in ERROR_RULES


@dataclass
class PlainReport:
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.is_error]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if not f.is_error]

    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(f.rule for f in self.findings).items()))


def load_plain_rules(config_dir: Path | None = None) -> PlainRules:
    from app.registries.paths import config_dir as default_config_dir

    path = (config_dir or default_config_dir()) / "plain_language.yaml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PlainRules(
        max_sentence_words=int(raw["max_sentence_words"]),
        max_grade_level=float(raw["max_grade_level"]),
        min_words_for_grade=int(raw["min_words_for_grade"]),
        explain_window=int(raw["explain_window"]),
        explain_markers=tuple(str(m).lower() for m in raw["explain_markers"]),
        jargon=tuple(str(j).lower() for j in raw["jargon"]),
        misconception_openers=tuple(str(o).lower() for o in raw["misconception_openers"]),
    )


@cache
def default_rules() -> PlainRules:
    return load_plain_rules()


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def word_count(sentence: str) -> int:
    """Words in a sentence; numbers and symbols (a formula) do not count as reading effort."""
    return len(_WORD.findall(sentence))


def _syllables(word: str) -> int:
    lower = word.lower().strip("'-")
    count = len(_VOWEL_GROUP.findall(lower))
    if lower.endswith("e") and not lower.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(count, 1)


def grade_level(text: str) -> float | None:
    """Flesch-Kincaid grade of the words in a text; None when there are no words."""
    words = _WORD.findall(text)
    sents = [s for s in sentences(text) if word_count(s)]
    if not words or not sents:
        return None
    syllables = sum(_syllables(w) for w in words)
    return 0.39 * len(words) / len(sents) + 11.8 * syllables / len(words) - 15.59


def unexplained_jargon(text: str, rules: PlainRules) -> list[str]:
    """Jargon words used without an explaining marker shortly after them."""
    lower = text.lower()
    found: list[str] = []
    for term in rules.jargon:
        for match in re.finditer(rf"(?<![a-z]){re.escape(term)}(?![a-z])", lower):
            tail = lower[match.end() : match.end() + rules.explain_window]
            if not any(marker in tail for marker in rules.explain_markers):
                found.append(term)
                break
    return found


def lint_reading(text: str, owner: str, rules: PlainRules) -> list[Finding]:
    out: list[Finding] = []
    for sentence in sentences(text):
        if word_count(sentence) > rules.max_sentence_words:
            out.append(
                Finding("PL.SENTENCE_LONG", owner, sentence, f"{word_count(sentence)} words")
            )
            break
    if len(_WORD.findall(text)) >= rules.min_words_for_grade:
        grade = grade_level(text)
        if grade is not None and grade > rules.max_grade_level:
            out.append(Finding("PL.READING_LEVEL", owner, text, f"grade {grade:.1f}", grade))
    for term in unexplained_jargon(text, rules):
        out.append(Finding("PL.JARGON", owner, text, term, 1.0))
    return out


def lint_misconception_message(mc: Misconception, rules: PlainRules) -> list[Finding]:
    text = mc.explanation.en
    out = lint_reading(text, mc.id, rules)
    if not text.strip().lower().startswith(rules.misconception_openers):
        out.append(Finding("PL.MC_NOT_EVERYDAY", mc.id, text, "does not start with 'You ...'"))
    return out


def key_texts(item: Item) -> list[str]:
    """The final answer as written: the key option's text for a multiple-choice item."""
    values = [item.answer.sympy, *item.answer.accept]
    if item.type == ItemType.mcq:
        key = next((o.en for o in item.options if o.id == item.answer.sympy), None)
        values = ([key] if key else []) + list(item.answer.accept)
    return [v for v in values if v]


def lint_item_plain(item: Item, rules: PlainRules, *, check_leaks: bool = True) -> list[Finding]:
    """`check_leaks=False` skips the (slow) answer-equivalence test; the validator already runs it
    for hints 1 and 2 as its own error."""
    out: list[Finding] = []
    keys = key_texts(item) if check_leaks else []
    for hint in item.hints:
        out.extend(lint_reading(hint.en, item.id, rules))
        if any(hint_leaks_answer(hint.en, key) for key in keys):
            rule = "PL.HINT_STATES_ANSWER" if hint.level < 3 else "PL.HINT3_STATES_ANSWER"
            out.append(Finding(rule, item.id, hint.en, f"hint level {hint.level}", 100.0))
    for step in item.solution_steps:
        out.extend(lint_reading(step.en, item.id, rules))
    return out


def own_misconception_ids(item: Item, skills: dict[str, Skill]) -> set[str]:
    own: set[str] = set()
    for skill_id in item.skill_ids:
        skill = skills.get(skill_id)
        if skill is not None:
            own.update(skill.misconceptions)
    return own


def misconception_mismatches(items: Iterable[Item], skills: Iterable[Skill]) -> list[Finding]:
    """Wrong-option misconception ids that are not among the item skill's own misconceptions."""
    by_id = {s.id: s for s in skills}
    out: list[Finding] = []
    for item in items:
        own = own_misconception_ids(item, by_id)
        for rule in item.misconception_rules:
            if rule.id not in own:
                kind = "PL.MC_NOT_OWN" if item.template_id else "PL.MC_NOT_OWN_HAND_AUTHORED"
                detail = f"skills {','.join(item.skill_ids)}"
                out.append(Finding(kind, item.id, rule.id, detail, 100.0))
    return out


def lint_bundle_plain(
    items: Iterable[Item],
    skills: Iterable[Skill],
    misconceptions: Iterable[Misconception],
    rules: PlainRules | None = None,
    *,
    check_leaks: bool = True,
) -> PlainReport:
    use = rules or default_rules()
    skill_list = list(skills)
    item_list = list(items)
    report = PlainReport()
    for item in item_list:
        report.findings.extend(lint_item_plain(item, use, check_leaks=check_leaks))
    for mc in misconceptions:
        report.findings.extend(lint_misconception_message(mc, use))
    report.findings.extend(misconception_mismatches(item_list, skill_list))
    return report


def worst_examples(report: PlainReport, limit: int = 10) -> list[Finding]:
    """The worst findings: errors first, then by score; one per rule and text (templates repeat)."""
    seen: set[tuple[str, str]] = set()
    ranked = sorted(report.findings, key=lambda f: (not f.is_error, -f.score, f.owner))
    out: list[Finding] = []
    for finding in ranked:
        key = (finding.rule, finding.text)
        if key in seen:
            continue
        seen.add(key)
        out.append(finding)
        if len(out) == limit:
            break
    return out


def format_counts(report: PlainReport) -> str:
    lines = ["Plain-language report"]
    counts = report.counts()
    for rule, count in counts.items():
        kind = "error" if rule in ERROR_RULES else "warning"
        lines.append(f"  {rule}: {count} ({kind})")
    if not counts:
        lines.append("  no findings")
    return "\n".join(lines)
