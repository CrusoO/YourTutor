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
| Lesson path (R38) | Pure `lesson_path(prerequisite_levels, beat_kinds)` in `app/lessons/path.py`, shared fixture `packages/shared/fixtures/lesson_path/cases.json`. Ready (every prerequisite at ladder level 4+, or none) gets every authored beat; anyone else skips the explore and scene beats that come before the first worked example. The prerequisite levels are recorded on the session when the `predict` action is emitted, so a resumed session serves the same path. The served lesson names its `order`. |
| Faded example | A lesson beat `faded_example` (worked steps, then a typed last step), after a worked example. The server checks the answer with the verifier on a `faded_answer` event (payload `faded` = ordinal among the lesson's faded examples, `response`); it is formative, never writes BKT or FSRS, and the client flag is ignored. The reply carries `lesson_correct`. It is a beat, not a separate action type: actions stay `predict` and `worked_example` carrying the lesson. |
| Approved sources | `content/sources/*.yaml` lists approved source ids with a licence (`authored`, `open`, `permission_on_file`). `content validate` and `content load` refuse a lesson or scene `source_ref` that is not listed or whose licence is not approved. Items do not carry `source_ref` yet. |
| LLM gateway | `app/llm/`: pure prompt builder (constitution excerpt quoted verbatim from `docs/TUTOR_CONSTITUTION.md`, grade-band style and word limit, authored source, glossary, forbidden answer; student text wrapped as data), pure post-checks in order (schema, leak, grounding/citation, length, tone, moderation, language), then a gateway that regenerates once and falls back to the authored text. The model is behind a small provider interface (`LiteLLMProvider`, imported lazily, plus a fake for tests and evals). No call in diagnostic or checkpoint sessions, without `ai_processing`, or without `LLM_API_KEY`. Personalising happens once after the policy decides, is stored on the action, and never touches BKT or FSRS. Wired for ladder hints 1 and 2, the explain-back reply and encouragement; `adapt_explanation` has a prompt and checks but no session uses it yet; `answer_doubt` is a stub for G7. |
| LLM call log | `llm_calls` holds metadata only (purpose, prompt version, model, band, outcome, attempts, failure codes, latency, tokens). The reply text is kept only for calls sampled for review (`LLM_REVIEW_SAMPLE_RATE`, default 100% for the first pilot week), and the student's own words are never stored. Skipped calls are not logged. |
| LLM word lists | Tone and moderation word lists are in `config/llm_rules.yaml`; person-praise words reuse the encouragement-copy list. Moderation is a local whole-word list, not a provider moderation call. |
| `draft_content` | `python -m app.llm draft_content` writes `status: draft` items only, with reviewer placeholders in place of translations, after schema, solver, verifier and leak checks. It refuses when `APP_ENV=production` or without a key. |
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
| Ladder levels 1–4 | Levels 1–4 are earned independently; 5–7 chain (5 after 4, 6 after 5, 7 needs 6). Level = highest achieved. Diagnostic, checkpoint and explain-back never reach the ladder; only practice and warm-up events do. Events dated after `now` are ignored. |
| Level 1 evidence | Until lessons exist (G3): the PREDICT → WORKED_EXAMPLE flow completed for the skill **and** a correct answer (hints allowed) on the first practice item afterwards. One function, `lesson_level1_reached`, holds this rule; G3 swaps it for lesson completion. |
| Level 2 evidence | Only an unhinted-correct first attempt on an `explain` item. Explain-back grades stay formative and never count. |
| Level 4 evidence | `p_known ≥ 0.95` **and** 3 consecutive unhinted-correct first attempts spanning ≥ 2 distinct stem-structure signatures (M4.5 `structure_signature`). Only `procedure`, `apply` and `transfer` items count: `recall` / `explain` items neither extend nor break the streak. Hinted answers never count. |
| Levels 5–7 evidence | 5: unhinted-correct first attempt on an `apply` item after level 4. 6: same for `transfer` after level 5. 7: a warm-up review answered correctly (unhinted, first attempt) ≥ 7 days after the last practice on the skill, then another ≥ 21 days after the last practice; an incorrect or hinted review resets retention and drops 7 → 6. Injectable clocks in tests. |
| T and selection | T = first overlay skill with ladder level < 4 (replaces `p_known < 0.95`). Role-aware selection: level 4 → `apply`, level 5 → `transfer`, otherwise `procedure` with `recall` / `explain` mixed in (every 2nd and 4th item of the skill) until level 2; a missing role falls back to any eligible role and logs `content_gap` (`reason: role_missing`). Warm-ups use the same role by level; a similar item keeps the missed item's role. |
| Extension practice | T is by definition below level 4, so levels 5–6 would never be earned. With no skill below level 4 the policy serves `apply` (level 4) then `transfer` (level 5) items on the first such skill before `chapter_complete`; with no item of that role it logs the gap and completes the chapter. |
| Ladder storage | `mastery.ladder_level`, `ladder_evidence` (level → client event ids), `flags`, plus `ladder_memory` (incremental state; not in the original plan). Recompute from the event log uses practice-session events only, with the verified `correct` now stored on `events` and client event ids as evidence ids; `events.created_at` is the policy's own time. Diagnostic seeding of `p_known` is not an event, so it is outside the recompute. |
| FSRS session end | Other practised skills get one FSRS rating when a practice session ends (not on consent revoke), from the session's unhinted-correct rate; per-session counts use the DB session id and are cleared after rating. This was specified in M3 but not wired, so no card existed in the live flow. |
| Item roles in content | `role` is required on every item and template. Seed backfill: word problems `apply`, everything else `procedure`; 36 new draft items (one `explain`, `apply`, `transfer` per skill). Four reason-choice `explain` items need teacher sign-off (not machine-verifiable). The live threshold needs ≥ 1 approved item of each of those roles per skill. |
| Overlay curriculum | Overlay YAML uses `curriculum_id`; the schema rejects a leftover `board:` and the validator rejects unknown curricula. `overlays.board` was renamed (migration 0015). Student and class `board` stay until G5 / G6. |
| Vertical slice first | Build a visible vertical slice (S1) before G2, to get real feedback early. A human pilot check follows S1b, before G2. |
| UI preview data | Preview students come from `python -m app.dev seed_scenarios`, which replays events through the real engine (never writes mastery rows) with the clock set in the past. It uses its own database (`yourtutor_preview`) so normal dev data is untouched. |
| Dev tools gating | `/dev` web pages need `NEXT_PUBLIC_DEV_TOOLS=true`; API `/dev/*` routes are a 404 unless `DEV_TOOLS` **and** `ALLOW_DRAFT_CONTENT` are on. Only `app.dev.clock.frozen` may pin the clock, and it refuses unless `ALLOW_DRAFT_CONTENT=true`. LAN preview uses explicit `CORS_EXTRA_ORIGINS` / `NEXT_ALLOWED_DEV_ORIGINS` (wildcards refused). |
| Content load safety | `python -m app.content load` refuses a missing or empty content root: an empty bundle would retire (or, in dev, hard-delete) everything already loaded. |
| Help events | `request_help` is the canonical event, `request_hint` a deprecated alias (stored as `request_help`). Actions carry `can_request_help` and the deprecated `can_request_hint`; OpenAPI says so. New events `stuck_choice` (`payload.choice`) and `stuck_step` (`payload.index`). |
| Stuck-point picker | Offered once per item, only before any attempt or help on it; a repeat request goes to the hint ladder. The request is the item's one BKT update. Choices: start (hint 1), step (numbered steps, then that step's hint), restate (authored paraphrase), might be right (prompt to submit, or Check your work after a wrong answer). Step hints and the restated question use no ladder level; per-item flags reset when the item is finished. |
| Step picker shows numbers | ARCHITECTURE 9.2 says "show the item's authored step list"; showing the steps would reveal the solution before hint 3, so the picker shows Step 1..n and the tap returns that step's hint. |
| Slip and diagnosis | `classify` is pure and first-match (misconception, slip, prerequisite gap, incomplete procedure, disengagement, generic). A slip needs ladder level 4 or more, a first attempt, and an authored pattern (sign flip, off by up to N, listed values); it returns `check_your_work` without using a hint level, and the second wrong answer goes to the ladder. The result is stored as `payload.diagnosis`. Disengagement is classified from counters (fast answers, help without an attempt) but its response (`break_or_switch`) is P7. A misconception answer gets the authored misconception explanation as hint 1 (falls back to the item hint if it would leak). |
| Draft diagnosis fields | `scripts/write_g2_item_fields.py` and `app/content/diagnosis_fields.py` derive drafts from solution steps. Step hints contain no numbers. Items stay `draft`; the approval hash now includes step hints and the restated question. |
| Stretch slot | When the ladder reaches level 4 or 5 it records `stretch_after_<level>` one day later. A due skill gets an apply (level 4) or transfer (level 5) item before the next new skill, after the warm-up: at most 2 per session, once per skill per session, practice sessions only, and no content gap when no item of that role exists. |
| Resume until midnight | A session whose last activity was on an earlier local day is ended as `day_rollover` and is never resumed; progress lives in the student model. Seeded preview sessions are stamped as used a few minutes ago. |
| Help on hint screens | Help is offered on hint screens while fewer than two ladder hints have been shown, so a restated question or step hint can be followed by more help. The Hint button is now Help and is no longer delayed. |
| Chapter titles | `chapters.titles` (JSON, locale -> text) and `chapters.position` come from `curriculum.yaml` (migration 0016); titles use the locale fallback chain. A chapter is *live* when its overlay has skills and is `live: true`, or drafts are allowed. Anything else is `coming_soon` and `POST /sessions` with its `chapter_id` answers 409 `chapter_coming_soon`. The seed book has a placeholder `Quadratic equations` chapter with no overlay so the map always shows one Coming soon card. |
| Recommended chapter | The first live chapter that is not Solid (a review-due chapter counts as not Solid); when every live chapter is Solid, the first live one. Always exactly one, or none when nothing is live. |
| Starting a skill | The chapter page starts a normal practice session for the chapter (`chapter_id` in the plan). The existing policy already opens a new skill with its lesson and a known skill with practice, so no policy change was needed. |
| Skip ahead | Its own session type `test_out`, outside the policy: 2 hard practice items (one `apply` or `transfer`), no hints, answers verified by the server and logged, never BKT or FSRS events. A pass writes one `test_out_passed` event: ladder level 4 with `evidence=test_out`, and `p_known` is raised to at least 0.95 so the policy does not treat the skill as a weak prerequisite. A miss writes nothing and shows no penalty wording. `ladder_log` recompute reproduces it. |
| Done summary | `end_session` actions carry `extras.summary`: skills moved forward this session (levels at start are kept in the session plan), skills practised, every skill status, next skill, minutes left, chapter and the recommended chapter. No streaks, ranks or scores. |
| Resume | Reopening an idle-ended session (Resume on Today, or `GET /sessions/{id}`) reopens it with `reopen_idle`, shared with starting a session; a session that ended for another reason still shows the Done screen. Skip-ahead sessions are never offered as Resume. |
| Lessons as files | Lessons are validated YAML in `content/lessons/` (one per skill, checked by `app.content validate`); DB tables come with G3. Python Pydantic models are the schema source of truth, JSON Schemas are generated (drift test), the TS validator is hand-written and checked against shared fixtures. |
| Lesson events | A lesson is attached to the session's `predict` / `worked_example` actions. `interactive_result` and `scene_answer` events bypass the policy, are checked server-side, are stored in `events` with `payload._verdict`, and never touch BKT/FSRS. The check item is the first practice item after the lesson, so it writes BKT exactly once. |
| Widget trust | The server recomputes the goal predicate from `final_state`; a result that misses the goal or names another widget is rejected (`widget_goal_not_met`, `widget_id_mismatch`, `widget_result_malformed`). The client predicate is for instant feedback only. |
| Scene budget | Scenes are limited to 50 KB per minute, estimated from action bytes and durations (`app/lessons/budget.py`); the validator fails a lesson over budget. |
| Lesson copy | Player chrome strings (Continue, Checked by the server, ...) are English constants in `LessonPlayer.tsx` until S1b moves them into the locale registry. |


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

