# PLAN — Pedagogy-First AI Tutor (Bhutan + Northeast India)

Bilingual, syllabus-matched AI tutor for Class 9–10 maths (science later). A **deterministic orchestrator decides WHAT to do next; the LLM only decides HOW to phrase it.**

**Pilot:** Bhutan national syllabus (English + Nepali) and Assam SEBA (English + Assamese). Payers: parents and tuition centres.

This file is the working milestone list. After each milestone: run tests, tick checkboxes, summarise, and **stop for review**.

---

## Decisions

| Topic | Choice |
|---|---|
| First languages | Both in the data model. Seed placeholders for Nepali (`ne`) and Assamese (`as`). UI via `next-intl` (`en` / `ne` / `as`). |
| First chapter | Class 9 linear equations (placeholder until the curriculum lead maps Bhutan + SEBA chapters). |
| LLM | LiteLLM gateway; `LLM_PROVIDER`, `LLM_MODEL_FAST`, `LLM_MODEL_STRONG` via env. Must work with **no API key** (authored fallback). |
| Parent reports | Email now. WhatsApp Business API as a pluggable stub. |
| Auth | Email OTP now, behind `OtpSender` (phone/WhatsApp later). Students: PIN under parent. See role matrix in ARCHITECTURE.md §17.1. |
| Timezones | Per student. Bhutan default `Asia/Thimphu`. SEBA/Assam default `Asia/Kolkata`. Quiet hours **21:00–07:00 local**. |
| Orchestrator | Pure state machine. Hint 1–2 retry; hint 3 = reveal lead-in. `predict_response` and `continue` events. |
| BKT | **Exactly one update per item**, at first answer or first hint request. Later hinted-correct only increments `mastery.hinted_correct`. |
| Session clock | `active_ms = sum(min(latency_ms, 5 min))`. Soft 15 min / 12 items; hard 20 min; auto-end after **10 min idle**; sessions **resumable**. No heartbeats. |
| Verifier | Never `sympify` raw input. Allowlist parser, length cap, timeout, digit/sign normalisation. |
| Explain-back | If `ai_processing` + API key: formative LLM grade. Else store student text, show authored model explanation, **no grade**. Never changes mastery or FSRS. |
| Offline / sync | Packs = numeric/exact/accept-list only. TS BKT + `ts-fsrs`. Server **re-verifies every answer** from stored `response` and **ignores client `correct`**. Reject/flag illegal sequences. |
| Checkpoints | Forms A/B. Score never updates mastery/FSRS. Hard min **10** items/form (validator **warning below 15**). Trials: **15–20**. Comparison: `study_participants` + expiring single-form token after consent. |
| Consent scopes | `tutoring`, `teacher_share`, `research_pseudonymised`, `ai_processing`. Teachers only see `teacher_share`. |
| Content gate | Production: `status=approved` only. `ALLOW_DRAFT_CONTENT=true` for dev/demo. **Live chapter:** ≥5 approved practice and ≥2 approved diagnostic items **per skill**; forms A and B with ≥10 checkpoint items each. |
| Current chapter target | First overlay skill with `p_known < 0.95`. Item **tiers** from `p_known` (easy / medium / hard); authored difficulty is ordering only; least-recently-shown in the tier. |
| Translations | Missing locale fields fall back to English. Never show empty strings or unreviewed machine translations. |
| Line endings | `.gitattributes` forces LF. |
| Local run | Docker Desktop + WSL2; repo on the **WSL filesystem**, not `/mnt/c`. |
| Primary skill | Each item has a **primary skill** = first `skill_ids` entry. BKT updates that skill only. Validator requires `skill_ids` length ≥ 1. |
| FSRS timing | Warm-up item outcomes update that skill's card **immediately**. Other skills: **one** FSRS rating at **session end**, from that session's unhinted-correct rate on the skill. |
| Similar item | After reveal, `SIMILAR_ITEM` is a **different** approved practice item on the **same primary skill and tier**. Never the same item. |
| Consent revoke | If consent is revoked mid-session, the session **ends on the next event** and **no further LLM calls** are made. |

