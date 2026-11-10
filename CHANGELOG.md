# Changelog

All notable changes to YourTutor (Brownie) are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow the plan in [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/RELEASES.md](docs/RELEASES.md).

## [Unreleased]

Code for v0.9 Safe Base (target 12 Nov 2026) merged in PR #30 on 5 Nov 2026 (distress detection and helplines, login fixes, the production start guard, guest syllabus scope; the same PR also carries the pitch video section). The v0.9 gate is not closed: the helplines are still marked `verified: false` (production will not start until they are verified), and key rotation is open. v0.95 Clean Base is in progress. A version ships only when its gate passes. See [docs/ROADMAP.md](docs/ROADMAP.md).

### Added
- Retention, export and delete coverage: `python -m app.retention <job>|all [--dry-run]` now also clears sign-in code rows (24 h), rate-limit events (7 d), expired sign-in tokens (30 d), AI call reply text (14 d) and metadata (90 d), and video jobs with their files (30 d); the export now includes sessions, answers, progress, review cards, lesson records and more; account and guest deletion explicitly clear every table that refers to the learner (a test lists them from the models); guests can export and delete their own data with their token (`GET /guest/{id}/export`, `DELETE /guest/{id}`). AI reply text is no longer sampled in production unless `LLM_REVIEW_SAMPLE_RATE` is set.
- Staff-only content review screen at `/staff/review` (teacher or admin): each draft item with its solver-checked answer, wrong options with their misconception labels and any Hindi text; Approve, Reject or Fix with a note, recorded per reviewer in the new `content_reviews` table (migration 0031). Two distinct approvals on the item's current content hash count as approved; `python -m app.content apply-reviews` then writes them into the YAML.
- A production start now refuses to run with an AI route on (`ASK_ENABLED` or `EXPLAIN_ENABLED`) and `LLM_DAILY_CAP` at 0, so an open API cannot spend without a daily limit. Development is unchanged.
- Tutor chat: a server-side answer-leak guard that holds back the practice item's answer until two hints and an attempt (digits, English number words and Devanagari digits are checked); a streamed reply (`POST /explain/chat/stream`); the chat can use Claude models (#31).
- Lesson quizzes are checked with the maths verifier: a quiz whose marked answer disagrees with the solved value is dropped, and one the verifier cannot read is kept and marked `verified: false` (#34), with a "not checked" note under the question (#37).
- Claude calls for the chat and the lessons go through the official Anthropic SDK, in `app/llm/anthropic_client.py` (#45).
- `apps/api/requirements.lock` and `requirements-dev.lock` (Linux, Python 3.12); CI and the API image install from them (#43).
- Planning docs: `docs/PRODUCT.md`, `docs/ROADMAP.md`, `docs/RELEASES.md`, `docs/RESEARCH_PLAN.md`.
- Decision records `docs/DECISIONS/ADR-001` to `ADR-015` for decisions D1 to D15.
- `REMOVED.md` (deletion log) and `docs/parked.md` (features kept behind flags; flags and entry points checked in #42).

### Changed
- The practice policy no longer shows a hint that gives the answer away; it falls back to a neutral guiding question (#32). The offline policy in `apps/web/lib/offline/policy.ts` mirrors it (#34).
- The two video styles are named neutrally in the story prompts (#33).
- The web image is built in stages and runs `next start` instead of the dev server; `NEXT_PUBLIC_*` values are build arguments (#39).
- The "remember" and "child" trust answers on the landing page are marked pending counsel approval again (#40). Hindi and Nepali show the English text for the shortened chapter two until reviewed text exists (#41).
- The home-page JS sub-budget is 128 KB gzip, up from 125 KB (#47). The 150 KB page total is unchanged.
- `.env.example` no longer lists `LLM_PROVIDER` or `OPENAI_API_KEY`, which no code reads (#44).

### Removed
- Groq, Gemini and OpenRouter support, the `LLM_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY` and `OPENROUTER_API_KEY` settings, the OpenAI-style HTTP path in the explain services, and `litellm` with the packages only it needed. Claude (Anthropic) is the only LLM provider; `ANTHROPIC_API_KEY` is the one key and model names must start with `anthropic/` (production refuses any other). The gateway provider is now `AnthropicProvider`. See `REMOVED.md`.

### Fixed
- Six API tests that failed on Postgres in CI (#35); a mypy error in the safety classifier that appeared only with the Anthropic SDK installed (#36); a naive-versus-aware datetime comparison in `review_overdue` on SQLite (#38); a flaky groups test whose check collided with the random join code (#46).
