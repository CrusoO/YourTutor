# ADR-006: Answer reveal (D6): only after 2 hints and an attempt, enforced in code

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D6

## Context

The audit found that practice enforces a hint ladder, but chat has no code guard [Audit section 3]. A prompt instruction alone can be bypassed.

## Decision

Chat may reveal an answer only after 2 hints and an attempt on the active item. This is enforced in code (an answer-leak guard using verifier equivalence), not in the prompt. The same rule applies in practice and in chat.

## Consequences

- The leak guard checks model output before it is shown. On a leak, Brownie uses authored text instead.
- The safety layers (distress detection, scope, the leak guard, the verifier, the action registry) are protected. Any change that could weaken them stops and asks the founder.
- The rule goes into `docs/TUTOR_CONSTITUTION.md` in Stage 2 (v0.95), along with the verification ladder, tiers and the registry rule. This ADR does not edit that file.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D6, prompt section 1 D6 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.6.

## Revisions

- None yet.
