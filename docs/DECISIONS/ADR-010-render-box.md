# ADR-010: Render box (D10): ARM spike first, x86 VM as fallback

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D10

## Context

ARM support on Oracle A1 for ffmpeg, Kokoro and Piper is unverified [Audit section 9].
## Decision

Run a one-day ARM spike on Oracle A1 for ffmpeg, Kokoro and Piper. If anything fails, plan an x86 VM.

Ask the founder before creating any cloud resource.

## Consequences

- No cloud resource is created without founder approval.
- The deploy stream (Stream H) reports the spike result before the v1.0 deploy.
- Fixed hosting costs in the plan are assumptions (API, video and Kokoro server at $0 to 40 per month) until the spike and real usage are measured.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D10, prompt section 1 D10 (parent folder, not in this repo).
- Brownie-Voice-Marketing-and-Pricing.md, section 5.4.

## Revisions

- None yet.