If something else is ambiguous and not blocking, pick the simplest option, add a row here, and continue.

---

## Open questions (non-blocking)

1. Exact Bhutan and SEBA chapter titles for linear equations — use placeholder overlay IDs until the curriculum lead maps them.
2. OTP delivery in local Docker — log the code in the API console when `SMTP` is unset (`EmailOtpSender`).
3. Eval-set size for M6 — start with ≥50 hand-authored turns covering leak, misconception, and language cases.

---

## Out of scope (keep the design open)

Flutter app, WhatsApp **chatbot** channel (OTP via WhatsApp later is an `OtpSender`), voice, photo-of-handwriting checking, Dzongkha, learned teaching policy (bandits), payments, boards beyond the two overlays, tuition-centre billing.

---

## Windows / local dev (copy into README at M0)

Developers on Windows **must** use Docker Desktop with the WSL2 backend.

1. Install Docker Desktop and enable WSL2.
2. Install Ubuntu (or similar) from the Microsoft Store; open that distro, not PowerShell, for day-to-day work.
3. Clone this repo **inside the WSL filesystem** (e.g. `~/src/YourTutor`), not under `/mnt/c/...`. Bind mounts from `/mnt/c` are slow and break file-watchers.
4. From that WSL path: `docker compose up --build`.
5. `.gitattributes` sets `* text=auto eol=lf` so checkout does not inject CRLF into YAML, Python, or Actions workflows.

---

## Guardrails (do not weaken)

Enforced in code + tests. Full list in [ARCHITECTURE.md](ARCHITECTURE.md) and `.cursor/rules/project.mdc`.

- Orchestrator owns pedagogy; LLM only phrases.
- Retry hints are levels **1–2** only and must not leak. Hint **3** is the `reveal_solution` lead-in, never a retry hint.
- Reveal only after the attempt **following hint 2** is also wrong, or `show_solution` after 2 hints.
- Exactly one BKT update per item (first answer or first hint request). Later hinted-correct increments `hinted_correct` only.
- Correctness from the allowlist verifier, never the LLM. Never `sympify` raw input.
- Explain-back grades are formative and do not change mastery or FSRS.
- Prerequisites first (mastery &lt; 0.6 of T). Warm-up only when FSRS cards are due (max 3).
- Session caps use **active time**; 10 min idle auto-ends; sessions are resumable.
- Checkpoint items never used in teaching or practice. Checkpoint scoring **never** updates mastery/FSRS. Diagnostic completion **does** seed mastery.
- Production serves only approved + live-chapter thresholds, unless `ALLOW_DRAFT_CONTENT=true`.
- Missing translations fall back to English.
- No PII to the LLM. Scoped parent consent. Quiet hours 21:00–07:00 local. No dark patterns.
- Do not machine-translate content and mark it approved.

---

## Milestone protocol

After each milestone:

1. Run the tests required for that milestone.
2. Update checkboxes in this file.
3. Summarise what changed (and any new Decisions).
4. **Stop for review.** Do not start the next milestone until told.

---

## M0 — Plan & scaffold

**Docs:** `PLAN.md`, `ARCHITECTURE.md`, `.cursor/rules/project.mdc`.

**Scaffold:**

- [x] Monorepo: `apps/api` (FastAPI), `apps/web` (Next.js App Router), `content/`, `packages/shared`
- [x] `docker-compose.yml`: Postgres 16 + pgvector, Redis, api, web
- [x] `.env.example` (includes `ALLOW_DRAFT_CONTENT=true` for local), `.gitattributes` (LF)
- [x] API + web health checks
- [x] GitHub Actions skeleton (ruff, mypy, eslint/tsc, pytest, vitest placeholders)
- [x] README: Docker Desktop + WSL2 instructions

**Accept:** `docker compose up` runs api + web + db + redis; CI skeleton green. **Met 2026-10-02:** compose stack healthy; `/health` and `/api/health` return ok; local ruff/mypy/pytest and tsc/vitest passed.

---

## M1 — Content pipeline

