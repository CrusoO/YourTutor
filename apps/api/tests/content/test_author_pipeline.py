"""G8 step 5: a chapter goes from passages to live using only the tooling and teacher approvals."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest
import yaml

from app.author import AuthorError, chapter_status, draft_missing, go_live, queue
from app.author import main as author_main
from app.content.review import export_sheet, import_sheet_report
from app.content.validator import validate_path
from app.llm.provider import FakeProvider
from app.registries.paths import content_root as shipped_root
from tests.content.conftest import loc, minimal_item, minimal_skill, write_yaml

CHAPTER = "bhutan_class9"  # a chapter of the curriculum registry
SKILL = "MATH.S1"
REVIEWER = "teacher.demo"


def _draft(stem: str, answer: str, steps: list[str], hints: list[str], **over: object) -> dict:
    base: dict = {
        "difficulty": 0.4,
        "type": "expression",
        "stem": stem,
        "answer": answer,
        "accept": [answer, f"x={answer}"],
        "solution_steps": steps,
        "hints": hints,
        "prediction_prompt": "Will x be bigger or smaller than the number on the right?",
    }
    base.update(over)
    return base


def _reply(*items: dict) -> str:
    return yaml.safe_dump(list(items), allow_unicode=True, sort_keys=False)


PRACTICE = [
    _draft(
        "Solve for x: x + 3 = 11", "8", ["Take 3 off both sides.", "x = 8"],
        ["x has a number added to it. What undoes adding?", "Take the added number off both sides.",
         "Subtract 3 from 11."],
    ),
    _draft(
        "Find x if x - 4 = 9", "13", ["Add 4 to both sides.", "x = 13"],
        ["Here a number is taken away from x. What undoes taking away?",
         "Put the taken-away number back on both sides.", "Add 4 to 9."],
    ),
    _draft(
        "Solve: 2x = 14", "7", ["Divide both sides by 2.", "x = 7"],
        ["x is multiplied by a number. Which operation undoes multiplying?",
         "Divide both sides by the multiplier.", "Divide 14 by 2."],
    ),
    _draft(
        "x / 5 = 3. Solve for x.", "15", ["Multiply both sides by 5.", "x = 15"],
        ["x is divided by a number. Which operation undoes dividing?",
         "Multiply both sides by the divisor.", "Multiply 3 by 5."],
    ),
    _draft(
        "Solve for x: 3x + 1 = 10", "3", ["Take 1 off both sides.", "Divide by 3.", "x = 3"],
        ["Two things were done to x. Which one do you undo first?",
         "Undo the adding before the multiplying.", "Subtract 1, then divide by 3."],
    ),
]  # fmt: skip
DIAGNOSTIC = [
    _draft(
        "Solve for x: x + 6 = 15", "9", ["Take 6 off both sides.", "x = 9"],
        ["Look at what is added to x. How do you undo it?",
         "Take 6 off both sides of the equation.", "Subtract 6 from 15."],
    ),
    _draft(
        "Find x if 4x = 28", "7", ["Divide both sides by 4.", "x = 7"],
        ["Look at what x is multiplied by. How do you undo it?",
         "Divide both sides of the equation by 4.", "Divide 28 by 4."],
    ),
    _draft(
        "Find x if x + 10 = 31", "21", ["Take 10 off both sides.", "x = 21"],
        ["Find the number added to x. Which step removes it?",
         "Take 10 off both sides of the equation.", "Subtract 10 from 31."],
    ),
]  # fmt: skip
EXPLAIN = _draft(
    "Dawa solves x + 8 = 20 and writes x = 28. What is the correct value of x?", "12",
    ["Dawa added 8 instead of taking it away.", "Take 8 off both sides.", "x = 12"],
    ["Check Dawa's step: was the added number undone or repeated?",
     "Undoing adding means taking the number away.", "Subtract 8 from 20."],
)  # fmt: skip
APPLY = _draft(
    "Pema had some stickers. After she got 7 more she had 19. How many did she start with?",
    "12",
    ["Let x be the stickers she started with: x + 7 = 19.", "Take 7 off both sides.", "x = 12"],
    ["Let x be the stickers Pema had at first. What happened to x?",
     "Write the story as a number sentence, then undo the adding.", "Subtract 7 from 19."],
)  # fmt: skip
TRANSFER = _draft(
    "Solve for x: 17 = x + 9", "8", ["Read it the other way round: x + 9 = 17.", "x = 8"],
    ["It does not matter which side x is on. What is added to x?",
     "Undo the adding on both sides, then read x.", "Subtract 9 from 17."],
)  # fmt: skip


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A small chapter: one skill, one passage, one lesson, matched checkpoint forms."""
    write_yaml(tmp_path / "skills" / "s1.yaml", minimal_skill(SKILL))
    write_yaml(
        tmp_path / "overlays" / "ov.yaml",
        {
            "id": CHAPTER,
            "curriculum_id": "bhutan",
            "grade": 9,
            "chapter": "linear_equations",
            "skill_ids": [SKILL],
            "live": False,
        },
    )
    write_yaml(
        tmp_path / "misconceptions" / "m1.yaml",
        {
            "id": "MC.1",
            "title": loc("Wrong inverse"),
            "explanation": loc("Undo by doing the opposite."),
            "remedial_skill": SKILL,
            "status": "draft",
        },
    )
    write_yaml(
        tmp_path / "glossary" / "en-ne.yaml",
        {"language": "ne", "terms": {"equation": "<Nepali — to be filled by reviewer>"}},
    )
    write_yaml(
        tmp_path / "sources" / "notes.yaml",
        {"sources": [{"id": "NOTE.MINI", "licence": "authored", "title": "Mini note"}]},
    )
    write_yaml(
        tmp_path / "passages" / "mini.yaml",
        {
            "passages": [
                {
                    "id": "PSG.MINI.1",
                    "chapter_id": CHAPTER,
                    "section_key": "s1",
                    "skill_ids": [SKILL],
                    "source_type": "authored_notes",
                    "licence_status": "owned",
                    "source_ref": "NOTE.MINI",
                    "text": "To solve x + 3 = 11, take 3 off both sides to get x = 8.",
                }
            ]
        },
    )
    lesson = (shipped_root() / "lessons" / "brackets.yaml").read_text(encoding="utf-8")
    lesson = lesson.replace("MATH.ALG.LIN1.BRACKETS", SKILL).replace(
        "NOTE.LIN1.BRACKETS", "NOTE.MINI"
    )
    (tmp_path / "lessons").mkdir()
    (tmp_path / "lessons" / "mini.yaml").write_text(lesson, encoding="utf-8")
    ids_a: list[str] = []
    ids_b: list[str] = []
    for index in range(10):
        for form, bucket in (("A", ids_a), ("B", ids_b)):
            item_id = f"ITEM.CP.{form}.{index:02d}"
            write_yaml(
                tmp_path / "items" / "checkpoint" / f"{item_id}.yaml",
                minimal_item(
                    item_id,
                    skill=SKILL,
                    pool="checkpoint",
                    stem=f"[{item_id}] Solve for x: x + {index + 2} = {index + 21}",
                    answer="19",
                ),
            )
            bucket.append(item_id)
    write_yaml(
        tmp_path / "checkpoints" / "forms.yaml",
        {
            "id": "CP.MINI.FORMS",
            "checkpoint_id": "CP.MINI",
            "A": ids_a,
            "B": ids_b,
            "match_map": dict(zip(ids_a, ids_b, strict=True)),
        },
    )
    return tmp_path


