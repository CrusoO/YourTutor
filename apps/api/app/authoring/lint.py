"""Deterministic lint of draft files. No model, no network. Reports; the exit code is the verdict.

Severity `error` means the item (or file) is not compiled. `warning` is shown but does not block.
Nothing here checks that a keyed answer is true: that is what the reviewers are for.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.authoring.compile import compile_item
from app.authoring.files import draft_files, drafts_root, read_draft
from app.authoring.hooks import NUMERIC_RECHECKS, NumericRecheck
from app.authoring.schema import SUBJECTS, DraftFile, DraftItem
from app.authoring.syllabus import MapTopic, SyllabusMap, load_map

STEM_MIN_CHARS = 12
STEM_MAX_CHARS = 450
NEAR_DUPLICATE = 0.85
ITEMS_PER_TOPIC = 6

# Board, exam, publisher, book and author names must not appear anywhere in a draft. The repo has
# no shared list (the rights gate works on the source register), so this one is the authoring
# lint's own. Word-boundary, case-insensitive.
BANNED_NAMES = (
    "cbse",
    "ncert",
    "icse",
    "cisce",
    "nios",
    "state board",
    "board exam",
    "board paper",
    "previous year",
    "pyq",
    "jee",
    "neet",
    "cuet",
    "olympiad",
    "textbook",
    "text book",
    "reference book",
    "exemplar",
    "s chand",
    "schand",
    "arihant",
    "oswaal",
    "rd sharma",
    "r d sharma",
    "rs aggarwal",
    "r s aggarwal",
    "hc verma",
    "h c verma",
    "dc pandey",
    "d c pandey",
    "mtg",
    "cengage",
    "pearson",
    "oxford",
    "cambridge",
    "macmillan",
    "wiley",
    "mcgraw",
    "lakhmir",
    "pradeep",
    "siyavula",
    "openstax",
    "khan academy",
    "byju",
    "vedantu",
    "unacademy",
)
_BANNED = re.compile(r"\b(" + "|".join(re.escape(n) for n in BANNED_NAMES) + r")\b", re.IGNORECASE)
_BAD_PHRASES = re.compile(
    r"all of the above|none of the above|all of these|none of these|both [a-d] and [a-d]\b"
    r"|assertion|\breason \(r\)|\bstatement i\b|which of the following (?:is|are) not",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_PLAIN_NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")  # 1.34e-5 is one number
_WORD = re.compile(r"[a-z0-9]+")
_MATH = re.compile(r"\d+(?:\.\d+)?|[^\sa-z\d]")
_PUNCTUATION = frozenset(".,;:?!\"'")
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Finding:
    file: str
    item: int | None  # 0-based position in the draft, None for file-level findings
    topic: str
    code: str
    severity: str  # error | warning | info
    message: str


@dataclass
class FileResult:
    path: str
    draft: DraftFile | None = None
    findings: list[Finding] = field(default_factory=list)
    topics: dict[str, MapTopic] = field(default_factory=dict)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    def bad_items(self) -> set[int]:
        return {f.item for f in self.errors if f.item is not None}

    @property
    def file_blocked(self) -> bool:
        """A file-level error (schema, syllabus) blocks the whole file."""
        return self.draft is None or any(f.item is None for f in self.errors)


def normalise_option(text: str) -> str:
    text = text.replace("−", "-").casefold()
    text = _SPACE.sub(" ", text).strip().strip("\"'").strip()
    return text.rstrip(".,;:")


def tokens(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.casefold()))


def math_signature(text: str) -> list[str]:
    """The numbers and symbols of a stem, sorted, without plain punctuation: `dy/dx = 2y` and
    `dy/dx + 2y = 0` differ here, a stem with a sentence added does not."""
    found = _MATH.findall(text.casefold().replace("\u2212", "-"))
    return sorted(t for t in found if t not in _PUNCTUATION)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _leaks(hint: str, correct: str, numeric: bool) -> bool:
    """True when the hint states the keyed answer: the same text as a whole word run, or (for a
    number) the same value."""
    answer = normalise_option(correct)
    if not answer:
        return False
    low = hint.replace("−", "-").casefold()
    if numeric and _PLAIN_NUMBER.fullmatch(answer):
        try:
            value = float(answer)
        except ValueError:
            return False
        return any(float(m) == value for m in _NUMBER.findall(low))
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(answer)}(?![a-z0-9])", low))


def _sig_figs(text: str) -> int:
    digits = re.sub(r"[^0-9]", "", text).lstrip("0")
    return len(digits.rstrip("0")) if "." not in text else len(digits)


def lint_item(
    file: str,
    position: int,
    item: DraftItem,
    topic: MapTopic | None,
    draft: DraftFile,
    rechecks: list[NumericRecheck],
) -> list[Finding]:
    out: list[Finding] = []

    def add(code: str, severity: str, message: str) -> None:
        out.append(Finding(file, position, item.topic, code, severity, message))

    stem_len = len(item.stem.strip())
    if stem_len < STEM_MIN_CHARS or stem_len > STEM_MAX_CHARS:
        add(
            "stem_length",
            "error",
            f"stem is {stem_len} characters (allowed {STEM_MIN_CHARS}-{STEM_MAX_CHARS})",
        )
    texts = [item.stem, item.correct, item.explanation, *item.hints, item.diagram or ""]
    for wrong in item.wrong:
        texts.extend([wrong.text, wrong.mistake])
    hit = next((m.group(0) for t in texts if (m := _BANNED.search(t))), None)
    if hit:
        add("banned_name", "error", f"board, exam, publisher or book name {hit!r} is not allowed")
    phrase = next(
        (
            m.group(0)
            for t in [item.stem, item.correct, *(w.text for w in item.wrong)]
            if (m := _BAD_PHRASES.search(t))
        ),
        None,
    )
    if phrase:
        add(
            "bad_phrase",
            "error",
            f"{phrase!r} is not allowed (one defensible answer, no assertion-reason)",
        )
    numeric = item.type == "numeric"
    if item.type == "mcq":
        options = [item.correct, *(w.text for w in item.wrong)]
        normal = [normalise_option(o) for o in options]
        if len(set(normal)) != 4:
            add("options_not_distinct", "error", "the 4 options are not distinct after normalising")
        if normal.count(normal[0]) != 1:
            add("correct_not_unique", "error", "the correct option appears more than once")
        mistakes = [norm_mistake(w.mistake) for w in item.wrong]
        if len(set(mistakes)) != len(mistakes):
            add("same_mistake", "warning", "two wrong options give the same mistake")
    else:
        answer = item.correct.strip().replace("−", "-")
        if not _PLAIN_NUMBER.fullmatch(answer):
            add("numeric_parse", "error", f"keyed answer {item.correct!r} is not one plain number")
        elif _sig_figs(answer) > 3:
            add(
                "numeric_precision",
                "warning",
                f"keyed answer {answer!r} has more than 3 significant figures",
            )
        for check in rechecks:
            result = check(stem=item.stem, correct=item.correct, unit=item.unit)
            if result is not None:
                tag = "agrees" if result.agrees else "DISAGREES"
                add(
                    "numeric_recheck",
                    "info" if result.agrees else "error",
                    f"second check ({result.method}) {tag}: {result.detail}",
                )
    short = len(normalise_option(item.correct)) <= 2
    for level, hint in enumerate(item.hints, start=1):
        if _leaks(hint, item.correct, numeric):
            add(
                "hint_leak",
                "warning" if short else "error",
                f"hint {level} contains the keyed answer",
            )
    forbidden = normalise_option(item.correct)
    for level, hint in enumerate(item.hints[:2], start=1):
        try:
            from app.content.leak import hint_leaks_answer

            leaked = hint_leaks_answer(hint, item.correct)
        except Exception:  # noqa: BLE001  (the shared checker parses maths; text may not parse)
            leaked = False
        if leaked and forbidden and not (_leaks(hint, item.correct, numeric) and not short):
            add("hint_leak", "error", f"hint {level} is equivalent to the keyed answer")
    steps = len([s for s in re.split(r"(?<=[.!?])\s+", item.explanation.strip()) if s])
    if not 2 <= steps <= 4:
        add("explanation_length", "warning", f"explanation has {steps} sentences (2-4 expected)")
    if topic is not None:
        if draft.class_ == 10 and topic.kind == "computed":
            add(
                "computed_topic",
                "error",
                "class 10 computed topics are made by the machine-checked lanes, not drafted",
            )
    if item.confidence == "low":
        add("low_confidence", "info", "the drafter marked this keyed answer as low confidence")
    try:  # the compiled item must satisfy the real Item schema
        from app.content.schema import Item

        data, _ = compile_item(draft, item, position + 1)
        Item.model_validate(data)
    except (ValidationError, ValueError) as exc:
        add(
            "item_schema",
            "error",
            f"compiled item fails the Item schema: {str(exc).splitlines()[0]}",
        )
    return out


def norm_mistake(text: str) -> str:
    return _SPACE.sub(" ", text.strip().lower())


def _file_findings(
    file: str, draft: DraftFile, smap: SyllabusMap | None, rel_expect: tuple[int, str, str] | None
) -> tuple[list[Finding], dict[str, MapTopic]]:
    out: list[Finding] = []
    topics: dict[str, MapTopic] = {}

    def add(code: str, message: str, topic: str = "") -> None:
        out.append(Finding(file, None, topic, code, "error", message))

    if rel_expect is not None and rel_expect != (draft.class_, draft.subject, draft.chapter):
        add(
            "path_mismatch",
            f"file path says {rel_expect} but the file says "
            f"{(draft.class_, draft.subject, draft.chapter)}",
        )
    if smap is None:
        add("no_syllabus_map", f"no syllabus map for class {draft.class_} {draft.subject}")
        return out, topics
    chapter = next((c for c in smap.chapters if c.key == draft.chapter), None)
    if chapter is None:
        add(
            "unknown_chapter",
            f"chapter {draft.chapter!r} is not in the class {draft.class_} {draft.subject} map",
        )
        return out, topics
    by_key = {t.key: t for t in chapter.topics}
    for key in dict.fromkeys(i.topic for i in draft.items):
        if key in by_key:
            topics[key] = by_key[key]
        else:
            add("unknown_topic", f"topic {key!r} is not in chapter {draft.chapter!r}", key)
    return out, topics


def _topic_findings(file: str, draft: DraftFile, topics: dict[str, MapTopic]) -> list[Finding]:
    out: list[Finding] = []
    for key, topic in topics.items():
        mine = [i for i in draft.items if i.topic == key]
        if len(mine) != ITEMS_PER_TOPIC:
            out.append(
                Finding(
                    file,
                    None,
                    key,
                    "topic_count",
                    "warning",
                    f"{len(mine)} items (target {ITEMS_PER_TOPIC})",
                )
            )
        spread: Counter[str] = Counter(i.difficulty for i in mine)
        if len(mine) == ITEMS_PER_TOPIC and any(spread[d] != 2 for d in ("easy", "medium", "hard")):
            out.append(
                Finding(
                    file,
                    None,
                    key,
                    "difficulty_spread",
                    "warning",
                    f"difficulty spread {dict(spread)} (2/2/2 expected)",
                )
            )
        wanted = topic.diagram or topic.kind == "diagram"
        pictured = sum(1 for i in mine if i.diagram)
        if wanted and pictured == 0:
            out.append(
                Finding(
                    file,
                    None,
                    key,
                    "diagram_missing",
                    "error",
                    "diagram topic has no item with a diagram description",
                )
            )
        elif wanted and pictured < 2:
            out.append(
                Finding(
                    file,
                    None,
                    key,
                    "diagram_few",
                    "warning",
                    f"only {pictured} item(s) carry a diagram description (2 expected)",
                )
            )
    return out


def near_duplicates(entries: list[tuple[str, int, str, str]]) -> list[tuple[int, int, float]]:
    """entries: (file, position, scope, stem). Returns index pairs (i, j), i before j, whose stems
    share a normalised token Jaccard of NEAR_DUPLICATE or more, within the same scope."""
    sets = [tokens(e[3]) for e in entries]
    signatures = [math_signature(e[3]) for e in entries]
    by_scope: dict[str, list[int]] = {}
    for index, entry in enumerate(entries):
        by_scope.setdefault(entry[2], []).append(index)
    pairs: list[tuple[int, int, float]] = []
    for members in by_scope.values():
        ordered = sorted(members, key=lambda i: len(sets[i]))
        for a_pos, a in enumerate(ordered):
            for b in ordered[a_pos + 1 :]:
                if len(sets[a]) < NEAR_DUPLICATE * len(sets[b]):
                    break  # sizes are sorted: no later stem can reach the threshold
                score = jaccard(sets[a], sets[b])
                # a maths stem that differs only in its numbers or symbols is a different question
                if score >= NEAR_DUPLICATE and signatures[a] == signatures[b]:
                    first, second = (a, b) if a < b else (b, a)
                    pairs.append((first, second, score))
    return sorted(pairs)


@dataclass
class LintRun:
    files: list[FileResult]

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.files for f in r.findings]

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    def to_json(self) -> dict[str, Any]:
        counts = Counter(f.severity for f in self.findings)
        return {
            "files": len(self.files),
            "errors": counts["error"],
            "warnings": counts["warning"],
            "info": counts["info"],
            "results": [
                {
                    "file": r.path,
                    "items": len(r.draft.items) if r.draft else 0,
                    "blocked": r.file_blocked,
                    "findings": [asdict(f) for f in r.findings],
                }
                for r in self.files
            ],
        }

    def to_text(self) -> str:
        lines: list[str] = []
        for r in self.files:
            if not r.findings:
                lines.append(f"OK    {r.path}")
                continue
            worst = "ERROR" if r.errors else "WARN "
            lines.append(f"{worst} {r.path}")
            for f in r.findings:
                where = f"item {f.item + 1}" if f.item is not None else "file"
                topic = f" [{f.topic}]" if f.topic else ""
                lines.append(f"    {f.severity:7} {f.code:20} {where}{topic}: {f.message}")
        counts = Counter(f.severity for f in self.findings)
        lines.append(
            f"{len(self.files)} files, {counts['error']} errors, {counts['warning']} warnings, "
            f"{counts['info']} info"
        )
        return "\n".join(lines)


def _expected_from_path(root: Path, path: Path) -> tuple[int, str, str] | None:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return None
    if len(rel.parts) != 3 or not rel.parts[0].isdigit() or rel.parts[1] not in SUBJECTS:
        return None
    return int(rel.parts[0]), rel.parts[1], rel.stem


def _shown(content_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(content_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def lint_paths(
    content_root: Path,
    paths: list[Path] | None = None,
    *,
    rechecks: list[NumericRecheck] | None = None,
) -> LintRun:
    """Lint the given draft files (default: every file under the drafts folder)."""
    root = drafts_root(content_root)
    chosen = paths if paths is not None else draft_files(root)
    checks = NUMERIC_RECHECKS if rechecks is None else rechecks
    maps: dict[tuple[int, str], SyllabusMap | None] = {}
    results: list[FileResult] = []
    entries: list[tuple[str, int, str, str]] = []
    owners: list[tuple[FileResult, int]] = []
    for path in sorted(chosen, key=lambda p: p.as_posix()):
        shown = _shown(content_root, path)
        result = FileResult(path=shown)
        results.append(result)
        draft, errors = read_draft(path)
        if draft is None:
            result.findings.extend(Finding(shown, None, "", "schema", "error", e) for e in errors)
            continue
        result.draft = draft
        key = (draft.class_, draft.subject)
        if key not in maps:
            try:
                maps[key] = load_map(content_root, *key)
            except ValueError:
                maps[key] = None
        found, topics = _file_findings(shown, draft, maps[key], _expected_from_path(root, path))
        result.findings.extend(found)
        result.topics = topics
        if found:
            continue
        result.findings.extend(_topic_findings(shown, draft, topics))
        for position, item in enumerate(draft.items):
            result.findings.extend(
                lint_item(shown, position, item, topics.get(item.topic), draft, checks)
            )
            entries.append((shown, position, f"{draft.class_}.{draft.subject}", item.stem))
            owners.append((result, position))
    for first, second, score in near_duplicates(entries):
        result, position = owners[second]
        other = entries[first]
        result.findings.append(
            Finding(
                result.path,
                position,
                result.draft.items[position].topic if result.draft else "",
                "near_duplicate",
                "error",
                f"stem is {score:.2f} similar to item {other[1] + 1} of {other[0]}",
            )
        )
    return LintRun(results)