- [x] Pydantic v2 schemas for skills, items, misconceptions, overlays, glossary
- [x] CLI: `python -m app.content.validate content/` and `python -m app.content.load content/`
- [x] Validator: unique IDs, refs resolve, no prerequisite cycles, **primary skill** required, **3 hint levels** (1–2 leak-checked; 3 = reveal lead-in), solution steps, checkpoint items not in practice, allowlist-parseable answers
- [x] Validator: each item's **final solution step is equivalent to its stated answer**
- [x] **Live-chapter threshold:** every skill has ≥5 approved practice and ≥2 approved diagnostic items; forms A and B exist with ≥10 checkpoint items each (warn &lt; 15) and a complete `match_map`
- [x] Content gate: runtime serves `status=approved` only, unless `ALLOW_DRAFT_CONTENT=true`; non-live chapters not targetable in production
- [x] Locale fallback: missing `ne`/`as` → English
- [x] Seed: one Class 9 linear-equations chapter — ~12 skills, ~8 misconceptions, ~120 items (60 practice / 30 diagnostic / 30 checkpoint), English, `status: draft`. Nepali/Assamese reviewer placeholders. **Do not machine-translate or mark approved.**
- [x] Glossary stubs and overlays (`bhutan_class9.yaml`, `seba_class9.yaml`)

**Accept:** validator catches broken refs, cycles, missing hints, checkpoint leakage, solution/answer mismatch, leak in hint 1–2, and failed live-chapter counts; seed loads; drafts hidden unless the env flag is set. **Met 2026-10-02:** 23 pytest passed; seed validates (12 skills, 8 misconceptions, 120 items = 60/30/30, forms A/B 15 each); SQLite load succeeded; overlays warn not-live because every item is draft.

---

## M2 — Accounts & consent

- [ ] `users` (parent / teacher / admin), email OTP via `OtpSender`
- [ ] OTP **rate limits** (request + verify)
- [ ] `students` with PIN hash, board, languages, timezone, `current_chapter_id`
- [ ] PIN **lockout after 5 failed attempts**
- [ ] Consent `scopes`: `tutoring`, `teacher_share`, `research_pseudonymised`, `ai_processing`
- [ ] Parent **data export** and **delete**
- [ ] Classes + memberships; teacher queries filter `teacher_share`
- [ ] Role/authorization matrix enforced (ARCHITECTURE.md §17.1)
- [ ] No session without active `tutoring` consent

**Accept:** no session without `tutoring`; teachers cannot see students without `teacher_share`; PIN locks after 5 failures; OTP rate-limited; parent export/delete works.

---

## M3 — Learner model

- [ ] BKT (`bkt.py`) with skill-level `p_init`, `p_learn`, `p_slip`, `p_guess`
- [ ] **Exactly one BKT update per item**, at first `answer` or first `request_hint`
- [ ] Later hinted-correct increments `mastery.hinted_correct` only (no second BKT write)
- [ ] Mastered: `p_known ≥ 0.95` **and** ≥ 3 correct **unhinted** answers
- [ ] FSRS (`scheduler_fsrs.py`); explain-back and checkpoints do not update FSRS
- [ ] `mastery_service.py` interface; **recompute from event log** (used on sync)

**M3 acceptance tests (required):**

- [ ] First unhinted correct → one BKT correct update
- [ ] First wrong answer → one BKT incorrect update; later hinted-correct → `hinted_correct += 1`, `p_known` unchanged by that event
- [ ] First event is `request_hint` → one BKT incorrect update; later correct answer → `hinted_correct` only
- [ ] Two answers on the same item never apply two BKT updates
- [ ] Deterministic FSRS due dates; checkpoint/explain-back fixtures do not move `due_at`
- [ ] Warm-up outcomes update that skill's FSRS card immediately; other skills get one rating at session end from unhinted-correct rate

**Accept:** all tests above green.

---

## M4 — Orchestrator + verifier (no LLM)

