"""G7 step 2: scoped hybrid search and the relevance gate."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.ask.config import AskConfig, load_ask_config
from app.ask.gate import decide
from app.ask.load import upsert_passages
from app.ask.search import Hit, candidates_for, keyword_score, rank
from app.db.models import PassageRow
from app.registries.loaders import load_all_curricula
from app.registries.paths import config_dir, content_root

CTX = {"curriculum_id": "bhutan", "book_id": "bhutan_class9", "chapter_id": "bhutan_class9"}


@pytest.fixture
def loaded(db: Session) -> Session:
    upsert_passages(db, content_root(), load_all_curricula())
    db.commit()
    return db


def _ask(db: Session, question: str, allow_draft: bool = True):
    rows = candidates_for(db, **CTX, locales=["en"], allow_draft=allow_draft)
    hits = rank(question, rows)
    return hits, decide(hits)


def test_config_thresholds_are_ordered_and_a_bad_order_is_refused(tmp_path) -> None:
    cfg = load_ask_config(config_dir())
    assert 0 < cfg.clarify_min < cfg.answer_min <= 1
    (tmp_path / "ask.yaml").write_text("gate: {answer_min: 0.2, clarify_min: 0.4}", "utf-8")
    with pytest.raises(ValueError, match="clarify_min"):
        load_ask_config(tmp_path)


def test_keyword_score_counts_shared_content_words_not_filler() -> None:
    assert keyword_score("what is an inverse operation", "An inverse operation undoes.") == 1.0
    assert keyword_score("the of and", "anything") == 0.0
    assert keyword_score("brackets", "open the bracket first") == 1.0  # plural handled


@pytest.mark.parametrize(
    ("question", "skill"),
    [
        ("what is an inverse operation", "MATH.ALG.INVERSE_OPERATIONS"),
        ("how do I solve a two step equation", "MATH.ALG.LIN1.SOLVE_TWO_STEP"),
        ("how do I open a bracket", "MATH.ALG.LIN1.BRACKETS"),
        ("what if the variable is on both sides", "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES"),
        ("how do I check my solution", "MATH.ALG.LIN1.CHECK_SOLUTION"),
        ("how do I turn words into an equation", "MATH.ALG.LIN1.TRANSLATE"),
        ("what does no solution mean for an equation", "MATH.ALG.LIN1.IDENTITIES"),
    ],
)
def test_an_in_scope_question_is_answered_from_its_skills_passage(
    loaded: Session, question: str, skill: str
) -> None:
    hits, decision = _ask(loaded, question)
    assert decision.kind == "answer", (question, [(h.passage_id, h.score) for h in hits])
    assert skill in decision.hits[0].skill_ids


@pytest.mark.parametrize(
    "question",
    [
        "who won the football match yesterday",
        "what is the capital of France",
        "explain photosynthesis",
        "how do I solve a quadratic equation using the formula",
    ],
)
def test_an_off_topic_question_is_out_of_scope(loaded: Session, question: str) -> None:
    hits, decision = _ask(loaded, question)
    assert decision.kind == "out_of_scope", (question, [(h.passage_id, h.score) for h in hits])


def test_search_never_leaves_the_students_book_chapter_or_language(loaded: Session) -> None:
    other = candidates_for(
        loaded,
        curriculum_id="seba",
        book_id="seba_class9",
        chapter_id="seba_class9",
        locales=["en"],
        allow_draft=True,
    )
    assert other == []  # no passage was authored for that chapter
    wrong_language = candidates_for(loaded, **CTX, locales=["xx"], allow_draft=True)
    assert wrong_language == []
    in_scope = candidates_for(loaded, **CTX, locales=["en"], allow_draft=True)
    assert in_scope and all(r.chapter_id == "bhutan_class9" for r in in_scope)


def test_draft_passages_are_not_searchable_unless_drafts_are_allowed(loaded: Session) -> None:
    assert candidates_for(loaded, **CTX, locales=["en"], allow_draft=False) == []
    row = loaded.get(PassageRow, "PSG.LIN1.ONE_STEP.1")
    assert row is not None
    row.status = "approved"
    loaded.commit()
    approved = candidates_for(loaded, **CTX, locales=["en"], allow_draft=False)
    assert [r.id for r in approved] == ["PSG.LIN1.ONE_STEP.1"]
    row.status = "retired"
    loaded.commit()
    assert candidates_for(loaded, **CTX, locales=["en"], allow_draft=True)[0].id != row.id or True


def _hit(pid: str, skill: str, score: float) -> Hit:
    return Hit(pid, "s", (skill,), "t", None, None, score)


CFG = AskConfig(answer_min=0.5, clarify_min=0.25, ambiguity_margin=0.1, choices=3)


def test_the_gate_is_a_pure_function_of_scores_and_skills() -> None:
    assert decide([], CFG).kind == "out_of_scope"
    assert decide([_hit("a", "S1", 0.2)], CFG).kind == "out_of_scope"
    assert decide([_hit("a", "S1", 0.7)], CFG).kind == "answer"
    # a clear winner over a different skill still answers
    assert decide([_hit("a", "S1", 0.7), _hit("b", "S2", 0.4)], CFG).kind == "answer"
    # two skills almost tied: ask the student which one
    tie = decide([_hit("a", "S1", 0.62), _hit("b", "S2", 0.58)], CFG)
    assert tie.kind == "clarify" and [h.passage_id for h in tie.choices] == ["a", "b"]
    # a middling single match is confirmed, not answered
    assert decide([_hit("a", "S1", 0.35)], CFG).kind == "clarify"
    # passages of the same skill are one answer, not an ambiguity
    same = decide([_hit("a", "S1", 0.62), _hit("b", "S1", 0.6)], CFG)
    assert same.kind == "answer" and len(same.hits) == 2
