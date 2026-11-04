# ADR-012: Keys and the zip (D12): the founder's job, not the agent's

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D12

## Context

Keys were pasted on 2026-10-20, and an `EduVideoEngine.zip` containing a `.env` sits in OneDrive [Audit section 12].

## Decision

The founder rotates every key pasted on 2026-10-20 and deletes `EduVideoEngine.zip` from OneDrive and its recycle bin.

Agents never touch keys. They remind the founder. Agents never print, log or commit key or `.env` values. Docs name variables only.

## Consequences

- Gate for v0.9: the founder has rotated keys and deleted the zip.
- Secrets handling rule for all streams: names only; never log OTPs, tokens or children's text.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D12, prompt section 1 D12 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 2 (v0.9 gate) and "What you do yourself".

## Revisions

- None yet.
