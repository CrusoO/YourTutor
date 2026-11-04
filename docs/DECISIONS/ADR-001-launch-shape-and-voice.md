# ADR-001: Launch shape (D1): maths-first, conversational, with push-to-talk voice

**Status:** Accepted (founder default, revised twice; last revision 5 Nov 2026)
**Date:** 2026-11-05
**Decision ID:** D1
**Numbering:** These ADRs use `ADR-NNN` in `docs/DECISIONS/`. The older integration ADRs in `docs/adr/` (0001 to 0003) keep their own four-digit numbers. Neither series renumbers the other.

## Context

The audit asked what shape Brownie should launch in. An earlier version of this decision put voice input in v2. The reasons were that children's audio is sensitive, Hinglish speech recognition is error-prone, and voice was assumed to be costly.

On 5 Nov 2026 the founder asked: "Why no mic? If they can't talk, how do we advertise it?" The voice paper found that:
- Sarvam speech-to-text is listed at Rs 30 per hour, billed per second [Checked: Sarvam docs].
- Hinglish recognition has improved, but rankings change with the test set [Checked, self-reported by a model author]. Brownie runs its own bake-off.
- Privacy can be handled by design (push-to-talk, no audio storage, no-retention vendor terms, consent for minors).

## Decision

Brownie launches maths-first and conversational, with push-to-talk voice input in v1.0 (Board Sprint, 15 Dec 2026). It also ships voice out, quick-reply chips and the maths keypad.

Rules:
- Push-to-talk only. Never always-listening.
- Audio is streamed to the speech-to-text vendor and never stored or logged by Brownie.
- Spoken answers go through the deterministic maths-speech parser and are read back for confirmation. They are never auto-submitted.
- Voice is off for minors unless the class's or guardian's consent record includes voice.
- Transcripts pass the same safety gate as typed text.
- Vendors are chosen only after the founder confirms their no-retention and no-training terms.
- Until the voice stream ships, the mic stays hidden (`VOICE_ENABLED=false`) so no dead button shows.
- Voice is an addition. It is never the only way in.

## Consequences

- v1.0 scope grows: a speech-to-text interface with two vendors, the maths-speech parser and read-back, voice consent flags, daily voice caps and a text-to-speech clip cache.
- Voice, not the LLM, becomes the largest variable cost. See `docs/PRODUCT.md` section on models and money.
- Research sprint R1 gains a speech-to-text bake-off, a parser test, a listening test and vendor contract checks. See `docs/RESEARCH_PLAN.md`.
- The conversational design in the fix plan section H ("voice out but not in yet") is superseded by this decision.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0, row D1, and prompt section 1 (parent folder, not in this repo).
- Brownie-Voice-Marketing-and-Pricing.md, sections 1, 2 and 7 (parent folder, not in this repo).

## Revisions

- 2026-11-04: first version of the fix plan (maths-first, no mic, voice out only).
- 2026-11-05: revised. Push-to-talk voice input moved into v1.0 (Brownie-Voice-Marketing-and-Pricing.md section 7, "D1 replaced").