- [ ] Pure policy: `(learner_state, session_state, last_event) → next_action`
- [ ] Events include `predict_response` and `continue`
- [ ] Verifier: allowlist parser (no raw `sympify`), normalisation, leak check on hints 1–2
- [ ] Hint 3 used only as `reveal_solution` lead-in
- [ ] Misconception match; unmatched → generic hint 1–2
- [ ] Active-time caps, 10 min idle auto-end, resume
- [ ] Shared fixtures + Python contract tests (TS in M7)

**M4 acceptance tests (required):**

- [ ] No reveal when delivering hint 1 or 2; leak check rejects leaking 1–2
- [ ] Hint 3 is never returned as a retry `hint` action
- [ ] Reveal only after the **attempt following hint 2** is also wrong, or `show_solution` after 2 hints; reveal text starts with hint 3
- [ ] After hint 1 or 2, next action is retry `PRACTICE`
- [ ] First `request_hint` or first `answer` triggers the single BKT update; later hinted-correct does not
- [ ] `EXPLAIN_BACK` once per skill after first unhinted correct or on mastery; `continue` skips; LLM grade (if any) does not change mastery
- [ ] Explain-back without `ai_processing` or API key: store student text, show authored model explanation, **no grade**
- [ ] `predict_response` advances PREDICT → WORKED_EXAMPLE; `continue` advances WORKED_EXAMPLE → PRACTICE
- [ ] `PREDICT` + `WORKED_EXAMPLE` only when the skill is new
- [ ] `WARMUP_REVIEW` skipped when no FSRS cards are due; when due, at most 3
- [ ] Prerequisite of T with mastery &lt; 0.6 scheduled before T; T defined as in §6.2
- [ ] Item **tiers**: `p_known < 0.4` easy, `0.4–0.8` medium, `> 0.8` hard; pick **least-recently-shown** eligible item in the tier; authored difficulty is ordering only
- [ ] `active_ms = sum(min(latency_ms, 5 min))` (no heartbeats); idle 10 min ends; resume restores last action
- [ ] Diagnostic and checkpoint: no hints, no reveal, no LLM
- [ ] Diagnostic completion seeds `p_known`; checkpoint score does **not** update mastery or FSRS
- [ ] Unmatched wrong answers use generic hint 1–2
- [ ] `idle_nudge` does not change pedagogy
- [ ] Checkpoint items never appear in practice selection
- [ ] Allowlist rejects malicious strings (`__import__`, overlong input, etc.); Devanagari/Bengali digits and `x = 5` normalise correctly
- [ ] Sync contract: server re-verifies answers from stored `response` and **ignores client `correct`**
- [ ] Sync contract: illegal sequences (reveal before the attempt after hint 2) are rejected or flagged
- [ ] `SIMILAR_ITEM` is a different approved practice item on the same primary skill and tier
- [ ] Consent revoked mid-session: next event ends the session; no further LLM calls

**Accept:** all tests above green with authored content only (no LLM).

---

## M5 — Diagnostic & checkpoint

- [ ] Placement diagnostic (10–15 min); on completion, seed mastery per skill
- [ ] `checkpoint_forms` A and B (matched `match_map`); hard min 10 items/form; **warning below 15**; trials target 15–20
- [ ] Scoring writes `checkpoint_results` only — **never** mastery/FSRS
- [ ] `study_participants` (`tutor` \| `comparison`) with `consent_ref`, `assigned_at`, `assignment_method` (record **random** assignment)
- [ ] Comparison tokens: single-form, expiring, no PII; **refuse issue** unless a parental consent row exists
- [ ] Comparison-group `GET /checkpoints/{id}/forms/{A|B}` (token + printable)
- [ ] `GET /analytics/export` CSV, pseudonymised, `research_pseudonymised` only

**Accept:** checkpoint items never in practice; diagnostic seeds mastery; checkpoint score does not; token cannot be issued without consent; comparison path works without a tutor session.

---

## M6 — LLM gateway

