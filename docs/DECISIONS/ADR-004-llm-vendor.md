# ADR-004: LLM vendor (D4): Anthropic paid API only in production

**Status:** Accepted (founder default)
**Date:** 2026-11-05
**Decision ID:** D4

## Context

The audit found that free-tier providers (Groq, Gemini, OpenRouter) may log or train on inputs [Audit section 11, INFERRED]. Children's text must not go to them. One vendor also means one contract to show schools.

## Decision

Anthropic's paid API is the only LLM vendor in production. Remove Groq, Gemini and OpenRouter from production config. Keep their code only if it is trivially isolated behind a dev flag; otherwise delete it.

Before children's text is sent, the founder confirms Anthropic's data-retention and training terms for the account.

## Consequences

- The Anthropic Python SDK (`AsyncAnthropic`) replaces the current provider layer in Phase 1. The old `litellm` and `urllib` provider calls are deleted afterwards, with evidence, and logged in `REMOVED.md`.
- Dead env names (`LLM_TEMPERATURE`, `LLM_MODE`, the Groq, Gemini and OpenRouter keys) are removed from code and `.env.example` in Stage 2 (v0.95).
- Speech-to-text and text-to-speech vendors are separate decisions (see ADR-001) and need written no-retention and no-training terms.
- Current repo state may differ from this target until the cleanup is done. Trust what is measured at the time.

## Source

- Brownie-FIX-PLAN-and-MASTER-PROMPT.md, section 0 row D4, prompt section 1 D4 (parent folder, not in this repo).
- Brownie-COMPLETE-PLAN-v3.md, Part 1.8 and Part 5.2.

## Revisions

- None yet.
