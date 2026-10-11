"""Layer B: scoped hybrid search over approved passages (ARCHITECTURE section 12.1).

Candidates are always filtered by the student's context key (curriculum, book, chapter) and
language before anything is scored, so a question can never surface text from another book or
chapter. The score blends shared wording with embedding similarity. Pure ranking; the database
read is `candidates_for`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ask.config import AskConfig, ask_config
from app.ask.embed import Embedder, cosine, default_embedder, tokens
from app.content.gate import content_status_is_servable
from app.db.models import PassageRow

# Parts of the keyword score: all passage words, the first sentence (its topic), adjacent pairs.
WHOLE_SHARE, TOPIC_SHARE, PHRASE_SHARE = 0.4, 0.3, 0.3
STOPWORDS = frozenset(
    "a an the is are was were be do does did i me my we you your it its this that these those "
    "of to in on at by for from with and or but how what why when where which who can "
    "could should would will if so as than then there their they them about into over under "
    "please tell explain mean means".split()
)


@dataclass(frozen=True)
class Hit:
    passage_id: str
    section_id: str
    skill_ids: tuple[str, ...]
    text: str
    page: int | None
    source_ref: str | None
    score: float


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def content_words(text: str) -> set[str]:
    return {_stem(w) for w in tokens(text) if w not in STOPWORDS and not w.isdigit()}


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]


def _weights(words: set[str], documents: list[set[str]]) -> dict[str, float]:
    """Rarer words weigh more; a word no passage uses weighs most, so unmatched terms count."""
    n = len(documents)
    return {w: math.log(1 + (n + 1) / (sum(w in d for d in documents) + 0.5)) for w in words}


def _coverage(weights: dict[str, float], found: set[str]) -> float:
    total = sum(weights.values())
    return sum(weight for w, weight in weights.items() if w in found) / total if total else 0.0


def _sequence(text: str) -> list[str]:
    """Content words in order, so 'the inverse of an operation' still reads 'inverse operation'."""
    return [_stem(w) for w in tokens(text) if w not in STOPWORDS and not w.isdigit()]


def phrase_score(question: str, passage_text: str, fallback: float = 0.0) -> float:
    """Share of the question's adjacent content-word pairs that also sit together in the passage
    (`fallback` when the question has a single content word, so it has no pairs)."""
    asked = _sequence(question)
    pairs = set(zip(asked, asked[1:], strict=False))
    if not pairs:
        return fallback
    held = _sequence(passage_text)
    return len(pairs & set(zip(held, held[1:], strict=False))) / len(pairs)


def keyword_score(
    question: str, passage_text: str, documents: list[set[str]] | None = None
) -> float:
    """Weighted share of the question's content words found in the passage; the passage's first
    sentence (its topic) counts for more than the rest."""
    wanted = content_words(question)
    if not wanted:
        return 0.0
    weights = _weights(wanted, documents or [content_words(passage_text)])
    whole = _coverage(weights, content_words(passage_text))
    topic = _coverage(weights, content_words(_first_sentence(passage_text)))
    phrase = phrase_score(question, passage_text, fallback=whole)
    return WHOLE_SHARE * whole + TOPIC_SHARE * topic + PHRASE_SHARE * phrase


def rank(
    question: str,
    candidates: list[PassageRow],
    *,
    embedder: Embedder | None = None,
    cfg: AskConfig | None = None,
) -> list[Hit]:
    cfg = cfg or ask_config()
    embedder = embedder or default_embedder()
    vector = embedder.embed(question)
    documents = [content_words(row.text) for row in candidates]
    hits = []
    for row in candidates:
        similarity = max(0.0, cosine(vector, list(row.embedding or [])))
        score = cfg.keyword_weight * keyword_score(question, row.text, documents) + (
            cfg.vector_weight * similarity
        )
        hits.append(
            Hit(
                passage_id=row.id,
                section_id=row.section_id,
                skill_ids=tuple(row.skill_ids or ()),
                text=row.text,
                page=row.page,
                source_ref=row.source_ref,
                score=round(score, 6),
            )
        )
    hits.sort(key=lambda h: (-h.score, h.passage_id))
    return hits[: cfg.top_k]


def candidates_for(
    db: Session,
    *,
    curriculum_id: str,
    book_id: str,
    chapter_id: str,
    locales: list[str],
    allow_draft: bool,
) -> list[PassageRow]:
    """Approved (in dev, draft) passages of exactly this book and chapter, in these languages."""
    rows = db.scalars(
        select(PassageRow).where(
            PassageRow.curriculum_id == curriculum_id,
            PassageRow.book_id == book_id,
            PassageRow.chapter_id == chapter_id,
            PassageRow.locale.in_(locales),
        )
    ).all()
    return [r for r in rows if content_status_is_servable(r.status, allow_draft=allow_draft)]
