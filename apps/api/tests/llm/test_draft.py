"""G4 step 5: `draft_content` is an authoring tool. It writes `status: draft` only, never
translates, validates each item, and refuses to run in production."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from app.config import settings
from app.content.schema import ContentStatus, Item
from app.llm.__main__ import main
from app.llm.draft import DraftRefused, draft_items
from app.llm.provider import FakeProvider

SKILL = "MATH.ALG.LIN1.SOLVE_ONE_STEP"


def _item(n: int = 1, **over: object) -> dict:
    base: dict = {
        "difficulty": 0.3,
        "type": "expression",
        "role": "procedure",
        "stem": f"Solve for x: x + {n} = {n + 10}",
        "answer": "10",
        "accept": ["10", "x=10"],
        "solution_steps": [f"Take {n} off both sides.", "x = 10"],
        "hints": [
            "What undoes adding a number?",
            "Do the opposite to both sides.",
            "Take the number off both sides.",
        ],
        "prediction_prompt": "Will x be bigger than the number added?",
    }
    base.update(over)
    return base


def _reply(*items: dict) -> str:
    return yaml.safe_dump(list(items), allow_unicode=True, sort_keys=False)


@pytest.fixture(autouse=True)
def _dev() -> Generator[None, None, None]:
    keep = (settings.app_env, settings.llm_api_key, settings.llm_model_strong)
    settings.app_env, settings.llm_api_key, settings.llm_model_strong = "development", "k", "m"
    yield
    settings.app_env, settings.llm_api_key, settings.llm_model_strong = keep


def test_valid_items_are_written_as_drafts_with_placeholders_not_translations(
    tmp_path: Path,
) -> None:
    provider = FakeProvider([_reply(_item(1), _item(2))])
    report = draft_items(
        skill_id=SKILL, passages="x + a = b is solved by taking a off both sides.", count=2,
        provider=provider, out_dir=tmp_path,
    )  # fmt: skip
    assert len(report.written) == 2 and report.rejected == []
    for path in report.written:
        item = Item.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        assert item.status is ContentStatus.draft and item.reviewed_by is None
        assert item.skill_ids == [SKILL] and item.pool.value == "practice"
        assert item.stem.en.startswith("Solve for x")
        assert "to be filled by reviewer" in (item.stem.ne or "")
        assert "to be filled by reviewer" in (item.stem.as_ or "")
        assert all("to be filled by reviewer" in (h.ne or "") for h in item.hints)
    assert len({p.name for p in report.written}) == 2
    assert "x + a = b is solved" in provider.calls[0].user  # the authored passage is in the prompt


def test_a_model_that_claims_approved_status_still_gets_draft(tmp_path: Path) -> None:
    claimed = _item(1, status="approved", reviewed_by="teacher.x", content_hash="abc")
    report = draft_items(
        skill_id=SKILL, passages="p", count=1, provider=FakeProvider([_reply(claimed)]),
        out_dir=tmp_path,
    )  # fmt: skip
    data = yaml.safe_load(report.written[0].read_text(encoding="utf-8"))
    assert data["status"] == "draft" and data["reviewed_by"] is None
    assert not data.get("content_hash")


def test_bad_items_are_rejected_with_a_reason_and_good_ones_still_written(tmp_path: Path) -> None:
    missing_hints = _item(2)
    missing_hints["hints"] = missing_hints["hints"][:2]
    wrong_answer = _item(3, answer="11", accept=["11"])  # x + 3 = 13 is 10, not 11
    leaking = _item(4, hints=["The answer is 10.", "Try 10.", "x = 10"])
    report = draft_items(
        skill_id=SKILL, passages="p", count=4,
        provider=FakeProvider([_reply(_item(1), missing_hints, wrong_answer, leaking)]),
        out_dir=tmp_path,
    )  # fmt: skip
    assert len(report.written) == 1
    reasons = dict(report.rejected)
    assert "hint levels" in reasons[1] or "hints" in reasons[1]
    assert "answer" in reasons[2]
    assert "leak" in reasons[3]


def test_unparseable_output_writes_nothing(tmp_path: Path) -> None:
    report = draft_items(
        skill_id=SKILL, passages="p", count=1, provider=FakeProvider(["not: [valid"]),
        out_dir=tmp_path,
    )  # fmt: skip
    assert report.written == [] and report.rejected and list(tmp_path.iterdir()) == []


def test_it_never_overwrites_an_existing_draft(tmp_path: Path) -> None:
    first = draft_items(
        skill_id=SKILL, passages="p", count=1, provider=FakeProvider([_reply(_item(1))]),
        out_dir=tmp_path,
    )  # fmt: skip
    before = first.written[0].read_text(encoding="utf-8")
    second = draft_items(
        skill_id=SKILL, passages="p", count=1, provider=FakeProvider([_reply(_item(2))]),
        out_dir=tmp_path,
    )  # fmt: skip
    assert second.written[0] != first.written[0]
    assert first.written[0].read_text(encoding="utf-8") == before


def test_it_refuses_to_run_in_production(tmp_path: Path) -> None:
    settings.app_env = "production"
    provider = FakeProvider([_reply(_item(1))])
    with pytest.raises(DraftRefused, match="production"):
        draft_items(skill_id=SKILL, passages="p", count=1, provider=provider, out_dir=tmp_path)
    assert provider.calls == [] and list(tmp_path.iterdir()) == []


def test_the_cli_refuses_in_production_and_without_a_key(tmp_path: Path, capsys) -> None:
    passages = tmp_path / "p.txt"
    passages.write_text("a passage", encoding="utf-8")
    out = tmp_path / "out"
    argv = ["draft_content", "--skill", SKILL, "--passages", str(passages), "--out", str(out)]
    settings.app_env = "production"
    assert main(argv) == 2 and "production" in capsys.readouterr().err
    settings.app_env, settings.llm_api_key = "development", ""
    assert main(argv) == 2 and "LLM_API_KEY" in capsys.readouterr().err
    assert not out.exists()


def test_the_cli_writes_drafts_with_an_injected_provider(tmp_path: Path, capsys) -> None:
    passages = tmp_path / "p.txt"
    passages.write_text("a passage", encoding="utf-8")
    out = tmp_path / "out"
    argv = ["draft_content", "--skill", SKILL, "--passages", str(passages), "--out", str(out)]
    code = main(argv, provider=FakeProvider([_reply(_item(1))]))
    assert code == 0 and len(list(out.glob("*.yaml"))) == 1
    assert "1 written" in capsys.readouterr().out
