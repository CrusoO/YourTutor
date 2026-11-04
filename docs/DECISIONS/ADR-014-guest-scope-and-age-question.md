# ADR-014: Guest scope (D14): guests for everyone, with a neutral age question first

**Status:** Accepted (founder default, revised 5 Nov 2026)
**Date:** 2026-11-05
**Decision ID:** D14

## Context

The founder wants guests for everyone. Children must not be exposed to open topics.

## Decision

The first screen asks neutrally: "Which class are you in? / I'm 18 or older".

- Under 18 or unknown: syllabus scope, minor tier, strictest safety.
- 18 or older: adult tier with open learning topics. The safety classifier is still on, and harmful instructions are still refused.
- The age answer is self-declared. It is never treated as verified for consent purposes.
- A guest is a minor by default.

## Consequences

- Tiers (guest, minor, adult, corporate) change scope and safety strictness, never the action list.
- The closed action registry holds 7 actions: `start_practice`, `continue_learning`, `show_subjects`, `switch_language`, `new_chat` (needs confirmation), `sign_in_prompt`, `help`. It never widens without a written proposal and the founder's approval. Model output never becomes an action.
- `docs/HOME_AND_ONBOARDING.md` is updated for the age question in Stage 2 (v0.95). This ADR does not edit it.
- Phase 0 (v0.9) ships guest syllabus scope and the age question.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D14, prompt section 1 D14, section J (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.8.

## Revisions

- 2026-11-05: revised to guests for everyone with the age question.