Order: generalise first (cheap now, expensive later), then the ladder (G1), then **S1, a visible vertical slice, before G2** so real people can react early; then the rest of the teaching core (G2–G3), the LLM and UI on top of it, grounding Ask, offline, and the adult views.

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

**Status:** **Met 2026-10-04.** API pytest **256 passed** on Postgres (`-p no:randomly`, and `pytest-randomly` seeds 1, 2, 3 all 256 passed); `ruff check` 0 errors, `ruff format --check` clean, `mypy` 0 errors (135 files); vitest 33 passed; `tsc` ok; region-literal check clean; locale generation no diff; content validates (12 skills, 370 items, 2 overlays) and loads; migration downgrade to `0008_retire` and upgrade to head tested with data. Playwright not run (no UI change).

**Carried out of G0** (unchecked items in the target milestones): overlay `board:` → G1; grade-band wiring → G2 (session caps), G4 (LLM style), G5 (UI); `board` compat field removal and client `device_timezone` → G5; `classes.board` → G6.

### G1 — Student model v2 (mastery ladder)

- [x] Item `role` field (recall, explain, procedure, apply, transfer); validator requires it (`56a9c65`)
- [x] Seed chapter: add ≥ 1 explain, ≥ 1 apply, ≥ 1 transfer item per skill (draft) (`d45b2fe`; 36 items)
- [x] `mastery.ladder_level`, `ladder_evidence`, `flags`; pure `ladder.compute(events)` in Python + fixture-shared spec (`92c50f6`, `a900920`)
- [x] Level 4 requires `p_known ≥ 0.95` + 3 consecutive unhinted correct first attempts across ≥ 2 structures (`92c50f6`)
- [x] Level 7 requires FSRS recalls at ≥ 7 and ≥ 21 days; incorrect recall drops 7 → 6 (`92c50f6`; reviews need FSRS cards, wired in `8ad3fdf`)
- [x] Student status mapping (Not started / Learning / Can do it / Solid / Review due) (`423f8bd`)
- [x] T = first overlay skill with ladder < 4 (`c0511ed`)
- [x] Live-chapter threshold adds role coverage (`5b8fac6`)
- [x] *Deferred from G0:* overlay YAML `board:` field replaced by `curriculum_id` (`dc57a95`)