- [ ] LiteLLM gateway; versioned prompts; gated on `ai_processing`
- [ ] Fast model: hints / encouragement. Strong model: explain-back grading (**formative only**)
- [ ] No-key / no-`ai_processing`: store explain-back text, authored model explanation, **no grade**
- [ ] Post-checks; regenerate once; authored fallback
- [ ] `llm_calls` + review-queue sampling
- [ ] No-key / no-scope mode still completes a session
- [ ] `evals/cases/*.jsonl` + `run_evals.py`

**Accept:** leak rate 0% on eval set; fallback works with no API key; explain-back grade does not change mastery.

---

## M7 — Student PWA

- [ ] PIN login, Today, session player (`predict_response`, `continue`), done-for-today, **resume**
- [ ] Offline packs: numeric/exact/accept-list only; exclude checkpoint and symbolic-only items
- [ ] TS orchestrator + BKT + `ts-fsrs` + same fixtures as M4
- [ ] Sync: server recomputes mastery from the event log
- [ ] Playwright smoke; 360 px layout

**Accept:** smoke session works; offline + sync matches server recompute; contract tests match Python.

---

## M8 — Parent & teacher views

- [ ] Parent: sign-in, add student, **scoped** consent, weekly progress, language switch
- [ ] RQ weekly report (email + WhatsApp stub); quiet hours
- [ ] Teacher heatmap / stuck / review queue **filtered by `teacher_share`**

**Accept:** report from real events; teacher cannot see a student without `teacher_share`; teacher can approve/edit an AI message.

---

## M9 — Hardening

- [ ] PII stripping; moderation; distress script
- [ ] General API rate limits (OTP/PIN already in M2)
- [ ] Quiet hours tests (`Asia/Thimphu`, `Asia/Kolkata`)
- [ ] Seed demo data + pilot README
- [ ] Error handling

**Accept:** PII/moderation/quiet-hours tests green; a new operator can run the pilot from the README.

---

## Required tests (ongoing)

| Area | When |
|---|---|
| Orchestrator policy | M4+, every change |
| Verifier allowlist + leak + malicious input | M4+, every change |
| BKT one-update-per-item + FSRS | M3+, every change |
| LLM guardrails + eval suite | M6+; CI on `llm/prompts/` or `orchestrator/` |
| Consent scopes + teacher_share | M2+ |
| Checkpoint isolation + no mastery write | M5+ |
| Shared fixture contracts | M4 (Python), M7 (TypeScript) |
| Playwright smoke | M7+ |
| Content gate + live-chapter threshold | M1+ |
| PIN lockout + OTP rate limit | M2+ |
| Parent export / delete | M2+ |
| Solution-step ≡ answer | M1+ |

---

## Track B (non-code, parallel)

Not software milestones. Owners: curriculum lead + field coordinator. Engineering consumes the outputs as YAML updates (still `status: draft` until a teacher sets `approved`). Live-chapter thresholds still apply.

### B1 — Teacher review of seed content

- [ ] Human reviewer fills Nepali and Assamese placeholders (no machine-translate-and-approve)
- [ ] Teacher approves or edits each seed skill / item / misconception (`reviewed_by`, `status: approved`)
- [ ] Counts reach live-chapter thresholds; production overlay `live=true`

### B2 — Manual WhatsApp pilot (30–50 families)

- [ ] Recruit 30–50 families (Samtse and/or Guwahati); consent with scopes
- [ ] Teachers run a **manual** WhatsApp loop using the same pedagogy
- [ ] Log real wrong answers and teacher interventions
- [ ] Replace placeholder misconceptions and items; validate; do not mark approved without teacher review

Track B does **not** block M0–M4. Start after M1 so later evals use real error patterns.

---

## Later (not this MVP)

- [ ] Recalibrate authored item difficulty from empirical unhinted correct rates (post-pilot). Until then, difficulty is ordinal / tier membership only.

---

## Pilot metrics (log from M7; dashboards later)

- % mistakes followed by an intervention in the same response (target ≥ 90%)
- Unhinted correct rate
- Weekly active days
- Checkpoint score change (measurement only)
- Eval: leak rate (must be 0), misconception match accuracy, schema-valid rate, average words, fallback rate, cost per 100 turns
