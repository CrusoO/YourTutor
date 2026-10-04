# PLAN — Pedagogy-First AI Tutor (v2)

A curriculum-matched, multilingual AI tutor for school maths (science later). A deterministic orchestrator decides WHAT to do next, the selected textbook decides WHAT is true, and the LLM only decides HOW to phrase it.

v2 is region-neutral. The first curriculum, languages and pilot site are deployment choices made in config and content, not in code.

This file is the working milestone list. After each milestone: run tests, tick checkboxes, summarise, and stop for review.

---

## 1. Review of v1 and why v2 changes it

v1 (M0–M5.5) built a strong, verified practice engine. The review against learning-science evidence and the product goals found these gaps:


| #   | Gap in v1                                                    | Why it matters                                                                                                              | v2 change                                                    | Arch ref  |
| --- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | --------- |
| 1   | Country-specific enums (board, locales, time zones, hosting) | Every new market would need code changes                                                                                    | Curriculum, locale, grade-band and jurisdiction registries   | §6, §19   |
| 2   | Wrong answers go straight to a hint                          | Strong evidence: diagnose the cause before correcting; slips, misconceptions and prerequisite gaps need different responses | Diagnosis engine + R30–R33                                   | §10       |
| 3   | No "ask before telling" on help requests                     | Tutors who find where the student is stuck give smaller, better help                                                        | Stuck-point picker (deterministic)                           | §9.2      |
| 4   | No stop rule for repeated failure across items               | Wheel-spinning: after ~10 attempts, more practice barely helps the remaining third of students                              | R34 wheel-spinning stop + prerequisite probe + teacher alert | §8.1      |
| 5   | Mastery = `p_known ≥ 0.95` + 3 unhinted                      | Correct answers are not understanding; retention and transfer are untested                                                  | 7-level mastery ladder with item roles and delayed recall    | §11.2     |
| 6   | One teaching path for every new skill                        | Worked examples help novices; problem-first works when prerequisites are solid (expertise reversal)                         | R38 lesson path chooses order                                | §8.1, §16 |
| 7   | No challenge or skip-ahead                                   | Over-scaffolding capable students hurts engagement and learning                                                             | R37 challenge, §9.7 test-out                                 | §9        |
| 8   | No frustration or disengagement handling                     | Unresolved confusion → frustration → boredom                                                                                | R35, R36, R40                                                | §8.1      |
| 9   | Praise and tone not governed                                 | Person-praise and filler praise add little; process feedback helps                                                          | Feedback rules + tone post-checks                            | §9.3, §14 |
| 10  | Same copy and caps for every age                             | Language, autonomy and session length should vary by age                                                                    | Grade-band style profiles                                    | §15       |
| 11  | No textbook grounding or citations                           | Trust requires visible, correct sources                                                                                     | Grounding Layers A–D, passages with licences                 | §12       |
| 12  | No visual/interactive teaching                               | Interactive explore + explain beats engage and build understanding                                                          | Lessons, whiteboard scenes, widget registry                  | §16       |
| 13  | Registration required staff/guardian first                   | Self-serve students need a low-friction, data-minimal start                                                                 | Guest mode with upgrade to family/school                     | §18       |
| 14  | Research machinery in the core path                          | Adds complexity to every deployment                                                                                         | Optional research module behind a flag                       | §4        |
| 15  | Today screen is a list of buttons                            | Students think in chapters                                                                                                  | Chapter map + skill path with mastery-derived status         | §5        |


Kept unchanged because they are correct: pure policy, LLM-as-phrasing, allowlist verifier, hint 1–2 retry / hint 3 reveal lead-in, one BKT update per item, FSRS warm-up, active-time caps, content approval gates, offline contract fixtures, consent-gated LLM use, no PII to the model.

---

## 2. Decisions


