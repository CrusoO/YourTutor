# ADR-002: First users (D2): Board Sprint first, then adults, then schools

**Status:** Accepted (founder default, revised 5 Nov 2026 for exam season)
**Date:** 2026-11-05
**Decision ID:** D2

## Context

Board exams are close. The fix plan lists these dates, and says to check the official sites before showing any date to users:
- UP Board Class 10 and 12: 5 to 24 Feb 2027 (pre-boards about 18 Jan).
- CBSE Class 10 and 12: expected mid-Feb 2027 (official date sheet not out at time of writing).
- CBSE Class 10 second (optional improvement) exam: about mid-May 2027.
- New academic session: 1 Apr 2027.

Existing content (406 items, linear equations) fits Class 10 Algebra "Pair of linear equations in two variables". Schools will not start a new Classes 6 to 8 tool during exam months. A pilot also needs a full term to measure.

## Decision

Serve users in this order:
1. **Board Sprint** (Nov 2026 to May 2027): Class 10 maths revision, Algebra first (pair of linear equations, then quadratics, AP, polynomials). Students arrive through a teacher's class code (the school is the data fiduciary) or a guardian sign-up with a consent record.
2. **Adults (18+)** self-serve from day one.
3. **Classes 6 to 8 school pilot** starts with the new session in April 2027. Sell it Jan to Mar using Board Sprint evidence.
4. **School consent mode** is ready before DPDP core duties start (about 13 to 14 May 2027).

Nepal comes after the April pilot.

## Consequences

- v1.0 targets 15 Dec 2026, giving about 7 weeks before the February boards and a second chance in May.
- An exam freeze runs 1 Feb to 31 Mar 2027. See `docs/ROADMAP.md`.
- The exam season raises safety stakes (late-night, high-stress use by 15 to 16 year olds). An exam-stress category and a gentle late-night stop for minors are added.
- Board Sprint students are minors. Do not treat the gap before the DPDP date as a loophole. Use class codes and guardian consent records from day one [Judgment in the source].
- Phase 1 exit criteria gain: at least 60 approved original items, an exam-stress category in the safety eval, and a teacher class code with a class mistake list.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D2, prompt section 1 D2, and section G (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.2 and Part 2.

## Revisions

- 2026-11-05: revised for exam season. Order set as above.
