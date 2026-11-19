"""An episode opens at a wrong answer, carries belief and help choices, closes at a right one."""

from __future__ import annotations

from app.learner.reason import assess
from app.learner.reason.episode import (
    Episode,
    after_answer,
    after_correction,
    after_move,
    public,
)
from app.learner.reason.moves import Guidance
from tests.orchestrator.conftest import catalog_item, make_learner, make_session

SKILL = "MATH.S1"


def _wrong(prev: Episode | None = None, response: str = "-12", **kw):  # type: ignore[no-untyped-def]
    item = catalog_item(answer="12", rules=(("MC.SIGN", ("-12",)),))
    learner = make_learner(p_known={SKILL: 0.1})
    prior = prev.posterior if prev else None
    found = assess(item, response, learner, make_session(item), prior=prior)
    return after_answer(
        prev, SKILL, correct=False, hinted=False, confidence=kw.get("confidence"), assessment=found
    )


def test_a_wrong_answer_opens_an_episode_with_help_to_offer() -> None:
    ep, effect = _wrong()
    assert effect is None
    assert ep.posterior is not None
    assert ep.offered and len(ep.offered) == 3
    shown = public(ep)
    assert shown is not None and shown["band"] == "likely" and shown["offer"] == list(ep.offered)


def test_a_right_answer_closes_the_episode_and_keeps_the_guidance_level() -> None:
    ep, _ = _wrong()
    done, _ = after_answer(
        ep, SKILL, correct=True, hinted=False, confidence="sure", assessment=None
    )
    assert done.posterior is None and done.offered == ()
    assert public(done) is None
    assert done.guidance.wins == 1


def test_the_help_chosen_is_credited_to_the_next_answer() -> None:
    ep, _ = _wrong()
    ep = after_move(ep, ep.offered[0])
    assert ep.pending == ep.offered[0]
    _, effect = after_answer(
        ep, SKILL, correct=True, hinted=False, confidence=None, assessment=None
    )
    assert effect == {"family": ep.offered[0], "correct": True}
    again, effect2 = _wrong(ep)
    assert effect2 == {"family": ep.offered[0], "correct": False}
    assert again.pending is None


def test_another_way_offers_a_different_family_first() -> None:
    ep, _ = _wrong()
    first = ep.offered[0]
    ep = after_move(ep, first)
    nxt, _ = _wrong(ep)
    # four families, three shown: the one just used is left out, so it really is another way
    assert first not in nxt.offered


def test_a_correction_lowers_the_named_cause_and_never_crashes_without_one() -> None:
    ep, _ = _wrong()
    before = ep.posterior.get("misconception:MC.SIGN")  # type: ignore[union-attr]
    corrected = after_correction(ep, "misconception")
    assert corrected.posterior.get("misconception:MC.SIGN") < before  # type: ignore[union-attr]
    assert after_correction(ep, "slip") == ep
    assert after_correction(Episode(SKILL), "misconception") == Episode(SKILL)


def test_a_move_outside_the_known_families_is_ignored() -> None:
    ep, _ = _wrong()
    assert after_move(ep, "magic") == ep


def test_an_episode_for_another_skill_starts_fresh() -> None:
    ep, _ = _wrong()
    other, _ = after_answer(
        ep, "MATH.S2", correct=True, hinted=False, confidence=None, assessment=None
    )
    assert other.skill == "MATH.S2" and other.guidance.wins == 1 and other.recent == ()


def test_the_payload_round_trips_and_damaged_payloads_are_dropped() -> None:
    ep, _ = _wrong()
    ep = after_move(ep, ep.offered[0])
    again = Episode.from_payload(ep.to_payload())
    assert again is not None
    assert again.skill == ep.skill and again.pending == ep.pending
    assert again.guidance == ep.guidance and again.recent == ep.recent
    assert again.posterior is not None and ep.posterior is not None
    assert (
        abs(
            again.posterior.get("misconception:MC.SIGN") - ep.posterior.get("misconception:MC.SIGN")
        )
        < 1e-9
    )
    damaged: list[object] = [None, [], {}, {"skill": 3}, "x"]
    for bad in damaged:
        assert Episode.from_payload(bad) is None
    messy = Episode.from_payload(
        {
            "skill": SKILL,
            "weights": {"a": "x", "b": 1},
            "recent": ["nope", "picture"],
            "pending": "zzz",
        }
    )
    assert messy is not None and messy.pending is None and messy.recent == ("picture",)
    assert messy.guidance == Guidance()