Accept:

- [x] Ladder fixtures: each level reached only with its evidence; hinted correct never reaches 4; one-structure streak does not reach 4 (`packages/shared/fixtures/ladder/`, 14 fixtures)
- [x] Recompute from event log equals incremental result (hypothesis on random logs; `recompute_ladders` vs stored in `tests/player/test_ladder_persistence.py`)
- [x] Review-due status appears when FSRS card is overdue and clears on correct recall (`tests/player/test_review_due_flow.py`, `tests/learner/test_status.py`)
- [x] Existing BKT one-update-per-item tests unchanged and green (`tests/learner/test_bkt.py`, `test_fsrs.py`, `test_properties.py` untouched)

**Status:** **Met 2026-10-05.** API pytest **379 passed (379 collected)** on Postgres in one piece (`-p no:randomly`), and `pytest-randomly` seeds 1 and 2 each 379 passed (up from 256 at G0); `ruff check` 0 errors, `ruff format --check` clean, `mypy` 0 errors (154 files); vitest 33 passed; `tsc` ok; region-literal check clean; locale generation no diff; content validates (12 skills, **406** items, 2 overlays) and loads; Alembic head `0015_g1_overlay_curriculum`, round-trip downgrade to `0008_retire` and upgrade to head tested with data. Playwright not run (no UI change). Process notes: the full suite was killed twice for low memory mid-milestone (see the G2 memory item); four reason-choice `explain` seed items still need teacher sign-off.

