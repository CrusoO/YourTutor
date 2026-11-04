# ADR-009: Video speed (D9): first playable second under 15 s

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D9

## Context

The audit found video generation about 3.4 times too slow for an "under 1 minute" promise [Audit section 9].

## Decision

- Request to first playable second: under 15 seconds, using streamed segments.
- A full 60 second video is ready in 60 seconds or less, uncontended.
- Popular topics are pre-rendered. Demo topics are pre-rendered for v1.0.
- One shared job budget covers the video engine.

## Consequences

- Streamed video segments are a v1.2 item. v1.0 ships video fixes and pre-rendered demo videos.
- Video work stays behind the engine contract. See `docs/ENGINE_INTEGRATION.md` and the existing `docs/adr/0001-engine-video-jobs.md`. No engine code or paths enter YourTutor.
- Speed metric: first video play under 15 s.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D9, prompt section 1 D9, section B7 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.11 and Part 2.

## Revisions

- None yet.
