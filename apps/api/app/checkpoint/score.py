"""Checkpoint scoring. Never writes mastery or FSRS."""

from __future__ import annotations

from collections import defaultdict


def score_answers(answers: list[dict]) -> dict:
    """Pure score: fraction correct plus per-skill tallies."""
    per_skill: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "n": 0})
    correct = 0
    for row in answers:
        skill = row.get("skill_id") or "unknown"
        per_skill[skill]["n"] += 1
        if row.get("correct"):
            per_skill[skill]["correct"] += 1
            correct += 1
    n = len(answers)
    return {
        "score": (correct / n) if n else 0.0,
        "n": n,
        "correct": correct,
        "per_skill": dict(per_skill),
    }
