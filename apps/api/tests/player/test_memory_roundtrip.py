from __future__ import annotations

import json
from collections import defaultdict

from app.player.runtime import _dump_memory, _load_memory


def test_bkt_memory_survives_a_json_round_trip_with_warmup_skills() -> None:
    memory: dict = {
        "bkt_done": {"I1", "I2"},
        "hinted": {"I2"},
        "first_wrong": set(),
        "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
        "warmup_skills": {("session-1", "MATH.S1")},
    }
    memory["session_unhinted"]["session-1"]["MATH.S1"] = [2, 3]
    stored = json.loads(json.dumps(_dump_memory(memory)))  # what the plan column does
    loaded: dict = _load_memory(stored)
    assert loaded["warmup_skills"] == {("session-1", "MATH.S1")}
    assert loaded["session_unhinted"]["session-1"]["MATH.S1"] == [2, 3]
    assert loaded["bkt_done"] == {"I1", "I2"}
    assert loaded["session_unhinted"]["other"]["MATH.S1"] == [0, 0]  # still a defaultdict
