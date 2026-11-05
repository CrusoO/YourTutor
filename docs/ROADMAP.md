# Brownie roadmap

Source: Brownie-COMPLETE-PLAN-v3.md, Part 2 (5 Nov 2026), in the parent folder (not in this repo).
This file is the roadmap for the YourTutor app. Product description is in [PRODUCT.md](PRODUCT.md). How a version moves is in [RELEASES.md](RELEASES.md). Research that feeds each version is in [RESEARCH_PLAN.md](RESEARCH_PLAN.md).

## Rules

Dates are **targets**. A version ships **only when its gate passes**. If a date slips, the scope shrinks. The safety work never shrinks.

## Versions

| Version | Name | Target date | What is in it | Gate (all must pass) |
|---|---|---|---|---|
| **v0.9** | **Safe Base** | 12 Nov 2026 | Phase 0 of the fix plan: two-layer distress detection and helplines, the login fixes (storage, SMTP, OTP lockout), the prod guard, guest syllabus scope and age question, mic hidden, no video prompt text stored, shared DB engine | Safety eval passes in CI; guest start works with storage blocked; prod guard tests; the founder has rotated keys and deleted the zip |
| **v0.95** | **Clean Base** | 22 Nov 2026 | Branch consolidation (master, hardening, PR #29, action router), code cleanup and refactor, docs consolidated, CI green | One integration branch; CI green in both repos; `REMOVED.md` and docs updated; no behaviour change (the same tests pass before and after) |
| **v1.0** | **Board Sprint** | **15 Dec 2026** | Phase 1: Anthropic SDK and streaming, Haiku/Sonnet routing, the answer-leak guard, verified quizzes, the conversation layer (chips, keypad, voice-out, memory, Hinglish), push-to-talk voice input (two speech-to-text vendors behind one interface, the maths-speech parser and read-back, voice consent flags, daily voice caps, a TTS clip cache), plans and payments (Free, Board Sprint Pass, Student, Adult Plus; usage caps), Google sign-in and class codes, global budgets, privacy and terms drafts, retention, the review screen, at least 60 approved Class 10 "pair of linear equations" items, teacher mistake list and warm-up, the deployed API, video fixes and pre-rendered demo videos | All Gate 1 criteria in the fix plan, plus the Board Sprint criteria (fix plan section G) |
| **v1.1** | **Pre-board** | 10 Jan 2027 | Quadratics and AP packs (approved), a teacher pre-board report, the exam-stress safety tune-up from real data, performance fixes | Content error audit under 1%; no P0 or P1 open |
| n/a | **Exam freeze** | 1 Feb to 31 Mar 2027 | **No changes to student-facing exam flows in production. Fixes only.** Development continues on `release/1.2` in staging | Any production change needs the founder's explicit approval |
| **v1.2** | **School Ready** | 1 Apr 2027 (new session) | Phase 2 core: school mode (enrolment, consent records, data agreement), the Classes 6 to 8 fractions and decimals pack with mistake functions, the teacher time-back loop, the parent weekly note, tiers, output moderation, error tracking, restore test, streamed video segments | Gate 2 in the fix plan; counsel sign-off; 2 to 3 schools signed for April |
| **v1.3** | **Consent Ready + Sprint 2** | 1 May 2027 | DPDP readiness (notices, consent records, retention, export and delete, grievance), Board Sprint 2 for the CBSE second Class 10 exam (about mid-May) | Counsel review complete before about 13 to 14 May 2027 |
| **v1.x** | **Pilot term** | Apr to Sep 2027 | Fixes and small improvements only, guided by research | A monthly release with the gates from [RELEASES.md](RELEASES.md) |
| **v2.0** | **Pilot Proven** | Oct to Nov 2027 (after the half-yearly exams as an outside measure) | Decided by the pilot results. Candidates: Teacher Autopilot on WhatsApp, the mystery-mistake miner, Mistake Monsters and Catch Brownie, Classes 6 to 10 maths and science, Nepal (Nepali), voice input improvements (if research supports it), per-skill BKT/IRT | Outside-test gain; renewals; teacher minutes saved above 0; error rate under 1% |
| **v3** | College, coding and aspirants | 2028 to 2030 | Code checker (runs tests), circuit and statistics checkers, verified skill records, adult Learn sets | Students pay or colleges renew |
| **v4** | Work skills | 2029 to 2032 | Practice-server labs, "Teach Brownie a bug", company libraries, team dashboards | Company renewals; measured fewer incidents |
| **v5** | Global | 2031 to 2035 | Local teacher networks, languages, offline and low-data mode, local law packs | A new country reaches pilot results with a local team |
| **v6** | Everyone | 2035 to 2040 | Lifelong learner-owned record, device actions (with permission), open mistake commons | North star growth |

## Status

- v0.9 Safe Base is in progress. See [CHANGELOG.md](../CHANGELOG.md).

## Law clock (from the plan)

- DPDP core duties apply from about 13 to 14 May 2027 (sources differ by one day).
- EU AI Act education obligations apply from 2 Dec 2027, if Brownie serves the EU.
- Counsel decides. Nothing in this roadmap is a legal conclusion.

## Decision records

Decisions D1 to D15 are recorded in `docs/DECISIONS/`. The older integration ADRs stay in `docs/adr/` with their own numbers.

| Decision | Record |
|---|---|
| D1 Launch shape and voice | [ADR-001](DECISIONS/ADR-001-launch-shape-and-voice.md) |
| D2 First users | [ADR-002](DECISIONS/ADR-002-first-users-and-order.md) |
| D3 Jurisdiction | [ADR-003](DECISIONS/ADR-003-first-jurisdiction.md) |
| D4 LLM vendor | [ADR-004](DECISIONS/ADR-004-llm-vendor.md) |
| D5 Models | [ADR-005](DECISIONS/ADR-005-models-and-routing.md) |
| D6 Answer reveal | [ADR-006](DECISIONS/ADR-006-answer-reveal-rule.md) |
| D7 Content approval | [ADR-007](DECISIONS/ADR-007-content-approval.md) |
| D8 Content next | [ADR-008](DECISIONS/ADR-008-content-next.md) |
| D9 Video speed | [ADR-009](DECISIONS/ADR-009-video-speed-target.md) |
| D10 Render box | [ADR-010](DECISIONS/ADR-010-render-box.md) |
| D11 Ship branch | [ADR-011](DECISIONS/ADR-011-ship-branch.md) |
| D12 Keys and the zip | [ADR-012](DECISIONS/ADR-012-keys-and-zip.md) |
| D13 Sign-in | [ADR-013](DECISIONS/ADR-013-sign-in.md) |
| D14 Guest scope | [ADR-014](DECISIONS/ADR-014-guest-scope-and-age-question.md) |
| D15 Pilot success | [ADR-015](DECISIONS/ADR-015-pilot-success-criteria.md) |
