# ADR-011: Ship branch (D11): one integration branch, merge plan needs founder OK

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D11

## Context

The audit found the conversation layer (PR #29), the action router and the hardening batch on different branches [Audit sections 1 and 16].

## Decision

Build one `integration` branch from `master` (which has PR #29, the conversation layer, and the action router) plus `feat/hardening-batch`.

The lead agent proposes the merge plan and waits for the founder's OK before merging anything.

Branch model from the release process:
- `main` is production.
- `release/x.y` is a release being stabilised.
- `integration` is where reviewed workstreams merge.
- `fix/...` and `feat/...` are workstream branches in their own worktrees.
- Never commit to main or master directly.

## Consequences

- Consolidation is Stage 2 (v0.95 Clean Base), after Safe Base.
- Gate for v0.95: one integration branch, CI green in both repos, the same tests pass before and after, `REMOVED.md` complete.
- Note: this ADR records the plan's branch names. Actual branch names in the repo may differ; the Stage 2 merge plan will state them.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D11, prompt section 1 D11 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 3.3 and Part 6 Stage 2.

## Revisions

- None yet.
