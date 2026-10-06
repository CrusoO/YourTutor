"""Scene size budget: at most 50 KB of script per minute of playback, audio excluded."""

from __future__ import annotations

import json

from app.lessons.schema import (
    DrawArrow,
    DrawShape,
    Highlight,
    PauseAndAsk,
    Scene,
    WriteText,
)

MAX_KB_PER_MINUTE = 50
ASK_SECONDS = 8.0  # reading a question and answering it


def scene_duration_seconds(scene: Scene) -> float:
    """Estimated playback time, matching the player's pacing (draw time plus caption dwell)."""
    total = 0.0
    for step in scene.steps:
        for action in step.actions:
            if isinstance(action, WriteText):
                total += min(1.1, 0.25 + 0.055 * len(action.text))
            elif isinstance(action, DrawShape | DrawArrow | Highlight):
                total += 0.35
            elif isinstance(action, PauseAndAsk):
                total += ASK_SECONDS
        total += max(1.6, len(step.caption.en) * 0.042)
    return total


def scene_bytes(scene: Scene) -> int:
    data = scene.model_dump(mode="json", by_alias=True, exclude_none=True)
    return len(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def scene_kb_per_minute(scene: Scene) -> float:
    minutes = scene_duration_seconds(scene) / 60
    return scene_bytes(scene) / 1024 / minutes
