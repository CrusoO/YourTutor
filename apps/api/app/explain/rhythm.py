"""Does a written story teach like a person thinking with the viewer, or read like a voiceover?

Checks the narration of an animated story for the things that make the difference, as plain
rules that can be tested without a model: a length that fits one to two minutes, a real question
in each scene, sentences that are not all the same length, a pause after the question and a slow
reveal, and no skipped step of
the mechanism being explained. Each problem comes back as an instruction the repair call can act on.

The numbers are tunable defaults, not measured truths: a spoken pace of about 130 words a
minute gives the
word budget below, and the rest are rules of thumb about rhythm.
"""

from __future__ import annotations

import re
from typing import Any

# Spoken pace is about 130 words a minute, pauses included, so a minute and a half is about
# 200 words.
MIN_WORDS = 130  # a little over a minute
MAX_WORDS = 290  # about two minutes
MAX_WORDS_LONG_CHAIN = 330  # a mechanism with more than four steps may take a little longer
LONG_CHAIN = 4
SHORT_SENTENCE = 6  # words: a short sentence lands an idea
LONG_SENTENCE = 12  # words: a long one carries the reasoning
SAME_LENGTH = 3  # three sentences in a row within this many words of each other read as a drone
MAX_STEPS = 8

_MARKER = re.compile(r"\s*\[(?:pause|slow|fast)\]\s*$", re.IGNORECASE)
_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)?")
_STOP = frozenset(
    "that this with from into then than they them their there here what when where which "
    "while about because each other more most some such only also very just over under again "
    "its are was were been "
    "being have has had does did and for the you your not but can will".split()
)


def spoken(sentence: str) -> str:
    """The sentence as it is said: without a trailing pacing marker."""
    return _MARKER.sub("", sentence).strip()


def word_count(sentence: str) -> int:
    return len(_WORD.findall(spoken(sentence)))


def is_question(sentence: str) -> bool:
    return spoken(sentence).endswith("?")


def _sentences(scene: Any) -> list[str]:
    """A scene's sentences, whatever the model wrote there: only text, in order."""
    raw = scene.get("sentences") if isinstance(scene, dict) else None
    return [s for s in raw if isinstance(s, str)] if isinstance(raw, list) else []


def _covers(scene: Any) -> list[int]:
    """The step numbers a scene says it covers: only whole numbers, whatever else was written."""
    raw = scene.get("covers") if isinstance(scene, dict) else None
    return (
        [n for n in raw if isinstance(n, int) and not isinstance(n, bool)]
        if isinstance(raw, list)
        else []
    )


def total_words(scenes: list[dict[str, Any]]) -> int:
    return sum(word_count(s) for scene in scenes for s in _sentences(scene))


def _key_words(step: str) -> set[str]:
    return {w.casefold() for w in _WORD.findall(step) if len(w) >= 4 and w.casefold() not in _STOP}


def _has_marker(sentences: list[str], marker: str) -> bool:
    return any(re.search(rf"\[{marker}\]\s*$", s, re.IGNORECASE) for s in sentences)


def rhythm_issues(scenes: list[dict[str, Any]], chain: list[str] | None = None) -> list[str]:
    """What is wrong with the way this story is said, as instructions for a repair pass.

    An empty list means nothing to fix.
    """
    issues: list[str] = []
    chain = chain or []
    last = len(scenes) - 1

    # 1. length
    words = total_words(scenes)
    ceiling = MAX_WORDS_LONG_CHAIN if len(chain) > LONG_CHAIN else MAX_WORDS
    if words > ceiling:
        issues.append(
            f"The narration is {words} words; it must be at most {ceiling} (about two minutes). "
            "Cut whole sentences that repeat or decorate, not the steps of the explanation."
        )
    elif words < MIN_WORDS:
        issues.append(
            f"The narration is only {words} words; it needs at least {MIN_WORDS} (a little over a "
            "minute). Add the missing reasoning, one short sentence at a time."
        )

    for index, scene in enumerate(scenes):
        sentences = _sentences(scene)
        name = f"Scene {index + 1}"
        lengths = [word_count(s) for s in sentences]

        # 2. a real question in every scene but the last (the last may land the point instead)
        if index != last and not any(is_question(s) for s in sentences):
            issues.append(
                f"{name}: ask the viewer a real question the scene then answers (a sentence "
                "ending in "
                "'?'), like someone thinking out loud: 'So where does it go?'"
            )

        # 3. sentences that are not all the same size
        if len(sentences) >= 3:
            if min(lengths) > SHORT_SENTENCE:
                issues.append(
                    f"{name}: add one short sentence of {SHORT_SENTENCE} words or fewer "
                    "to land an idea."
                )
            if max(lengths) < LONG_SENTENCE:
                issues.append(
                    f"{name}: make one sentence longer, {LONG_SENTENCE} words or more, "
                    "to carry the reasoning."
                )
            for i in range(len(lengths) - 2):
                run = lengths[i : i + 3]
                if max(run) - min(run) <= SAME_LENGTH:
                    issues.append(
                        f"{name}: sentences {i + 1} to {i + 3} are almost the same length "
                        f"({run[0]}, {run[1]}, {run[2]} words). Vary them: one short, one longer."
                    )
                    break

    # 4. the pause after the question and the slow reveal
    if scenes and not _has_marker(_sentences(scenes[0]), "pause"):
        issues.append(
            "Scene 1: put [pause] at the end of the hook question, so the viewer can think."
        )
    reveals = [s for s in scenes if isinstance(s, dict) and s.get("role") == "reveal"]
    if reveals and not any(_has_marker(_sentences(s), "slow") for s in reveals):
        issues.append(
            "The reveal scene: put [slow] at the end of its single most important sentence."
        )

    # 5. no skipped step: every step of the mechanism is covered and actually spoken
    if chain:
        claimed: dict[int, list[int]] = {}
        for index, scene in enumerate(scenes):
            for claim in _covers(scene):
                if 1 <= claim <= len(chain):
                    claimed.setdefault(claim, []).append(index)
        for number, step in enumerate(chain, 1):
            owners = claimed.get(number)
            if not owners:
                issues.append(
                    f'Step {number} of the explanation is never covered: "{step}". '
                    "Add it to a scene and list its number in that scene's covers."
                )
                continue
            wanted = _key_words(step)
            said = {
                w.casefold()
                for i in owners
                for s in _sentences(scenes[i])
                for w in _WORD.findall(spoken(s))
            }
            if wanted and not wanted & said:
                issues.append(
                    f"Scene {owners[0] + 1} says it covers step {number} "
                    f'("{step}") but never says it. '
                    "Say that step in words."
                )
    return issues
