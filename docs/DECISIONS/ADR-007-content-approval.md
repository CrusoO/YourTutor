# ADR-007: Content approval (D7): founder plus two teachers, by review screen

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D7

## Context

The audit found 438 drafts and zero approved files, and production refuses drafts [Audit section 3]. The demo needs approved content.

## Decision

The founder and two teacher reviewers approve items through a review screen (Teacher Autopilot, swipe to approve). Two approvals make an item live. The demo needs one approved algebra chapter of at least 60 items.

Each item stores source, licence, author and reviewers. Only approved items are used in production.

Content law from the plan:
- Never copy textbook or board-paper text.
- NCERT textbooks are non-commercial and no-derivatives, and NCERT terms forbid use in software [as stated in the plan].
- Openly licensed sources may be reused with attribution: Illustrative Mathematics 6 to 8 (2019 edition only) and OpenStax.
- Avoid Khan Academy and CK-12 (non-commercial licences).

## Consequences

- The founder must line up two teacher reviewers by 1 Dec 2026.
- The review screen is a v1.0 deliverable.
- A monthly 200-item content audit and near-duplicate scans feed the content error rate target (under 1%).

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D7, prompt section 1 D7 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.7 and Part 4.2.

## Revisions

- None yet.