### S1 — Vertical slice (runs before G2)

A phone-sized path through the seed chapter that people can open and judge: login → subject → chapter map → chapter page → lesson → practice → done. Preview tools (scenarios, `/dev`, screenshots) are in `docs/UI_PREVIEW.md`.

**S1a — playable lesson**

- [x] Met 2026-10-07. Schemas in `packages/shared/schemas/` for lesson (beats), scene script (`write_text`, `draw_shape`, `draw_arrow`, `highlight`, `pause_and_ask`) and widget params/state/goal; validated in Python and TS
- [x] Met 2026-10-07. Scene player (SVG, 360 px): progressive drawing, pause/replay, captions always on, `pause_and_ask` with feedback, reduced motion respected, no external libraries
- [x] Met 2026-10-07. Widgets `balance_scale` and `function_graph` with goal predicates in Python and TS (shared fixtures); the server re-checks the final state and rejects a forged result
- [x] Met 2026-10-07. Lesson runner for one skill: predict → explore (widget) → explain scene → worked example → check item; lesson beats never write BKT/FSRS, the check item does exactly once
- [x] Met 2026-10-07. Content: a draft lesson for the linear-equation skill ported from the approved prototype (`docs/prototypes/balancing-equations-lesson.html`) plus lessons for 3 more skills (draft, English, authored text; every scene has `skill_id` and `source_ref`)
- [x] Met 2026-10-07. `/dev/lessons` lists every lesson and opens each without login (dev only)
- [x] Met 2026-10-07. Playwright: the full lesson with a 360 px screenshot of each beat

