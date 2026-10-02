from app.checkpoint.score import score_answers


def test_score_answers_per_skill() -> None:
    result = score_answers(
        [
            {"item_id": "A", "skill_id": "S1", "correct": True},
            {"item_id": "B", "skill_id": "S1", "correct": False},
            {"item_id": "C", "skill_id": "S2", "correct": True},
        ]
    )
    assert result["n"] == 3
    assert result["correct"] == 2
    assert result["per_skill"]["S1"] == {"correct": 1, "n": 2}
    assert result["score"] == 2 / 3