| Topic            | Choice                                                                                                                                                                              |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Region           | No country, board, language or time zone in code. Registries in `config/` and `content/curricula/`.                                                                                 |
| First curriculum | One sample curriculum (`sample_board`) with the existing Class 9 linear-equations chapter, until the curriculum lead picks the launch curriculum.                                   |
| Languages        | Locale registry with fallback chains. Default locale `en`. Existing placeholder locales become ordinary registry entries.                                                           |
| Digits           | Unicode-generic normalisation (`unicodedata.decimal`), plus curriculum notation profile.                                                                                            |
| Account modes    | `guest` (no PII), `family` (guardian OTP), `school` (site code). Guest upgrades without data loss.                                                                                  |
| Legal rules      | Jurisdiction profile YAML; `default_strict` when unset. Legal review before enabling any profile.                                                                                   |
| Orchestrator     | Pure state machine. v1 rules R01–R22 kept; v2 rules R30–R40 added.                                                                                                                  |
| Diagnosis        | Pure `classify()`; classes: misconception, slip, prerequisite_gap, incomplete_procedure, disengagement, generic.                                                                    |
| Help             | Stuck-point picker before first hint; hint ladder 1–2 retry, 3 = reveal lead-in; similar item after reveal.                                                                         |
| Mastery          | 7-level ladder (§11.2 Arch). T uses level 4. Statuses: Not started, Learning, Can do it, Solid, Review due.                                                                         |
| Item roles       | recall, explain, procedure, apply, transfer. Live skills need ≥ 1 explain, apply, transfer.                                                                                         |
| BKT              | Exactly one update per item, at first answer or first help request. Lesson beats never update BKT.                                                                                  |
| FSRS             | Warm-up updates immediately; others one rating at session end.                                                                                                                      |
| Thresholds       | Starting values: 3 consecutive wrong first attempts or 10 items without level 4 → wheel-spinning; 3 fast answers → disengagement; 3 unhinted correct → challenge. Tune after pilot. |
| Lessons          | One per skill: predict, (explore), explain scene, worked example, faded example, check.                                                                                             |
| Scenes           | JSON scene scripts rendered client-side; ≤ 50 KB/min excluding audio; captions always on.                                                                                           |
| Widgets          | Registry with TS + Python predicate mirrors; first two: `balance_scale`, `function_graph`.                                                                                          |
| Grounding        | Layer A (structured lookup) everywhere; Ask (Layers B–D) behind `ASK_ENABLED`, `ai_processing`, profile. No web fallback.                                                           |
| Content sources  | Authored notes by default. Textbook text only with written permission; loader refuses unknown licences.                                                                             |
| LLM              | LiteLLM gateway; fast model for hints/encouragement; strong model for explain-back and grounded answers. Works with no key.                                                         |
| Content drafting | LLM `draft_content` is an authoring tool only; output is draft until validator + teacher approval.                                                                                  |
| Grade bands      | A (1–5), B (6–8), C (9–10), D (11–12): word limits, caps, default first move.                                                                                                       |
| Research         | `RESEARCH_MODULE=off` by default. Checkpoints, participants, tokens, analytics export live there.                                                                                   |
| Diagnostic       | Offered on first run ("quick warm-up"), never forced, never blocks practice.                                                                                                        |
| Session clock    | `active_ms = Σ min(latency_ms, 5 min)`; caps from grade band; 10 min idle auto-end; resumable.                                                                                      |
| Translations     | Fallback along chain; never empty strings or unreviewed machine translation marked approved.                                                                                        |
| Local run        | Docker Desktop + WSL2; repo on WSL filesystem; LF line endings.                                                                                                                     |
| Parent reports | Email now. WhatsApp Business API as a pluggable stub. |
| Auth | Email OTP now, behind `OtpSender` (phone/WhatsApp later). Students: PIN under parent. See role matrix in ARCHITECTURE.md §17.1. |
| Verifier | Never `sympify` raw input. Allowlist parser, length cap, timeout, digit/sign normalisation. |
| Explain-back | If `ai_processing` + API key: formative LLM grade. Else store student text, show authored model explanation, **no grade**. Never changes mastery or FSRS. |
| Offline / sync | Packs = numeric/exact/accept-list only. TS BKT + `ts-fsrs`. Server **re-verifies every answer** from stored `response` and **ignores client `correct`**. Reject/flag illegal sequences. |
| Checkpoints | Forms A/B. Score never updates mastery/FSRS. Hard min **10** items/form (validator **warning below 15**). Trials: **15–20**. Comparison: `study_participants` + expiring single-form token after consent. |
| Consent scopes | `tutoring`, `teacher_share`, `research_pseudonymised`, `ai_processing`. Teachers only see `teacher_share`. |
| Content gate | Production: `status=approved` only. `ALLOW_DRAFT_CONTENT=true` for dev/demo. **Live chapter:** ≥5 approved practice and ≥2 approved diagnostic items **per skill**; forms A and B with ≥10 checkpoint items each. |
| Line endings | `.gitattributes` forces LF. |
| Primary skill | Each item has a **primary skill** = first `skill_ids` entry. BKT updates that skill only. Validator requires `skill_ids` length ≥ 1. |
| Similar item | After reveal, `SIMILAR_ITEM` is a **different** approved practice item on the **same primary skill and tier**. Never the same item. |
| Consent revoke | If consent is revoked mid-session, the session **ends on the next event** and **no further LLM calls** are made. |
| Removed content | Removed content is retired, not deleted; hard prune is dev-only or guarded. |
| Hint API naming (`request_help`) | Defer to **G2**; keep `request_hint` / `can_request_hint` until alias pass. |
| Quiet hours | **G0:** read start/end from jurisdiction profile (`default_strict` = 21:00–07:00); behaviour unchanged. |
| Web i18n | **G0:** keep `lib/messages.ts`; locale list + fallbacks from `config/locales.yaml` → generated JSON. No `next-intl`. |
| Research routes | **G0:** `RESEARCH_MODULE` off → study/checkpoint/analytics (and admin paper entry) return **404**. |
| Context picker UI | **G5**; **G0** data migration sets each student’s `context_key` so implicit chapter still works. |
| Curricula seed | **G0:** one registry entry per legacy board under `content/curricula/`; `sample_board` stays generic; no merge into sample. |
| FSRS timing | Warm-up item outcomes update that skill's card **immediately**. Other skills: **one** FSRS rating at **session end**, from that session's unhinted-correct rate on the skill. |
| Time zone | Student override → curriculum `default_timezone` → device (client-sent; see G5) → UTC. Quiet hours start/end come from the jurisdiction profile (`default_strict` = 21:00–07:00). |
| v1 current-chapter target | v1: first overlay skill with `p_known < 0.95`, item tiers from `p_known`. Kept until G1 switches T to ladder level < 4. |
| `board` deprecation | G0 keeps `students.board` / `classes.board` and the read-only `board` field in API responses. Overlay YAML `board:` → `curriculum_id` in **G1**; `classes.board` → `curriculum_id` in **G6**; client `device_timezone` in **G5**. |
| Test isolation | Tests that mutate the global `settings` are undone by an autouse snapshot/restore fixture in `tests/conftest.py`; `pytest-randomly` is a dev dependency and the suite must pass in random order. |
| Jurisdiction profile | `JURISDICTION_PROFILE` (default `default_strict`) selects the deployment's profile; it is the one quiet hours read. An unknown id, or a curriculum naming an unknown profile, stops API startup. The per-curriculum `jurisdiction_profile` field stays as data and is validated, but no longer drives behaviour. Containers set `CONFIG_DIR=/config` and `CONTENT_DIR=/content` (mounted in compose). |
| Sections | Section id = `{chapter_id}.{key}`; `overlays.section_map` is keyed by the local `key` (an overlay can serve several chapters). Validator fails on unresolved keys/skills. Seed sections are draft placeholders; the content loader also syncs registry rows from YAML. |
| Alembic target | `migrations/env.py` honours `cfg.attributes["database_url"]` (else app settings) and keeps existing loggers alive (`disable_existing_loggers=False`). |
| Lint and types | `ruff` line length **100** (already set in `apps/api/pyproject.toml`), `ruff format` for wrapping, long strings split with implicit concatenation; `types-PyYAML` in `requirements-dev.txt`; mypy fixed without `# type: ignore` where possible. Lint/type cleanups must not change behaviour (AST-checked). |


