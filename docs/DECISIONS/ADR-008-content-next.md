# ADR-008: Content next (D8): one algebra chapter now, then fractions and decimals

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D8

## Context

The strategic wedge is Classes 6 to 8 [Research, per the plan], but the demo needs approved content this month.

## Decision

Approve one algebra chapter for the demo now. Then build fractions and decimals for Classes 6 to 8 using mistake functions.

A mistake function is a small function over an item's numbers that returns the wrong answer a student with a given misconception would give. Templates plus the solver produce verified items. Wrong options carry meaning, and diagnosis does not depend on an LLM guessing.

## Consequences

- Teacher Autopilot lets teachers name mistakes and approve cards while the machine builds, checks and translates. The plan estimates about 25 teacher-hours for a Classes 6 to 8 maths bank, against about 200 [as stated in the plan; not independently checked].
- The fractions pack is built Jan to Mar 2027 for v1.2 (April 2027), using the mistake library from research sprint R3.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D8, prompt section 1 D8 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.7.

## Revisions

- None yet.