def _provider() -> FakeProvider:
    # the order of draft_missing's calls: practice, diagnostic, then explain, apply, transfer
    return FakeProvider(
        [
            _reply(*PRACTICE),
            _reply(*DIAGNOSTIC),
            _reply(EXPLAIN),
            _reply(APPLY),
            _reply(TRANSFER),
        ]
    )


def _approve_everything(root: Path, tmp_path: Path):
    sheet = tmp_path / "sheet.csv"
    export_sheet(root, sheet, tmp_path / "sheet.html")
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    for row in rows:
        row["approve"] = "Y"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return import_sheet_report(sheet, root, REVIEWER)


def test_the_starting_chapter_is_valid_but_blocked_on_everything_a_teacher_must_supply(
    root: Path,
) -> None:
    assert validate_path(root).errors == []
    assert queue(root) == {"items": 20, "templates": 0, "lessons": 1, "passages": 1}
    status = chapter_status(root, CHAPTER)
    assert not status.ready and not status.live
    text = " | ".join(status.blockers)
    for needle in ("practice 0/5", "diagnostic 0/2", "role explain", "no approved lesson"):
        assert needle in text, text
    assert "no approved passage" in text


def test_a_chapter_goes_from_passages_to_live_with_only_the_tooling_and_a_teacher(
    root: Path, tmp_path: Path
) -> None:
    # 1. draft only what is missing, from the passages (drafts, never approved)
    written = draft_missing(root, CHAPTER, _provider())
    assert sum(written.values()) == len(PRACTICE) + len(DIAGNOSTIC) + 3
    drafts = sorted((root / "items" / "drafts" / CHAPTER).glob("*.yaml"))
    assert len(drafts) == 11
    assert all(yaml.safe_load(p.read_text("utf-8"))["status"] == "draft" for p in drafts)
    assert validate_path(root).errors == []

    # 2. still blocked: nothing is approved, and going live is refused
    assert not chapter_status(root, CHAPTER).ready
    with pytest.raises(AuthorError, match="not ready"):
        go_live(root, CHAPTER, REVIEWER)
    with pytest.raises(PermissionError):
        go_live(root, CHAPTER, "stranger")
    assert yaml.safe_load((root / "overlays" / "ov.yaml").read_text("utf-8"))["live"] is False

    # 3. the teacher approves through the review sheet
    result = _approve_everything(root, tmp_path)
    assert not result.stale and not result.refused, result
    assert {"LESSON.LIN1.BRACKETS", "PSG.MINI.1"} <= set(result.approved)

    # 4. nothing blocks any more; going live flips the overlay and the content still validates
    status = chapter_status(root, CHAPTER)
    assert status.ready, status.format()
    done = go_live(root, CHAPTER, REVIEWER)
    assert done.live
    assert yaml.safe_load((root / "overlays" / "ov.yaml").read_text("utf-8"))["live"] is True
    assert validate_path(root).errors == []