If something else is ambiguous and not blocking, pick the simplest option, add a row here, and continue.

---

## 3. Open questions (non-blocking unless marked)

- **Blocking before public launch:** legal review of guest mode, guardian consent and free-text input for the chosen jurisdiction.
- Which curriculum and book edition launch first; which section → skill map the curriculum lead signs off.
- Written permission to index textbook text, or authored notes only.
- Native-speaker reviewers per medium locale; TTS quality per locale (recorded audio may be needed).
- Diagnosis thresholds (fast-answer ms per item type, wheel-spinning counts) — tune from pilot logs.
- Eval-set sizes: start with ≥ 50 LLM phrasing turns, ≥ 100 grounding questions (incl. 30 out-of-scope, 20 injection), ≥ 30 per locale.

---

## 4. Out of scope (keep the design open)

Notes/notebook photo explanations, voice, native mobile app, chat channels, learned teaching policy, payments, subjects beyond maths, curricula beyond the first, open-ended chat.

---

## 5. Guardrails (do not weaken)

Enforced in code + tests. Full list in [ARCHITECTURE.md](http://ARCHITECTURE.md) and `.cursor/rules/project.mdc`.

- Orchestrator owns pedagogy; LLM only phrases; diagnosis is deterministic.
- Every wrong answer is classified before a response is chosen.
- Help escalates one level at a time; retry hints 1–2 and step hints never leak; hint 3 is only the reveal lead-in.
- Reveal only after the retry following hint 2 is wrong, or `show_solution` after 2 hints; then a different similar item.
- Exactly one BKT update per item. Lesson beats, explain-back grades and checkpoint scores never update BKT/FSRS.
- Correctness from the verifier (incl. widget predicates re-checked on the server), never the LLM or client.
- Mastery ladder levels require their evidence; "Solid" requires delayed recall.
- Wheel-spinning stops drilling; never end a session on a failure.
- Study Mode statements cite approved passages or say "not in your book"; no web fallback.
- Unknown-licence content is never indexed.
- Production serves approved, live content only, unless `ALLOW_DRAFT_CONTENT=true`.
- No PII to the LLM; consent and profile gate AI features; no dark patterns, ranks or streak threats.
- No country/board/language constants in code.

---

## 6. Milestone protocol

After each milestone:

1. Run the tests required for that milestone.
2. Update checkboxes in this file.
3. Summarise what changed (and any new Decisions).
4. Stop for review. Do not start the next milestone until told.

---

## 7. Completed (v1)


| Milestone                                  | Status                                                                |
| ------------------------------------------ | --------------------------------------------------------------------- |
| M0 Plan & scaffold                         | Met 2026-10-02                                                        |
| M1 Content pipeline                        | Met 2026-10-02                                                        |
| M2 Accounts & consent                      | Met 2026-10-02                                                        |
| M3 Learner model (BKT + FSRS)              | Met 2026-10-02                                                        |
| M4 Orchestrator + verifier (no LLM)        | Met 2026-10-02                                                        |
| M4.5 Content / policy / observability pass | Met 2026-10-02                                                        |
| M5 Diagnostic & checkpoint                 | Met 2026-10-02 (checkpoint parts move into the research module in G0) |
| M5.5 Content templates                     | Met 2026-10-02                                                        |
| M6 LLM gateway                             | Not started → becomes G4                                              |
| M7a Online student player                  | In progress → completed parts are kept; remaining scope folds into G5 |
| M7b Offline + sync                         | Not started → becomes G9                                              |
| M8 Parent & teacher views                  | Not started → becomes G10                                             |
| M9 Hardening                               | Not started → becomes G11                                             |

### v1 Met notes (from the v1 plan)

**M0 — Plan & scaffold**

**Accept:** `docker compose up` runs api + web + db + redis; CI skeleton green. **Met 2026-10-02:** compose stack healthy; `/health` and `/api/health` return ok; local ruff/mypy/pytest and tsc/vitest passed.

**M1 — Content pipeline**

**Accept:** validator catches broken refs, cycles, missing hints, checkpoint leakage, solution/answer mismatch, leak in hint 1–2, and failed live-chapter counts; seed loads; drafts hidden unless the env flag is set. **Met 2026-10-02:** 23 pytest passed; seed validates (12 skills, 8 misconceptions, 120 items = 60/30/30, forms A/B 15 each); SQLite load succeeded; overlays warn not-live because every item is draft.

**M2 — Accounts & consent**

**Accept:** no session without `tutoring`; teachers cannot see students without `teacher_share`; PIN locks after 5 failures; OTP rate-limited; parent export/delete works. **Met 2026-10-02:** 106 pytest passed on docker-compose Postgres (105 + loader on SQLite; postgres loader included when `TEST_DATABASE_URL` is set). Alembic `0001_m2` applies on Postgres (`scopes text[]`). OTP logs to console when SMTP is unset. Mid-session consent revoke ends the session with `ended_reason=consent_revoked` and `llm_called=false`.

**M3 — Learner model**

**Accept:** all tests above green. **Met 2026-10-02.**

**M4 — Orchestrator + verifier (no LLM)**

**Accept:** all tests above green with authored content only (no LLM). **Met 2026-10-02:** seed 126 items (60/36/30), 0 needs_teacher_check, validator + loader + 162 pytest green on Postgres; pure `policy()` + allowlist verifier; sync_guardrails fixtures cover ignore-client-correct, illegal reveal, hint-3-not-retry, SIMILAR_ITEM.

**M4.5 — Content / policy / observability / review quality pass**

**Accept:** Postgres validate/load/tests green. **Met 2026-10-02:** seed 126 items (60/36/30), 0 hint-leak errors, ≥3 practice structures and all three tiers per skill, 174 pytest green on Postgres (`yourtutor_test`); `content_gap` + nearest-tier fallback; hypothesis scripted students; review CLI hash reset; transition Mermaid drift test. **Note for M5:** placement diagnostic should use about one item per skill (12 items), with a second item only on borderline results.

**M5 — Diagnostic & checkpoint**

**Accept:** checkpoint items never in practice; diagnostic seeds mastery; checkpoint score does not; token cannot be issued without consent; comparison path works without a tutor session. **Met 2026-10-02:** one-per-skill placement, second item only if first wrong and prereq correct; fail-twice skips dependents (low prior); I-don't-know is incorrect with p_guess=0; cap 15 min / 16 items; `checkpoint_results` only; within-site random tutor A/B counterbalance; comparison token requires consent; analytics CSV is research-scoped and PII-free.

**M5 fixes (2026-10-02):**

**M5.5 — Content templates**

**Accept:** generated practice passes the validator; approval inheritance resets on edit. **Met 2026-10-02.**

G0 (2026-10-04) is tracked under §8. Post-G0 verification: API pytest **232 passed** on Postgres in default and randomized order (seeds 1–3); vitest 33 passed; `tsc` ok.

---

## 8. v2 milestones

Order: generalise first (cheap now, expensive later), then the teaching core (G1–G3), then the LLM and UI on top of it, then grounding Ask, offline, and the adult views.

### G0 — Region-neutral registries

- [x] `config/locales.yaml` + `locales` table: code, name, script, fallback chain, status (Alembic 0012; seeded from the YAML, re-synced by the content loader)
- [x] `config/grade_bands.yaml` (A–D) + loader, tested. *Wiring it into behaviour is carried to G2 (session caps), G4 (LLM style) and G5 (UI) below.*
- [x] `config/jurisdictions/default_strict.yaml` + loader; `JURISDICTION_PROFILE` env (default `default_strict`; unknown id stops startup)
- [x] `content/curricula/` + tables `curricula`, `books`, `chapters`, `sections` (Alembic 0009, 0011); overlays gain `section_map`; seed chapters have placeholder sections; validator checks `section_map` references
- [x] Migrate `students.board` enum → `curriculum_id` + `book_id`; locale columns → text FKs; `timezone` free IANA string (Alembic 0010; `board` column kept as read-only compat)
- [x] Remove all country/board/language enums and constants from code (CI guard clean; legacy-board curricula stay separate from `sample_board` by Decision). The remaining read-only `board` compat is carried to G1, G5 and G6 below.
- [x] Verifier: Unicode-generic digit normaliser + curriculum notation profile
- [x] `RESEARCH_MODULE` flag; checkpoint/participant/token/analytics routes only mounted when on (no research jobs exist yet)
- [x] Context key object (§6 Arch) used by session start and content lookup (LLM calls: no gateway until G4)

Accept:

- [x] grep-based CI check: no hard-coded curriculum, locale or time-zone literals outside `config/`, `content/`, tests
- [x] Migration up/down on Postgres with data present (`tests/migrations/test_roundtrip.py`: downgrade to `0008_retire`, upgrade to head); all existing tests green after migration
- [x] Digits from at least 4 different Unicode scripts normalise; decimal-comma profile parses `2,5`
- [x] Research routes return 404 when the flag is off; existing M5 tests pass with the flag on
- [x] Locale fallback walks the chain; empty/placeholder strings count as missing

**Status:** all G0 items done; final verification counts are recorded in the next commit.

**Carried out of G0** (unchecked items in the target milestones): overlay `board:` → G1; grade-band wiring → G2 (session caps), G4 (LLM style), G5 (UI); `board` compat field removal and client `device_timezone` → G5; `classes.board` → G6.

### G1 — Student model v2 (mastery ladder)

- [ ] Item `role` field (recall, explain, procedure, apply, transfer); validator requires it
- [ ] Seed chapter: add ≥ 1 explain, ≥ 1 apply, ≥ 1 transfer item per skill (draft)
- [ ] `mastery.ladder_level`, `ladder_evidence`, `flags`; pure `ladder.compute(events)` in Python + fixture-shared spec
- [ ] Level 4 requires `p_known ≥ 0.95` + 3 consecutive unhinted correct first attempts across ≥ 2 structures
- [ ] Level 7 requires FSRS recalls at ≥ 7 and ≥ 21 days; incorrect recall drops 7 → 6
- [ ] Student status mapping (Not started / Learning / Can do it / Solid / Review due)
- [ ] T = first overlay skill with ladder < 4
- [ ] Live-chapter threshold adds role coverage
- [ ] *Deferred from G0:* overlay YAML `board:` field replaced by `curriculum_id`

Accept:

- [ ] Ladder fixtures: each level reached only with its evidence; hinted correct never reaches 4; one-structure streak does not reach 4
- [ ] Recompute from event log equals incremental result
- [ ] Review-due status appears when FSRS card is overdue and clears on correct recall
- [ ] Existing BKT one-update-per-item tests unchanged and green

### G2 — Diagnosis engine + policy v2

- [ ] `diagnosis.classify()` pure, with item fields `slip_patterns`, `prereq_signatures`, intermediate step values, `min_plausible_ms`
- [ ] R30 diagnose before hint; R31 `check_your_work` for slips
- [ ] R32 `request_help` → `ask_stuck_point`; choices route to hint 1, step hint, `hint_restate`, or recheck
- [ ] Item fields `step_hints[]` and `hint_restate`; validator leak-checks step hints
- [ ] R33 prerequisite probe; R34 wheel-spinning stop + `teacher_alerts`
- [ ] R35 disengagement → `break_or_switch`; R36 frustration de-escalation; R37 challenge; R40 never end on failure
- [ ] Skip-ahead test-out (§9.7 Arch) with `evidence=test_out`
- [ ] Praise trigger rules; encouragement only on triggers (authored copy)
- [ ] `request_hint` kept as an alias of `request_help`
- [ ] Transition table + Mermaid markers updated; drift test
- [ ] *Deferred from G0:* grade bands (`config/grade_bands.yaml`) drive session caps (soft/hard active-time caps per band, ARCH §20)

Accept:

- [ ] Scripted students (hypothesis): slip student gets `check_your_work` then ladder; misconception student gets targeted hints; prerequisite-gap student gets a probe within 3 failures; random guesser triggers `break_or_switch`; strong student hits `challenge` after 3 unhinted correct
- [ ] Wheel-spinning detected by item 10 on a skill in 100% of simulated non-learners; teacher alert row written only with `teacher_share`
- [ ] Help escalation is monotonic in every simulated session; no reveal before v1 conditions
- [ ] No session ends immediately after a reveal or wrong answer (R40) while staying within hard cap + 1 item
- [ ] Stuck-point step hints pass leak checks; BKT still updated exactly once per item

### G3 — Lessons, scenes and widgets (backend + content)

- [ ] Schemas in `packages/shared/schemas/`: lesson, scene script, widget params/state/goal
- [ ] Widget registry with Python + TS predicate mirrors: `balance_scale`, `function_graph`
- [ ] `lessons`, `scenes`, `widgets` tables; loader + validator (schema, source refs, approved sources, size budget)
- [ ] R38 lesson path (problem-first if prerequisites ≥ level 4, else worked-example-first); faded examples
- [ ] Events `predict_response`, `interactive_result`, `scene_answer`; actions `lesson_*`, `worked_example`, `faded_example`
- [ ] Server re-checks widget predicates; client result ignored
- [ ] Every item/scene/lesson carries `section_id` / `source_ref` (Layer A grounding)
- [ ] Seed: one draft lesson per skill in the seed chapter (≥ 4 using widgets)
- [ ] Live-chapter threshold requires an approved lesson per skill

Accept:

- [ ] Shared predicate fixtures pass in Python and TS
- [ ] A forged `interactive_result` with an unsolved state is rejected/flagged
- [ ] Lesson beats never write BKT/FSRS; the check item does (once)
- [ ] Novice vs ready student get different lesson orders (fixtures)
- [ ] Scene scripts ≤ 50 KB/min; every text node traces to an approved source

### G4 — LLM gateway (was M6, extended)

- [ ] LiteLLM gateway; purposes: `personalise_hint`, `adapt_explanation`, `grade_explain_back`, `encourage`, `draft_content` (authoring only); `answer_doubt` stubbed for G7
- [ ] Prompt includes constitution excerpt + grade-band style profile + authored source + glossary + forbidden answer
- [ ] Post-checks: schema → leak → grounding/citation → length (band word limit) → tone (no person-praise, no shaming) → moderation → language → regenerate once → authored fallback
- [ ] `llm_calls` + review-queue sampling; gated on `ai_processing` and API key
- [ ] Explain-back without key/scope: store text, show authored model explanation, no grade
- [ ] `draft_content` CLI writes `status: draft` only; refuses to run in production
- [ ] `evals/` suites: phrasing (leak, length, tone, language), explain-back rubric agreement
- [ ] *Deferred from G0:* grade-band style profile (word limits, tone) wired into LLM prompts and post-checks

Accept:

- [ ] Leak rate 0% and tone violations 0% on the eval set
- [ ] Word limits respected per band
- [ ] No-key and no-scope sessions complete end to end
- [ ] Explain-back grade never changes ladder, BKT or FSRS

### G5 — Student app v2 (absorbs M7a)

- [ ] Context picker: curriculum → grade → subject → (book/medium); curated optional school list with "Other"
- [ ] Guest start (`POST /guest/start`): random id, no PII; retention per profile
- [ ] First run: "Quick warm-up to find where to start" / "Start from the beginning"; no "test" wording, no marks; nothing automatic; warm-up re-offered after 2nd session with respected "not now"
- [ ] Subjects → Chapter map (`GET /students/{id}/chapters`): statuses, one recommended, Coming soon (server-enforced), no hard locks
- [ ] Chapter page: skill path with statuses, visual unlocks, Skip ahead
- [ ] Session player: warm-up, lesson beats (predict, explore widget, scene player with pause-and-ask, worked/faded examples), practice (math input + MCQ), feedback, stuck-point picker, hints, check-your-work, reveal, similar item, prerequisite probe, challenge, explain-back, break/switch, done
- [ ] Scene player: SVG/JS, captions, optional audio, offline-cacheable
- [ ] Source chips on explanations
- [ ] Family/school login (family code + PIN) kept from M7a
- [ ] Grade-band styling (read-aloud default, choices), 360 px layout, large targets, low data
- [ ] UI strings via locale registry with fallback
- [ ] *Deferred from G0:* client sends `device_timezone`; resolution order student → curriculum default → device → UTC already in the API
- [ ] *Deferred from G0:* grade bands drive UI styling (read-aloud default, choices, target sizes)
- [ ] *Deferred from G0:* remove the read-only `board` compat field from student API responses once clients use `curriculum_id` / `context_key`

Accept:

- [ ] Playwright: guest onboarding → chapter map → lesson (widget + scene) → practice (wrong → check-your-work or stuck picker → hint → retry → reveal → similar) → done
- [ ] First login creates no session; skip leads to practice on T; warm-up offer after 2nd session and "not now" remembered
- [ ] Coming-soon chapter cannot be started via API
- [ ] Lighthouse mobile: page weight budget met on a lesson screen

### G6 — Accounts and consent v2

- [ ] Guest → family upgrade (`POST /guest/{id}/upgrade`) links records after guardian consent
- [ ] Consent scopes availability from jurisdiction profile (`tutoring`, `teacher_share`, `ai_processing`, `free_text`, `research_pseudonymised`)
- [ ] School mode via staff-assigned `site_id`; no school/surname/phone/address fields on students
- [ ] Guest retention job (delete after profile inactivity window); export/delete for family
- [ ] Role matrix updated for guest
- [ ] *Deferred from G0:* `classes.board` replaced by `curriculum_id`

Accept:

- [ ] Upgrade preserves all events and ladder state
- [ ] Guest records purge after the configured window (time-travel test)
- [ ] Features requiring a scope are refused without it, per profile fixtures
- [ ] Existing M2 tests green

### G7 — Study Mode Ask (grounding Layers B–D)

- [ ] `passages` table + loader with licence rule; embeddings (pgvector) for approved passages only
- [ ] Ask flow: input safety → current-item guard (routes to stuck picker) → Layer A → scoped hybrid search → gate (answer / clarify / out_of_scope) → `answer_doubt` with citations → Layer D verify → source chip
- [ ] `content_gaps` logging (question hash unless `free_text` consent)
- [ ] Meaning-preservation check against passages; fallback to passage text
- [ ] Feature flag `ASK_ENABLED`; guest default off
- [ ] Grounding eval suite

Accept:

- [ ] Unsupported-claim rate < 1%; correct abstention ≥ 95% on out-of-scope set; citation accuracy ≥ 98%
- [ ] Current-item guard: 100% of "solve this item" questions routed to the hint ladder
- [ ] Injection set: 0 rule changes or scope escapes
- [ ] Unknown-licence passage cannot be loaded

### G8 — Content scale-up tooling

- [ ] Authoring UI/CLI: section passages → `draft_content` → validator → teacher review queue → approve
- [ ] Template coverage for roles (apply/transfer templates)
- [ ] Review export/import with hashes (from M4.5) extended to lessons and scenes
- [ ] Locale review workflow: reviewer fills per-locale strings; machine drafts never auto-approved

Accept:

- [ ] A chapter can go from passages to live using only the tooling + teacher approvals
- [ ] Editing any approved object resets approval via hash

### G9 — Offline + sync (was M7b, extended)

- [ ] Packs: offline-verifiable items, lessons, scenes, widgets for a chapter
- [ ] TS mirrors: policy (incl. R30–R40), diagnosis, ladder, BKT, ts-fsrs, widget predicates — same fixtures
- [ ] Sync: server re-verifies, ignores client correctness and widget results, recomputes ladder/BKT/FSRS, rejects/flags illegal sequences

Accept:

- [ ] All shared fixtures pass in Python and TS
- [ ] Offline session synced = server recompute, byte-for-byte on ladder and BKT state

### G10 — Guardian and teacher views (was M8, extended)

- [ ] Guardian: progress by chapter status and ladder, what was learned this week, language switch, export/delete
- [ ] Weekly report job (channels from profile); quiet hours from profile
- [ ] Teacher: heatmap by ladder level, stuck-now, wheel-spinning and repeated-misconception alerts, review queue — consented students only

Accept:

- [ ] Reports from real events; no rankings or comparisons
- [ ] Teacher cannot see a student without `teacher_share`
- [ ] Alerts resolve when the skill reaches level 4

### G11 — Hardening (was M9, extended)

- [ ] PII stripping, moderation, distress script with pause and flag
- [ ] API rate limits; OTP/PIN limits kept
- [ ] Jurisdiction profile tests (strict default, retention, quiet hours in multiple IANA zones)
- [ ] Error handling, demo seed, operator README

Accept:

- [ ] PII/moderation/profile tests green; a new operator can run a pilot from the README

### G12 — Pilot readiness

- [ ] Launch curriculum chapter approved and live (Track B)
- [ ] All eval gates met (Arch §26) incl. native-reviewer sign-off for the medium locale
- [ ] Pilot protocol written: metrics, duration, consent, optional research module comparison design, pre-registered primary outcome
- [ ] Dashboards for pilot metrics

Accept:

- [ ] Go/no-go review signed by curriculum lead, engineering, and legal

---

## 9. Required tests (ongoing)


| Area                                                                         | From                                       |
| ---------------------------------------------------------------------------- | ------------------------------------------ |
| Orchestrator policy incl. R30–R40 + transition drift                         | G2, every change                           |
| Diagnosis classification fixtures                                            | G2                                         |
| Mastery ladder + recompute                                                   | G1                                         |
| Verifier allowlist, leak (incl. step hints), malicious input, Unicode digits | G0                                         |
| Widget predicates (Python = TS)                                              | G3                                         |
| BKT one-update-per-item + FSRS                                               | ongoing                                    |
| LLM guardrails + eval suites                                                 | G4; CI on `llm/prompts/` or policy changes |
| Grounding evals                                                              | G7                                         |
| Consent scopes + profiles + teacher_share                                    | G6                                         |
| Research isolation (checkpoint never in practice; no mastery write)          | when module on                             |
| Shared fixture contracts                                                     | G1–G3 (Python), G9 (TS)                    |
| Playwright smoke                                                             | G5                                         |
| Content gate + live-chapter threshold                                        | ongoing                                    |
| No region literals in code                                                   | G0                                         |


---

## 10. Track B (non-code, parallel)

Owners: curriculum lead + field coordinator. Engineering only lands outputs as validated YAML (status draft until a teacher approves).

- **B1 Curriculum mapping:** choose the launch curriculum and book edition; map sections → skills; obtain textbook permission or commission authored notes.
- **B2 Content review:** teachers approve skills, items (with roles), misconceptions, lessons and scenes; native reviewers fill medium-locale strings.
- **B3 Field loop:** 30–50 families or one school class run a manual version of the pedagogy; log real wrong answers and stuck points; replace placeholder misconceptions, slip patterns and stuck-point copy.
- **B4 Legal:** jurisdiction profile review; consent copy; retention.

Track B does not block G0–G3. Start B1 and B3 now so G2 thresholds and misconceptions use real data.

---

## 11. Pilot metrics

- % mistakes followed by an intervention in the same response (target ≥ 90%)
- Diagnosis mix per skill (slip / misconception / gap) and intervention success rate per class
- Unhinted-correct rate; ladder progression (time to level 4); level 7 reach (retention)
- Wheel-spinning rate and resolution rate after probe
- Weekly active days; session completion; lesson completion
- Ask: answered / clarified / out-of-scope rates; content gaps per chapter
- Eval: leak rate (0), unsupported-claim rate, tone violations, fallback rate, cost per 100 turns
- Checkpoint change (research module only, measurement only)

---

## 12. Later (not this MVP)

- Recalibrate item difficulty and diagnosis thresholds from pilot data
- Notes/notebook photo explanations (through the Ask flow; images deleted after extraction)
- Learned policy and learned mastery behind existing interfaces
- Additional curricula, subjects and widget types via registries

