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
- **Targeted tests (from G7, until the final run):** per step and per milestone run only the tests that cover the changed code and what depends on it (grep usages), plus ruff, mypy and the region check. The full Postgres suite and the random-seed passes run once, at the very end, when the user asks. Record "targeted tests: N passed" in PLAN ticks and say the audit baseline's full counts are pending. If a test changes because v2 changes behaviour, change it in the same commit and say why.
- Keep the suite green for what you ran. If a test changes because v2 changes behaviour, change it in the same commit and say why.
- Policy, diagnosis, ladder and widget predicates are pure functions. Logic mirrored by the offline player gets a shared fixture in packages/shared/fixtures/.
- Never weaken a guardrail in PLAN.md §5. If one blocks you, stop and ask.
- New content is status: draft. Never machine-translate strings and mark them approved.
- No country/board/language/time-zone literals outside config/, content/, migrations/, tests/.
- Ambiguous but not blocking: pick the simplest option, add a PLAN.md Decisions row.
- Don't push, don't rewrite git history, don't touch .env files.
- Every milestone report ends with a **"How to see it"** block: URL, which /dev scenario or login, exact clicks, what to expect, screenshot paths. If nothing is visible, say so explicitly.
- Anything student-visible: run `python -m app.dev seed_scenarios` and `npm run test:ui`, view the screenshots, and list what changed on screen (see docs/UI_PREVIEW.md).

## Commands (run from Git Bash on Windows; verified 2026-10-04)

Environment actually used: Windows 11, Git Bash, Docker Desktop (compose stack running on the Windows side), Python 3.13 with packages installed for the user (no venv), Node from Windows. The repo lives on `/mnt/c`; WSL (Ubuntu) has no Docker integration or Python env, so do not run the checks there unless that is set up. Check the `docker compose ps` stack is healthy first.

- Always use `127.0.0.1`, not `localhost`, for the local database: on this machine `localhost` resolves to `::1` first, Docker does not answer there, and every new connection stalls exactly 30 s (this alone made full test runs take up to 2 hours).
- Stack: `docker compose up -d postgres redis` (the compose service is `postgres`, not `db`)
- API tests: `cd apps/api && TEST_DATABASE_URL=postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_test python -m pytest -q` (slow: about 7 min on Postgres; the suite must pass with `-p no:randomly` and with `-p randomly --randomly-seed=N`)
- API lint/types: `cd apps/api && ruff check . && ruff format --check . && python -m mypy .`
- Web: `cd apps/web && npx vitest run && npx tsc --noEmit`
- Region check: `cd apps/api && python scripts/check_region_literals.py`
- Locales: `cd apps/api && PYTHONPATH=. python scripts/generate_web_locales.py` (writes `packages/shared/generated/locales.json`; expect no git diff)
- Content: `cd apps/api && python -m app.content validate ../../content/` then `python -m app.content load ../../content/`
- UI preview: `cd apps/api && ALLOW_DRAFT_CONTENT=true python -m app.dev seed_scenarios` (needs a migrated, content-loaded database; the preview uses `POSTGRES_DB=yourtutor_preview`); `cd apps/web && npm run test:ui -- --workers=1` (API with `DEV_TOOLS=true`; screenshots in `apps/web/test-results/screens/`). Details: docs/UI_PREVIEW.md.
- Python edits on Windows: pass `encoding="utf-8"` to `open()` (or set `PYTHONUTF8=1`); the working tree may be CRLF while git stores LF.

## When a milestone is done

1. Run the targeted tests and checks above (Playwright too if UI changed); the full runs wait for the final pass.
2. Tick checkboxes in PLAN.md with "Met " and test counts; update V2_GAP_AUDIT.md baseline.
3. Update ARCHITECTURE.md where details settled.
4. Report: what changed, new Decisions, test counts before/after, deferred items, and the "How to see it" block. Then stop.