def test_drafting_a_second_time_adds_nothing_because_existing_items_count(root: Path) -> None:
    draft_missing(root, CHAPTER, _provider())
    again = draft_missing(root, CHAPTER, FakeProvider([]))
    assert sum(again.values()) == 0
    assert len(list((root / "items" / "drafts" / CHAPTER).glob("*.yaml"))) == 11


def test_editing_an_approved_item_after_approval_blocks_the_chapter_again(
    root: Path, tmp_path: Path
) -> None:
    draft_missing(root, CHAPTER, _provider())
    _approve_everything(root, tmp_path)
    assert chapter_status(root, CHAPTER).ready
    victim = sorted((root / "items" / "drafts" / CHAPTER).glob("*.yaml"))[0]
    data = yaml.safe_load(victim.read_text("utf-8"))
    data["stem"]["en"] += " (edited)"
    victim.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    status = chapter_status(root, CHAPTER)
    assert not status.ready  # the edit reset that item to draft by hash
    assert yaml.safe_load(victim.read_text("utf-8"))["status"] == "draft"


def test_going_live_that_would_break_validation_is_rolled_back(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft_missing(root, CHAPTER, _provider())
    _approve_everything(root, tmp_path)
    real = validate_path
    calls = {"n": 0}

    def flaky(path: Path):
        report = real(path)
        calls["n"] += 1
        if calls["n"] >= 2:  # the check after flipping the flag
            report.errors.append("simulated failure")
        return report

    monkeypatch.setattr("app.author.validate_path", flaky)
    with pytest.raises(AuthorError, match="broke validation"):
        go_live(root, CHAPTER, REVIEWER)
    assert yaml.safe_load((root / "overlays" / "ov.yaml").read_text("utf-8"))["live"] is False


def test_the_command_line_reports_status_and_refuses_the_draft_command_in_production(
    root: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert author_main(["queue", str(root)]) == 0
    assert "passages: 1 in draft" in capsys.readouterr().out
    assert author_main(["status", str(root), "--chapter", CHAPTER]) == 1
    assert "NOT ready" in capsys.readouterr().out
    monkeypatch.setattr("app.config.settings.app_env", "production")
    assert author_main(["draft", str(root), "--chapter", CHAPTER], FakeProvider([])) == 2
    shutil.rmtree(root / "items" / "drafts", ignore_errors=True)
    assert not (root / "items" / "drafts").exists()
