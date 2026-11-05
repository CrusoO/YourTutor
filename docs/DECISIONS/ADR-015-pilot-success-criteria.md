# ADR-015: Pilot success (D15): outside test gain, renewal, teacher time, error rate

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D15

## Context

Eedi's trial showed no gain on a standardised test [Research, per the plan], so in-app scores alone will not convince schools.

## Decision

The pilot succeeds only if all four hold:
- (a) An outside test gain versus a comparison class.
- (b) The school renews.
- (c) Teachers' net minutes saved is greater than 0.
- (d) The published content error rate is under 1%.

## Consequences

- Pilot term (Apr to Sep 2027) uses a pre-registered plan and a pre/post outside test. See research sprint R6 in `docs/RESEARCH_PLAN.md`.
- The v2.0 gate repeats these criteria. See `docs/ROADMAP.md`.
- An honest null result is reported as a null result.
- North star metric: mistakes fixed and still fixed 14 days later, per active learner per week.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D15, prompt section 1 D15 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.11 and Part 4.3.

## Revisions

- None yet.