Result: pytest 467 (one piece; seeds 1 and 2: 467 each), vitest 111, test:ui 8 specs (with the 6 scenario specs); 17 lesson screenshots in apps/web/test-results/screens/lesson-*.png.

Deferred from S1a (unchecked): lesson strings in the locale registry (S1b); lesson tables in the DB and lesson review workflow (G3); offline caching of scene scripts (offline milestone); `faded_example`, `number_line`, `area_model`, `fraction_bar` (not built).

Accept: lesson beats never write BKT/FSRS; the check item writes once; a forged widget result is rejected; schemas validate; screenshots show each beat.

**S1b — student flow end to end**

- [x] Met 2026-10-07. `GET /students/{id}/chapters`: id, title (locale + fallback), live, status (`not_started`, `learning`, `can_do_it`, `solid`, `review_due`), `recommended: true` on exactly one chapter; non-live chapters return `coming_soon` and cannot be started (server-enforced); no hard locks between live chapters
- [x] Met 2026-10-07. `GET /students/{id}/chapters/{chapter_id}/skills`: skill path with per-skill status; visual unlock when the previous skill reaches "Can do it"
- [x] Met 2026-10-07. Chapter map UI (status chips, one recommended chapter, "Coming soon" cards) and chapter page with the skill path and a logged "Skip ahead" test-out (2 unhinted-correct hard-tier items incl. one apply/transfer → level 4, `evidence=test_out`; failure returns without penalty copy)
- [x] Met 2026-10-07. Starting a skill: new skill → lesson then practice; known skill → practice. Done screen: what was learned, skill statuses, next recommendation, remaining active minutes; no streaks or ranks
- [x] Met 2026-10-07. Warm-up first when reviews are due, with plain-words copy (today a warm-up looks like any other question)
- [x] Met 2026-10-07. **Fix:** "Resume" on Today opens `/session/<id>` for an idle-ended session and shows "Done for now / idle / Back to Today"; Resume must reopen the session. Also replace the raw `practice` and `idle` labels with locale-registry copy
- [x] Met 2026-10-07. Playwright: login → map → chapter → lesson → practice (wrong → hint → retry) → done at 360 px; scenarios `new_student` and `mid_chapter` in the spec

Result: pytest 534 (one piece; seeds 1 and 2: 534 and 534), vitest 137, test:ui 10 specs; 17 flow screenshots in apps/web/test-results/screens/flow-*.png.

Deferred from S1b (unchecked): chapter and student-flow strings are English only until the locale review (G8); Today stays as a dev/utility page (minutes left, Resume, diagnostic and checkpoint buttons) and is no longer the first page after login; no first-run "quick warm-up" offer (G5); a chapter that is partly done shows the weakest skill status per ARCHITECTURE 11.3, which reads as "Not started" while the card says "4/12 skills you can do" (pilot check: decide whether to show "Learning" once any skill has started).

Accept: a student completes the path on a phone; a coming-soon chapter cannot be started via the API; exactly one recommended chapter; status-derivation tests for each state; lesson beats never write BKT/FSRS.

**Done so far (P3, setup):** `python -m app.dev seed_scenarios` (5 scenarios by replaying events through the real engine), `/dev` page with one-click log in as, dev-only `GET/POST /dev/*`, phone preview docs, `npm run test:ui` with 360 px screenshots.

### G2 — Diagnosis engine + policy v2

**G2a (P6, branch `g2a-diagnosis`) — Met 2026-10-08** for the items ticked below; G2b (R33–R40, P7) — Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs; random seeds 1 and 2: 757 and 757). pytest 660 (one piece; seeds 1 and 2: 660 and 660), vitest 153, test:ui 13 specs; whole suite in one process peaks at 354 MB (target 2 GB); 12 Playwright screenshots in `apps/web/test-results/screens/help-*.png` and the earlier flow, lesson and scenario screens. The S1 pilot check (B5) was still pending when P6 started (gate waived by the product owner).

