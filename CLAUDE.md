# CLAUDE.md — working agreement for this repo

## Read first (sources of truth)

- PLAN.md — milestones, Decisions, guardrails (§5), milestone protocol (§6)
- ARCHITECTURE.md — design (v2); the transition table is normative
- docs/TUTOR_CONSTITUTION.md — tutor behaviour
- .cursor/rules/project.mdc — guardrails as rules (same content as PLAN §5)
- V2_GAP_AUDIT.md — current status and test baseline

If these disagree with the code or each other, stop and report; don't guess.

## How to work

- One milestone at a time, only when told which one. Never start the next milestone.
- Break the milestone into small ordered steps and show them before coding.
- Tests first for each Accept item; commit after each step (message names step + milestone).
- Keep the full suite green at every commit. If a test changes because v2 changes behaviour, change it in the same commit and say why.
- Policy, diagnosis, ladder and widget predicates are pure functions. Logic mirrored by the offline player gets a shared fixture in packages/shared/fixtures/.
- Never weaken a guardrail in PLAN.md §5. If one blocks you, stop and ask.
- New content is status: draft. Never machine-translate strings and mark them approved.
- No country/board/language/time-zone literals outside config/, content/, migrations/, tests/.
- Ambiguous but not blocking: pick the simplest option, add a PLAN.md Decisions row.
- Don't push, don't rewrite git history, don't touch .env files.

## Commands (run from WSL, repo on the WSL filesystem)

- Stack: `docker compose up -d db redis`
- API tests: `cd apps/api && TEST_DATABASE_URL=postgresql+psycopg://tutor:tutor@localhost:5432/yourtutor_test pytest -q`
- API lint/types: `cd apps/api && ruff check . && mypy .`
- Web: `cd apps/web && npx vitest run && npx tsc --noEmit`
- Region check: `python scripts/check_region_literals.py`
- Locales: `python scripts/generate_web_locales.py`
- Content: `python -m app.content validate content/` then `python -m app.content load content/`

## When a milestone is done

1. Run all of the above (Playwright too if UI changed).
2. Tick checkboxes in PLAN.md with "Met " and test counts; update V2_GAP_AUDIT.md baseline.
3. Update ARCHITECTURE.md where details settled.
4. Report: what changed, new Decisions, test counts before/after, deferred items. Then stop.

