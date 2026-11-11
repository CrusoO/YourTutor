"""Exam blueprint: facts about past papers, never their text.

A blueprint row says "in year Y, paper P, section S, question N was worth M marks, of this type,
on this chapter and skill, at this competency". That is all. The operator fills a CSV by hand;
`import_csv` checks it against the curriculum map and the skill ids and appends it to
`<content>/blueprint/<paper>.yaml`. There is no PDF parser and no model extraction here, and a CSV
with a column that could hold question text (`stem`, `question`, ...) or a long free-text value is
refused whole.

Every import appends one line to `<content>/blueprint/audit.jsonl`: date, rows added, the source
file's name and SHA-256, and `source_deleted` (set by the operator once the source file is gone).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

BLUEPRINT_DIR = "blueprint"
AUDIT_FILE = "audit.jsonl"
DRIFT_THRESHOLD_PP = 5.0  # percentage points
DRIFT_LOOKBACK_YEARS = 3
MAX_SECTION_CHARS = 24
MAX_NOTE_CHARS = 60
MAX_NOTE_WORDS = 6


class QuestionType(StrEnum):
    mcq = "mcq"
    assertion_reason = "assertion_reason"
    case_based = "case_based"
    fill_blank = "fill_blank"
    very_short = "very_short"
    short = "short"
    long = "long"
    other = "other"


class Competency(StrEnum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyse = "analyse"


CSV_COLUMNS = (
    "year",
    "paper",
    "section",
    "question_number",
    "marks",
    "question_type",
    "chapter",
    "skill_id",
    "competency",
    "internal_choice",
)
OPTIONAL_COLUMNS = ("note",)
FORBIDDEN_COLUMNS = frozenset(
    {"stem", "question", "question_text", "text", "body", "prompt", "content", "answer", "options"}
)

_PAPER = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_QNUM = re.compile(r"^\d{1,3}[a-z]?$")
_TRUE = {"true", "yes", "1", "y"}
_FALSE = {"false", "no", "0", "n", ""}


def looks_like_question_text(value: str, *, max_chars: int, max_words: int) -> str | None:
    """A reason the value is too long or too sentence-like to be a label, or None."""
    if len(value) > max_chars:
        return f"longer than {max_chars} characters"
    if len(value.split()) > max_words:
        return f"more than {max_words} words"
    if "?" in value:
        return "contains a question mark"
    if re.search(r"\d\s*[-+*/=^]\s*\d|[a-z]\s*=\s*[\dxyz]", value.lower()):
        return "contains an equation"
    return None


class BlueprintRow(BaseModel):
    model_config = {"extra": "forbid"}

    year: int = Field(ge=2000, le=2100)
    paper: str
    section: str = Field(min_length=1)
    question_number: str
    marks: int = Field(ge=1, le=10)
    question_type: QuestionType
    chapter: str
    skill_id: str
    competency: Competency
    internal_choice: bool = False
    note: str | None = None

    @field_validator("paper")
    @classmethod
    def _paper_slug(cls, value: str) -> str:
        if not _PAPER.match(value):
            raise ValueError("paper must be a lowercase slug such as cbse-10-maths-standard")
        return value

    @field_validator("question_number")
    @classmethod
    def _qnum(cls, value: str) -> str:
        if not _QNUM.match(value):
            raise ValueError("question_number must be like 21 or 21a")
        return value

    @field_validator("section")
    @classmethod
    def _section(cls, value: str) -> str:
        reason = looks_like_question_text(value, max_chars=MAX_SECTION_CHARS, max_words=3)
        if reason:
            raise ValueError(f"section looks like text ({reason})")
        return value

    @field_validator("note")
    @classmethod
    def _note(cls, value: str | None) -> str | None:
        if value:
            reason = looks_like_question_text(
                value, max_chars=MAX_NOTE_CHARS, max_words=MAX_NOTE_WORDS
            )
            if reason:
                raise ValueError(f"note looks like question text ({reason})")
        return value or None

    @property
    def key(self) -> tuple[int, str, str, str]:
        return (self.year, self.paper, self.section, self.question_number)


@dataclass
class ImportResult:
    added: int = 0
    errors: list[str] = field(default_factory=list)
    audit: dict | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def blueprint_dir(root: Path) -> Path:
    return root / BLUEPRINT_DIR


def paper_file(root: Path, paper: str) -> Path:
    return blueprint_dir(root) / f"{paper}.yaml"


def load_blueprint(root: Path) -> list[BlueprintRow]:
    rows: list[BlueprintRow] = []
    folder = blueprint_dir(root)
    for path in sorted(folder.glob("*.yaml")) if folder.is_dir() else []:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for raw in data.get("rows") or []:
            rows.append(BlueprintRow.model_validate(raw))
    return rows


def known_chapter_ids(root: Path) -> set[str]:
    from app.registries.loaders import load_all_curricula

    folder = root / "curricula"
    specs = load_all_curricula(folder) if folder.is_dir() else load_all_curricula()
    return {ch.id for spec in specs.values() for book in spec.books for ch in book.chapters}


def known_skill_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    for path in sorted((root / "skills").rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            ids.add(str(data["id"]))
    return ids


def parse_csv(
    path: Path, *, chapters: set[str], skills: set[str]
) -> tuple[list[BlueprintRow], list[str]]:
    """Rows of a hand-filled CSV, or every problem found. Nothing is accepted if anything fails."""
    errors: list[str] = []
    rows: list[BlueprintRow] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = [(h or "").strip() for h in (reader.fieldnames or [])]
        banned = [h for h in header if h.lower() in FORBIDDEN_COLUMNS]
        unknown = [h for h in header if h not in CSV_COLUMNS and h not in OPTIONAL_COLUMNS]
        if banned:
            errors.append(f"column(s) {', '.join(banned)} may not be imported: facts only")
        if unknown and not banned:
            errors.append(f"unknown column(s): {', '.join(unknown)}")
        missing = [c for c in CSV_COLUMNS if c not in header]
        if missing:
            errors.append(f"missing column(s): {', '.join(missing)}")
        if errors:
            return [], errors
        for number, raw in enumerate(reader, start=2):
            data = {(k or "").strip(): (v or "").strip() for k, v in raw.items() if k}
            flag = data.get("internal_choice", "").lower()
            if flag not in _TRUE | _FALSE:
                errors.append(f"row {number}: internal_choice must be true or false")
                continue
            data["internal_choice"] = "true" if flag in _TRUE else "false"
            if not data.get("note"):
                data.pop("note", None)
            try:
                row = BlueprintRow.model_validate(data)
            except ValidationError as exc:
                for err in exc.errors():
                    where = ".".join(str(p) for p in err["loc"])
                    errors.append(f"row {number}: {where}: {err['msg']}")
                continue
            if row.chapter not in chapters:
                errors.append(f"row {number}: chapter {row.chapter!r} is not in the curriculum map")
            if row.skill_id not in skills:
                errors.append(f"row {number}: skill_id {row.skill_id!r} is not a known skill")
            rows.append(row)
    if not rows and not errors:
        errors.append("the file has no rows")
    return rows, errors


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _dump_paper(root: Path, paper: str, rows: list[BlueprintRow]) -> None:
    path = paper_file(root, paper)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r.year, r.section, r.question_number))
    data = {
        "paper": paper,
        "rows": [r.model_dump(mode="json", exclude_none=True) for r in ordered],
    }
    header = "# Exam blueprint: facts only (no question text). Written by `blueprint-import`.\n"
    path.write_text(
        header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def import_csv(
    csv_path: Path, root: Path, *, source_deleted: bool = False, today: date | None = None
) -> ImportResult:
    """Validate a CSV and append it to the blueprint YAML plus one audit line."""
    result = ImportResult()
    rows, errors = parse_csv(
        csv_path, chapters=known_chapter_ids(root), skills=known_skill_ids(root)
    )
    existing = {r.key for r in load_blueprint(root)}
    seen: set[tuple[int, str, str, str]] = set()
    for row in rows:
        if row.key in existing or row.key in seen:
            errors.append(f"duplicate blueprint row {row.key}")
        seen.add(row.key)
    if errors:
        result.errors = errors
        return result
    by_paper: dict[str, list[BlueprintRow]] = defaultdict(list)
    for row in rows:
        by_paper[row.paper].append(row)
    for paper, new_rows in by_paper.items():
        old = [r for r in load_blueprint(root) if r.paper == paper]
        _dump_paper(root, paper, [*old, *new_rows])
    audit = {
        "date": (today or date.today()).isoformat(),
        "rows_added": len(rows),
        "source_file": csv_path.name,
        "sha256": file_sha256(csv_path),
        "source_deleted": source_deleted,
    }
    log = blueprint_dir(root) / AUDIT_FILE
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(audit, sort_keys=True) + "\n")
    result.added = len(rows)
    result.audit = audit
    return result


# --- report ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Drift:
    paper: str
    year: int
    question_type: str
    share: float  # percent of the paper's marks that year
    baseline: float  # mean percent over the previous years used
    baseline_years: tuple[int, ...]

    @property
    def delta(self) -> float:
        return self.share - self.baseline


def _marks_by_type(rows: list[BlueprintRow]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[row.question_type.value] += row.marks
    return counter


def type_drift(rows: list[BlueprintRow], threshold: float = DRIFT_THRESHOLD_PP) -> list[Drift]:
    """Types whose share of a paper's marks moved by more than `threshold` percentage points
    against the mean of the previous three years that have data (needs at least one)."""
    out: list[Drift] = []
    for paper in sorted({r.paper for r in rows}):
        paper_rows = [r for r in rows if r.paper == paper]
        years = sorted({r.year for r in paper_rows})
        shares: dict[int, dict[str, float]] = {}
        for year in years:
            counts = _marks_by_type([r for r in paper_rows if r.year == year])
            total = sum(counts.values()) or 1
            shares[year] = {t: 100.0 * m / total for t, m in counts.items()}
        for index, year in enumerate(years):
            previous = years[max(0, index - DRIFT_LOOKBACK_YEARS) : index]
            if not previous:
                continue
            types = set(shares[year]).union(*(shares[p] for p in previous))
            for question_type in sorted(types):
                baseline = sum(shares[p].get(question_type, 0.0) for p in previous) / len(previous)
                share = shares[year].get(question_type, 0.0)
                if abs(share - baseline) > threshold:
                    out.append(Drift(paper, year, question_type, share, baseline, tuple(previous)))
    return out


def format_report(rows: list[BlueprintRow]) -> str:
    if not rows:
        return "No blueprint rows."
    lines: list[str] = []
    for paper in sorted({r.paper for r in rows}):
        paper_rows = [r for r in rows if r.paper == paper]
        lines.append(f"Paper {paper}")
        for year in sorted({r.year for r in paper_rows}):
            year_rows = [r for r in paper_rows if r.year == year]
            lines.append(f"  {year}: {sum(r.marks for r in year_rows)} marks")
            for chapter in sorted({r.chapter for r in year_rows}):
                counts = _marks_by_type([r for r in year_rows if r.chapter == chapter])
                detail = ", ".join(f"{t} {m}" for t, m in sorted(counts.items()))
                lines.append(f"    {chapter}: {sum(counts.values())} marks ({detail})")
    drifts = type_drift(rows)
    lines.append("")
    if drifts:
        lines.append(f"Type share moved by more than {DRIFT_THRESHOLD_PP:g} points:")
        for d in drifts:
            span = f"{d.baseline_years[0]}-{d.baseline_years[-1]}"
            lines.append(
                f"  FLAG {d.paper} {d.year} {d.question_type}: {d.share:.1f}% of marks vs "
                f"{d.baseline:.1f}% in {span} ({d.delta:+.1f} points)"
            )
    else:
        lines.append(f"No type share moved by more than {DRIFT_THRESHOLD_PP:g} points.")
    return "\n".join(lines)


def pattern_for_skill(rows: list[BlueprintRow], skill_id: str) -> tuple[int, str, list[int]] | None:
    """The most common (marks, type) among blueprint rows for a skill, with its years; None when
    the skill has no rows. This is the only thing that lets the pattern tag appear."""
    mine = [r for r in rows if r.skill_id == skill_id]
    if not mine:
        return None
    common = Counter((r.marks, r.question_type.value) for r in mine).most_common()
    top = max(count for _, count in common)
    marks, question_type = sorted(key for key, count in common if count == top)[0]
    years = sorted({r.year for r in mine if r.marks == marks and r.question_type == question_type})
    return marks, question_type, years


@lru_cache(maxsize=4)
def _cached_blueprint(root: str) -> tuple[BlueprintRow, ...]:
    return tuple(load_blueprint(Path(root)))


def pattern_tag_for_skill(skill_id: str, root: Path | None = None) -> str | None:
    """The pattern tag text for a skill, or None when the blueprint has no rows for it."""
    from app.content.labels import pattern_tag
    from app.registries.paths import content_root

    found = pattern_for_skill(list(_cached_blueprint(str(root or content_root()))), skill_id)
    return pattern_tag(found[0], found[1], found[2]) if found else None