Draft content note: the step hints, restated questions, slip patterns, intermediate values and `min_plausible_ms` on all 336 practice items are machine drafts (generic wording, English plus reviewer placeholders); a teacher must edit them before any item is approved. The restated question repeats the stem, which reads awkwardly.

- [x] Met 2026-10-08. **Test-suite memory check (start of G2):** measure peak memory per test directory; find and fix leaks (undisposed engines/sessions, large fixtures). Target: the full suite runs within 2 GB. *Finding: during G1 and P3 the suite was killed three times for low memory. Time is the other problem: the full suite takes 20 min to almost 2 hours. About 15 tests each validate or load the whole seed bundle at ~75 s apiece (e.g. `test_role_coverage`, `test_overlay_curriculum`, `test_loader_guard`, `test_sections`), and `test_templates::test_generation_is_deterministic` takes ~230 s and `test_simulations::test_scripted_students_on_seed` ~150 s. Share one validated bundle per session (fixture) and speed up validation.* *Measured 2026-10-08: no leak; max 354 MB for the whole suite, 208 MB for the heaviest directory*
- [x] Met 2026-10-08. `diagnosis.classify()` pure, with item fields `slip_patterns`, `prereq_signatures`, intermediate step values, `min_plausible_ms`
- [x] Met 2026-10-08. R30 diagnose before hint; R31 `check_your_work` for slips
- [x] Met 2026-10-08. R32 `request_help` → `ask_stuck_point`; choices route to hint 1, step hint, `hint_restate`, or recheck
- [x] Met 2026-10-08. Item fields `step_hints[]` and `hint_restate`; validator leak-checks step hints
- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). R33 prerequisite probe; R34 wheel-spinning stop + `teacher_alerts`
- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). R35 disengagement → `break_or_switch`; R36 frustration de-escalation; R37 challenge; R40 never end on failure
- [x] Skip-ahead test-out (§9.7 Arch) with `evidence=test_out` *(covered by S1b)*
- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). Praise trigger rules; encouragement only on triggers (authored copy)
- [x] Met 2026-10-08. `request_hint` kept as an alias of `request_help`
- [x] Met 2026-10-08. Transition table + Mermaid markers updated; drift test *R31 and R32 rows added; R33-R40 follow in P7*
- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). *Deferred from G0:* grade bands (`config/grade_bands.yaml`) drive session caps (soft/hard active-time caps per band, ARCH §20)
- [x] Met 2026-10-08. Session resume only until local midnight in the student's time zone; after that, start a new session (progress carries via the student model). Test with injected clocks. *Finding: `start_session` resumes any idle-ended session with no age limit (seen in G1 step 8).*

Accept:

- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). Scripted students (hypothesis): slip student gets `check_your_work` then ladder; misconception student gets targeted hints; prerequisite-gap student gets a probe within 3 failures; random guesser triggers `break_or_switch`; strong student hits `challenge` after 3 unhinted correct
- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). Wheel-spinning detected by item 10 on a skill in 100% of simulated non-learners; teacher alert row written only with `teacher_share`
- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). Help escalation is monotonic in every simulated session; no reveal before v1 conditions
- [x] Met 2026-10-09 (pytest 757, vitest 160, test:ui 15 specs). No session ends immediately after a reveal or wrong answer (R40) while staying within hard cap + 1 item
- [x] Met 2026-10-09 (leak checks in tests/content/test_diagnosis_fields.py, BKT once per item in tests/orchestrator/test_help_simulation.py). Stuck-point step hints pass leak checks; BKT still updated exactly once per item

### G3 — Lessons, scenes and widgets (backend + content)

- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Schemas in `packages/shared/schemas/`: lesson, scene script, widget params/state/goal *(covered by S1a)*
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Widget registry with Python + TS predicate mirrors: `balance_scale`, `function_graph` *(covered by S1a)*
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). `lessons`, `scenes`, `widgets` tables; loader + validator (schema, source refs, approved sources, size budget)
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). R38 lesson path (problem-first if prerequisites ≥ level 4, else worked-example-first); faded examples
- [ ] *Events done (plus `faded_answer`); actions kept as `predict` / `worked_example` carrying the lesson, see Decisions; not ticked until you confirm.* Events `predict_response`, `interactive_result`, `scene_answer`; actions `lesson_*`, `worked_example`, `faded_example`
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Server re-checks widget predicates; client result ignored *(covered by S1a)*
- [ ] *Lessons and scenes carry `source_ref` (checked against the approved sources); items do not yet.* Every item/scene/lesson carries `section_id` / `source_ref` (Layer A grounding)
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Seed: one draft lesson per skill in the seed chapter (≥ 4 using widgets) *(S1a covers 4 skills; the rest stays here)*
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Live-chapter threshold requires an approved lesson per skill

