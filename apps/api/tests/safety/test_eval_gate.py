"""CI gate for Layer 1: recall and false positives on the labelled phrase set.

The set (`eval_phrases.tsv`) was written by hand and is not generated from the lexicon. Positives
are urgent or exam-stress phrases in English, Hindi and Hinglish; negatives include science and
maths questions that use words such as die, kill, sex and cut. The build fails when the lexicon
misses more than 2 percent of positives, or flags more than 3 percent of negatives.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.safety_lexicon import default_lexicon, detect

MIN_RECALL = 0.98
MAX_FALSE_POSITIVE = 0.03
SET = Path(__file__).with_name("eval_phrases.tsv")


def _rows() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in SET.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            label, language, category, text = line.split("\t")
            rows.append((label, language, category, text))
    return rows


def _measure() -> tuple[dict[str, list[int]], list[str], list[str]]:
    # per language: [positives, caught, negatives, flagged]
    stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    misses: list[str] = []
    false_positives: list[str] = []
    for label, language, _category, text in _rows():
        found = detect(text)
        row = stats[language]
        if label == "none":
            row[2] += 1
            if found.risk != "none":
                row[3] += 1
                false_positives.append(f"{language}: {text}")
        else:
            row[0] += 1
            if found.risk != "none":
                row[1] += 1
            else:
                misses.append(f"{language}: {text}")
    return stats, misses, false_positives


def test_the_eval_set_is_large_and_balanced() -> None:
    rows = _rows()
    assert len(rows) >= 300
    for language in ("en", "hi", "hinglish"):
        assert sum(1 for r in rows if r[1] == language and r[0] != "none") >= 20
        assert sum(1 for r in rows if r[1] == language and r[0] == "none") >= 25
    assert sum(1 for r in rows if r[0] == "concern") >= 30  # exam stress is covered
    assert len(default_lexicon().exact) >= 150


def test_recall_and_false_positives_meet_the_gate(capsys) -> None:  # type: ignore[no-untyped-def]
    stats, misses, false_positives = _measure()
    positives = sum(s[0] for s in stats.values())
    caught = sum(s[1] for s in stats.values())
    negatives = sum(s[2] for s in stats.values())
    flagged = sum(s[3] for s in stats.values())
    with capsys.disabled():
        for language, (p, c, n, f) in sorted(stats.items()):
            print(
                f"\nlayer1 {language}: recall {c}/{p} = {c / p:.3f}, false positives {f}/{n}",
                end="",
            )
        print(f"\nlayer1 all: recall {caught}/{positives}, false positives {flagged}/{negatives}")
    assert caught / positives >= MIN_RECALL, f"missed: {misses}"
    assert flagged / negatives <= MAX_FALSE_POSITIVE, f"flagged: {false_positives}"


def test_every_language_meets_the_recall_gate_on_its_own() -> None:
    stats, misses, _ = _measure()
    for language, (p, c, _n, _f) in stats.items():
        assert c / p >= MIN_RECALL, f"{language} missed: {[m for m in misses if language in m]}"


def test_urgent_positives_are_not_downgraded_to_concern() -> None:
    wrong = [
        text
        for label, _lang, _cat, text in _rows()
        if label == "urgent" and detect(text).risk == "concern"
    ]
    assert wrong == []
