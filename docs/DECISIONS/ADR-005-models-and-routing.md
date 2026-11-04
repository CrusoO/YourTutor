# ADR-005: Models (D5): Haiku 5.5 by default, Sonnet 5.5 for hard turns

**Status:** Accepted (founder default, revised 5 Nov 2026)
**Date:** 2026-11-05
**Decision ID:** D5

## Context

The founder chose Haiku by default to keep cost low. Prices in the plan [Checked, API docs and audit]: Haiku 5.5 is $0.10 in / $0.50 out per million tokens. Sonnet 5.5 is $2 / $10.

Estimated cost per learner per month (fix plan section I): about $0.08 all-Haiku (explain-heavy), and about $0.31 worst case at the 15% Sonnet cap. Practice-only sessions cost about $0.00065 each.

## Decision

- Default live model: `claude-haiku-5-5`.
- Escalate a turn to `claude-sonnet-5-5` only by deterministic rules, capped at 15% or less of a learner's daily LLM calls, plus a global monthly Sonnet budget. Above the budget, stay on Haiku.
- Hard-turn rules: wheel-spinning; the same misconception 3 times after hint 2; "why" asked twice on a step; explain-back "not yet" twice; multi-step 3 or more or difficulty 0.8 or more; an adult open-topic question labelled complex.
- The safety classifier, hints and praise always stay on Haiku.
- A refusal never escalates. Brownie uses authored text.
- Offline content drafting uses Sonnet 5.5 through the Message Batches API (50% off), then the verifier, then human review. Never generate lessons or stories live for students.
- Model IDs are pinned in config, never "latest".

API rules from the plan: no temperature, top_p or top_k; no prefill; check `stop_reason`; structured outputs; cache prefixes of 512 tokens or more; count tokens with `count_tokens`. Check the SDK docs rather than guessing.

## Consequences

- Report the weekly Sonnet share and reasons. This is also a research input (blind Haiku vs Sonnet ratings in R2).
- A new model version is treated like a feature: eval first (safety eval, leak guard, tutor-quality set graded blind by two teachers, cost and latency), then flag, staged rollout, rollback ID kept. See `docs/RELEASES.md`.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D5, prompt sections 1 D5 and 4B, section I (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.10 and Part 3.5.

## Revisions

- 2026-11-05: revised. Haiku default, Sonnet capped, per the founder's answer.