Accept:

- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Shared predicate fixtures pass in Python and TS
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). A forged `interactive_result` with an unsolved state is rejected/flagged
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Lesson beats never write BKT/FSRS; the check item does (once)
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Novice vs ready student get different lesson orders (fixtures)
- [x] Met 2026-10-10 (pytest 777; random seeds 1 and 2: 777 and 777; vitest 167; test:ui 15 specs). Scene scripts ≤ 50 KB/min; every text node traces to an approved source

### G4 — LLM gateway (was M6, extended)

- [ ] *Built and tested with a fake provider; the LiteLLM path is not exercised (library not installed, no key) and `adapt_explanation` is not used by a session yet.* LiteLLM gateway; purposes: `personalise_hint`, `adapt_explanation`, `grade_explain_back`, `encourage`, `draft_content` (authoring only); `answer_doubt` stubbed for G7
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). Prompt includes constitution excerpt + grade-band style profile + authored source + glossary + forbidden answer
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). Post-checks: schema → leak → grounding/citation → length (band word limit) → tone (no person-praise, no shaming) → moderation → language → regenerate once → authored fallback
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). `llm_calls` + review-queue sampling; gated on `ai_processing` and API key
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). Explain-back without key/scope: store text, show authored model explanation, no grade
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). `draft_content` CLI writes `status: draft` only; refuses to run in production
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). `evals/` suites: phrasing (leak, length, tone, language), explain-back rubric agreement
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). *Deferred from G0:* grade-band style profile (word limits, tone) wired into LLM prompts and post-checks

Accept:

- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). *Scripted replies only; a live run is what measures a model.* Leak rate 0% and tone violations 0% on the eval set
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). Word limits respected per band
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). No-key and no-scope sessions complete end to end
- [x] Met 2026-10-10 (offline; pytest 866, vitest 167). Explain-back grade never changes ladder, BKT or FSRS

### G5 — Student app v2 (absorbs M7a)

- [ ] Context picker: curriculum → grade → subject → (book/medium); curated optional school list with "Other"
- [ ] Guest start (`POST /guest/start`): random id, no PII; retention per profile
- [ ] First run: "Quick warm-up to find where to start" / "Start from the beginning"; no "test" wording, no marks; nothing automatic; warm-up re-offered after 2nd session with respected "not now"
- [ ] Subjects → Chapter map (`GET /students/{id}/chapters`): statuses, one recommended, Coming soon (server-enforced), no hard locks *(covered by S1b)*
- [ ] Chapter page: skill path with statuses, visual unlocks, Skip ahead *(covered by S1b)*
- [ ] Session player: warm-up, lesson beats (predict, explore widget, scene player with pause-and-ask, worked/faded examples), practice (math input + MCQ), feedback, stuck-point picker, hints, check-your-work, reveal, similar item, prerequisite probe, challenge, explain-back, break/switch, done *(lesson beats and warm-up copy: S1a/S1b; the rest stays here)*
- [ ] Scene player: SVG/JS, captions, optional audio, offline-cacheable *(covered by S1a; offline caching stays here)*
- [ ] Source chips on explanations
- [ ] Family/school login (family code + PIN) kept from M7a *(covered by S1b)*
- [ ] Grade-band styling (read-aloud default, choices), 360 px layout, large targets, low data *(360 px layout covered by S1; the rest stays here)*
- [ ] UI strings via locale registry with fallback *(covered by S1b for the slice)*
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
- [ ] **B5 S1 pilot check:** run the S1 vertical slice with the curriculum lead, one teacher and 2–3 students on a phone; log feedback as PLAN.md items before G2.
  - *2026-10-08: P6 started with this check still pending (gate waived by the product owner). Log the feedback as PLAN items when it happens; later prompts may need to adapt.*
- [ ] **B2 now:** teacher approval of `ITEM.LIN1.R.0001`, `0004`, `0007` and `0031` (reason-choice explain items the validator cannot machine-verify).

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

