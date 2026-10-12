# BUILD_PROMPTS.md — ordered prompts for the whole build

Put this file at `docs/BUILD_PROMPTS.md`. It is the single ordered list of work for Claude Code.
PLAN.md holds the milestone checklists and Accept tests; this file holds the exact instructions
and the order. If the two disagree, stop and report.

## How to use

Paste this driver prompt into Claude Code to run the next prompt in the list:

```text
Read CLAUDE.md, then docs/BUILD_PROMPTS.md. Find the first prompt whose status is
TODO (skip DONE). Check that its prerequisites are DONE and that the repo is clean
and on main. If the prompt conflicts with the current code or PLAN.md, stop and
report the conflict instead of guessing. Otherwise execute that prompt exactly,
following "Rules for every prompt". When finished, change its status to DONE with
the date and final test counts, commit that change, report (ending with the
"How to see it" block), and STOP. Do not start the next prompt.
```

After every report: review it (ideally in the planning chat), then run the driver again.
Never run two prompts in one go; each ends with a human review.

## Rules for every prompt

- Work on a branch named in the prompt; merge to main (--no-ff) only when everything is green.
- Show your step plan first. Tests first. Commit per step. Full suite green at every commit.
- Run the full suite in one piece plus random seeds 1–2 before reporting done; if memory runs
  out, stop and say so; never skip.
- Never weaken a guardrail in PLAN.md §5. Pure functions stay pure. Shared fixtures for anything
  the offline player mirrors.
- New content is status: draft. Never machine-translate and mark approved.
- No region literals outside config/, content/, migrations/, tests/.
- Anything student-visible: run `python -m app.dev seed_scenarios` + `npm run test:ui`, view the
  screenshots, and list what changed on screen.
- Every report ends with **"How to see it"**: URL, which /dev scenario or login, exact clicks,
  what I should see, screenshot paths. If nothing is visible, say so explicitly.
- Record new decisions as PLAN.md Decisions rows; record deferred work as unchecked PLAN.md items.

## Status overview

| # | Prompt | Branch | Status |
| --- | --- | --- | --- |
| P0 | Housekeeping (docs, constitution, retire-on-load, test isolation, lint) | various | DONE |
| P1 | G0 region-neutral registries (+ close-out) | g0-… | DONE |
| P2 | G1 mastery ladder | g1-mastery-ladder | DONE (2026-10-05) |
| P3 | Setup: merge G1, UI preview tools, plan reorder | ui-preview-setup | DONE (2026-10-06; pytest 409 passed (one piece, `-p no:randomly`; random seeds 1 and 2: 409 passed each), vitest 42, test:ui 6 specs / 11 screenshots) |
| P4 | S1a playable lesson | s1a-lesson-player | DONE (2026-10-07; pytest 467 (one piece; seeds 1 and 2: 467 each), vitest 111, test:ui 8 specs / lesson screenshots per beat) |
| P5 | S1b student flow end to end | s1b-student-flow | DONE (2026-10-07; pytest 534 (one piece; seeds 1 and 2: 534 and 534), vitest 137, test:ui 10 specs) |
| P6 | G2a diagnosis + stuck picker | g2a-diagnosis | DONE (2026-10-08; pytest 660 (one piece; seeds 1 and 2: 660 and 660), vitest 153, test:ui 13 specs; suite peak 354 MB) |
| P7 | G2b policy rules R33–R40 | g2b-policy | DONE (merged 2026-10-11, tag g2b-done) |
| P8 | G3 remainder: all lessons, lesson path, server checks | g3-lessons | DONE (merged 2026-10-11, tag g3-done) |
| P9 | G4 LLM gateway | g4-llm-gateway | DONE (merged 2026-10-11, tag g4-done; never run against a real model) |
| P10 | G5 remainder: guest, context picker, first run | g5-student-app | DONE (merged 2026-10-11, tag g5-done) |
| P11 | G6 accounts and consent v2 | g6-accounts | DONE (merged 2026-10-11, tag g6-done) |
| P12 | G7 Study Mode Ask | g7-ask | DONE (merged 2026-10-11, tag g7-done; ASK_ENABLED off by default) |
| P13 | G8 content scale-up tooling | g8-authoring | DONE (merged 2026-10-11, tag g8-done) |
| P14 | G9 offline + sync | g9-offline | DONE (merged 2026-10-11, tag g9-done) |
| P15 | G10 guardian and teacher views | g10-views | DONE (merged 2026-10-11, tag g10-done) |
| P16 | G11 hardening | g11-hardening | DONE (merged 2026-10-11, tag g11-done) |
| P17 | G12 pilot readiness | g12-pilot | PARTLY (engineering parts built on g11-hardening; the launch chapter, reviewer sign-off and go/no-go are human work) |
| H1 | harden-1: server-side consent scopes, safe maths parser, production startup guard, CI | harden-1 | DONE (merged 2026-10-12, tag harden-1-done) |
| R1 | ui-responsive: shell widths at 768, 1024, 1280 | ui-responsive | DONE (merged 2026-10-12, tag ui-responsive-done) |
| UI-1 | Chat-first front door, role homes, design system | ui-1-chat-shell | IN PROGRESS |

Human checkpoints (not prompts): after P5, run the S1 pilot check (curriculum lead + one teacher
+ 2–3 students on a phone); log feedback as PLAN.md items before P6. Teacher approval of content
(Track B) runs in parallel.

---

## P3 — Setup: merge G1, UI preview tools, plan reorder  [DONE 2026-10-06]

Prerequisites: P2 DONE.

```text
Setup task. Read CLAUDE.md first.

1. Merge branch g1-mastery-ladder into main (--no-ff) if not already merged.
   Tell me the remote status: is there a git remote? If not, say so and skip
   that part; I'll create a private GitHub repo.
2. New branch ui-preview-setup. Do all of these:
   a. `python -m app.dev seed_scenarios` (refuses unless ALLOW_DRAFT_CONTENT=true):
      students with printed login cards for new_student, mid_chapter,
      skill_at_level_4, review_due, all_skills_level_4. Built by replaying events
      through the real engine, never by writing mastery rows. Prints family code
      + PIN per scenario.
   b. Dev-only web page /dev listing every scenario with a one-click "log in as"
      button, plus a link to /dev/lessons (empty for now; S1a fills it).
   c. Make the web dev server reachable from a phone on the same Wi-Fi (bind
      0.0.0.0). Write docs/UI_PREVIEW.md: exact commands to start the stack,
      how to open http://localhost:3000/dev on the PC, how to find the PC's LAN
      IP and open it on a phone, and the Windows firewall step if needed.
   d. Playwright: one spec per scenario with 360 px screenshots saved to
      apps/web/test-results/screens/, plus npm script test:ui.
3. Add to CLAUDE.md the standing rule: every milestone report ends with a "How
   to see it" block (URL, scenario/login, clicks, expected result, screenshot
   paths; say so if nothing is visible).
4. PLAN.md: add milestone "S1 — Vertical slice" (S1a lesson player + /dev/lessons;
   S1b student flow login → subject → chapter map → chapter page → lesson →
   practice → done, seed chapter only, 360 px). Order: S1 runs BEFORE G2a. Mark
   which G3/G5 items S1 covers ("covered by S1"). Track B: "S1 pilot check with
   curriculum lead + one teacher + 2–3 students"; "teacher approval of
   ITEM.LIN1.R.0001, 0004, 0007, 0031". Decision row: "Build a visible vertical
   slice before G2, to get real feedback early."
5. Add to PLAN.md under G2a: "Test-suite memory check (target: full suite in
   2 GB)" and "Session resume only until local midnight in the student's time
   zone" if not already there.
6. Run all checks from CLAUDE.md plus test:ui. Commit per step; merge to main
   when green.
```

Before P4: save the approved lesson prototype HTML (the "Balancing equations" artifact from the
planning chat) as `docs/prototypes/balancing-equations-lesson.html`.

---

## P4 — S1a: playable lesson  [DONE 2026-10-07]

Prerequisites: P3 DONE; prototype file in docs/prototypes/.

```text
Implement S1a from PLAN.md on branch s1a-lesson-player. Read CLAUDE.md,
ARCHITECTURE §16, and docs/prototypes/balancing-equations-lesson.html (the
approved look and behaviour reference). Show your step plan first.

1. Schemas in packages/shared/schemas/: lesson (beats), scene script
   (write_text, draw_shape, draw_arrow, highlight, pause_and_ask), widget
   params/state/goal. Validate in Python and TS.
2. Scene player component (SVG, 360 px): progressive drawing, pause/replay,
   captions always on, pause_and_ask with feedback on wrong choices,
   reduced-motion respected, no external libraries.
3. Widgets balance_scale and function_graph with goal predicates in Python and
   TS (shared fixtures). Port from the prototype. The server re-checks the final
   state; a forged result is rejected.
4. Lesson runner for one skill: predict → explore (widget) → explain scene →
   worked example → check item. Lesson beats never write BKT/FSRS; the check
   item does, exactly once.
5. Content: one draft lesson for the seed chapter's linear-equation skill
   ported from the prototype, plus lessons for 3 more skills (draft, English,
   authored text only; every scene has skill_id and source_ref).
6. /dev/lessons lists all lessons; each opens directly with no login (dev only).
7. Playwright: play the full lesson with screenshots of each beat at 360 px.

Accept: lesson beats never write BKT/FSRS; check item writes once; forged widget
result rejected; schemas validate; screenshots show each beat.
```

---

## P5 — S1b: student flow end to end  [DONE 2026-10-07]

Prerequisites: P4 DONE.

```text
Implement S1b from PLAN.md on branch s1b-student-flow. Read CLAUDE.md and
ARCHITECTURE §5, §11.3. Show your step plan first.

Flow (seed chapter only, 360 px, strings via the locale registry):
login (existing family code + PIN) → Subjects (Maths only) → Chapter map →
Chapter page (skill path) → lesson (S1a runner) → practice (existing hint
ladder) → Done screen with skill statuses.

1. GET /students/{id}/chapters: chapters for the student's context key with
   id, title (locale + fallback), live, status from mastery (not_started,
   learning, can_do_it, solid, review_due), and recommended:true on exactly one
   chapter (first not Solid). Non-live chapters return coming_soon and cannot be
   started (server-enforced). No hard locks between live chapters.
2. GET /students/{id}/chapters/{chapter_id}/skills: skill path with per-skill
   status; visual unlock when the previous skill reaches "Can do it".
3. Chapter map UI with status chips, one recommended chapter, "Coming soon"
   cards. Chapter page with the skill path and a logged "Skip ahead" action
   that starts a test-out (2 unhinted correct hard-tier items incl. one
   apply/transfer → level 4, evidence=test_out; failure returns without
   penalty copy).
4. Starting a skill: new skill → lesson, then practice; known skill → practice.
   Done screen: what was learned this session, skill statuses, next
   recommendation, remaining active minutes; no streaks or ranks.
5. Warm-up appears first when reviews are due (G1 behaviour) with plain-words copy.
6. Playwright: login → map → chapter → lesson → practice (wrong → hint → retry)
   → done, with 360 px screenshots; add the scenarios new_student and
   mid_chapter to the spec.

Accept: a student completes the path on a phone; coming-soon cannot be started
via API; exactly one recommended chapter; status derivation tests for each
state; lesson beats never write BKT/FSRS.
```

Human checkpoint after P5: the S1 pilot check. Log feedback in PLAN.md before P6.

---

## P6 — G2a: diagnosis + stuck-point picker  [DONE 2026-10-08]

Prerequisites: P5 DONE and S1 feedback logged.

```text
Implement G2a on branch g2a-diagnosis. Read CLAUDE.md, PLAN.md (G2),
ARCHITECTURE §8.1, §9.2, §10, and docs/TUTOR_CONSTITUTION.md rules 5–7.
Show your step plan first.

1. Test-suite memory check: measure peak memory per test directory, fix leaks,
   target the full suite within 2 GB.
2. Session resume only until local midnight in the student's time zone
   (injected clocks in tests).
3. Pure diagnosis.classify() per ARCHITECTURE §10 with item fields
   slip_patterns, prereq_signatures, intermediate step values, min_plausible_ms.
   Classes: misconception, slip, prerequisite_gap, incomplete_procedure,
   disengagement, generic. Store on events.payload.diagnosis. Shared fixtures.
4. R30 diagnose before any hint. R31 slip → check_your_work (no hint level
   used); a second wrong answer goes to the normal ladder.
5. R32 stuck-point picker: request_help before an answer → ask_stuck_point;
   choices route to hint 1, a step hint, hint_restate, or recheck. Add
   step_hints[] and hint_restate to the item schema; generate drafts for seed
   and template items from solution steps; the validator leak-checks step
   hints. Counts as the item's one BKT update.
6. Accept request_help with request_hint as an alias; actions carry both
   can_request_help and can_request_hint (old one deprecated in OpenAPI).
7. Player UI: stuck picker and check_your_work screens (360 px, locale
   registry). Add the slip_prone scenario to seed_scenarios + a Playwright spec.
8. Stretch slot: after a skill reaches level 4, schedule one apply item
   (transfer after level 5) in a later session, spaced like reviews; max 2 per
   session.

Accept: PLAN.md G2 Accept items for slips, misconceptions and stuck points;
help escalation monotonic in hypothesis simulations; BKT exactly one update per
item; no reveal before v1 conditions; step hints pass leak checks; memory target
met; UI check with screenshots.
```

---

## P7 — G2b: policy rules R33–R40  [TODO]

Prerequisites: P6 DONE.

```text
Implement G2b on branch g2b-policy. Read CLAUDE.md, PLAN.md (G2),
ARCHITECTURE §8, §9, and docs/TUTOR_CONSTITUTION.md rules 9, 11, 13, 19–20.
Show your step plan first.

1. R33 prerequisite probe (diagnosis prerequisite_gap or wheel_spinning flag):
   one item on the lowest-mastery prerequisite; wrong → schedule it next and
   return to T later; right → change representation for T.
2. R34 wheel-spinning stop (3 consecutive wrong first attempts, or 10 items
   without level 4) → flag, probe, teacher_alerts row (only with teacher_share).
3. R35 disengagement → break_or_switch; R36 frustration de-escalation (tier down
   for 2 items after 2 reveals or 3 wrong in a row); R37 challenge (3 unhinted
   correct → tier up; at hard → transfer/interleaved item); R40 never end on a
   failure (one likely-success item before end, hard cap + 1 item max).
4. Praise rules: encouragement only on trigger (hard success, recovery after
   failure, session end); authored copy; never person-praise, never after easy.
5. Grade-band session caps and word limits from config/grade_bands.yaml wired
   into policy and copy selection.
6. Update the transition table with rule ids R30–R40; regenerate the Mermaid
   markers; drift test must pass.
7. Player UI: break_or_switch, challenge and probe screens. Add wheel_spinning
   to seed_scenarios + Playwright spec.

Accept: PLAN.md G2 Accept items (scripted students: slip, misconception,
prerequisite-gap, guesser → break_or_switch, strong student → challenge;
wheel-spinning caught by item 10 in 100% of simulated non-learners; teacher
alert only with teacher_share; no session ends right after a failure within caps).
```

---

## P8 — G3 remainder: lessons everywhere, lesson path, server checks  [TODO]

Prerequisites: P7 DONE.

```text
Complete G3 on branch g3-lessons, covering what S1a did not. Read CLAUDE.md,
PLAN.md (G3), ARCHITECTURE §16. Show your step plan first.

1. R38 lesson path: problem-first (predict → explore → explain scene → worked
   example) when every prerequisite is at ladder ≥ 4; otherwise
   worked-example-first. Faded examples (last 1–2 steps left to the student,
   verifier-checked). Replace the temporary level-1 evidence from G1 with
   lesson completion + check item, behind the same single function.
2. Draft lessons for every skill in the seed chapter; at least 4 use widgets.
   Every item, scene and lesson carries section_id / source_ref.
3. Server re-checks all widget predicates; forged results rejected/flagged.
4. Live-chapter threshold requires an approved lesson per skill; scene scripts
   validated for size (≤ 50 KB/min excluding audio) and source traceability.
5. Add widget types number_line and area_model if a seed skill needs them;
   otherwise record as deferred.
6. Playwright: novice vs ready-student scenarios show different lesson orders;
   screenshots of each lesson type.

Accept: PLAN.md G3 Accept items; shared predicate fixtures pass in Python and TS;
lesson beats never write BKT/FSRS; novice vs ready orders differ in fixtures.
```

---

## P9 — G4: LLM gateway  [TODO]

Prerequisites: P8 DONE.

```text
Implement G4 on branch g4-llm. Read CLAUDE.md, PLAN.md (G4), ARCHITECTURE §14, §15
and docs/TUTOR_CONSTITUTION.md. Show your step plan first.

1. LiteLLM gateway; purposes personalise_hint, adapt_explanation,
   grade_explain_back, encourage, draft_content (authoring only); answer_doubt
   stubbed for G7. Versioned prompts. Works with no API key.
2. Prompts include the constitution excerpt, grade-band style profile (word
   limits from config), authored source, glossary, forbidden answer.
3. Post-checks: schema → leak → grounding/citation → length → tone (no
   person-praise, no shaming) → moderation → language → regenerate once →
   authored fallback. llm_calls (no PII) + review-queue sampling. Gated on
   ai_processing and API key.
4. Explain-back without key/scope: store text, show authored model explanation,
   no grade. Explain-back grade never changes ladder, BKT or FSRS.
5. draft_content CLI writes status: draft only and refuses in production.
6. evals/ suites: phrasing (leak, length, tone, language) and explain-back.
7. UI: AI-phrased text vs authored fallback must look identical; add a dev
   toggle to force fallback; show where AI text appears in the "How to see it".

Accept: leak rate 0% and tone violations 0% on the eval set; word limits per
band; no-key and no-scope sessions complete end to end.
```

---

## P10 — G5 remainder: guest, context picker, first run  [TODO]

Prerequisites: P9 DONE.

```text
Complete G5 on branch g5-student-app. Read CLAUDE.md, PLAN.md (G5),
ARCHITECTURE §5, §6, §18. Show your step plan first.

1. Context picker: curriculum → grade → subject → (book/medium); optional curated
   school list with "Other / not listed"; no free text. GET /curricula routes.
2. Guest start: POST /guest/start creates a random-id learner with a context
   key, no PII; retention per jurisdiction profile (stored; purge job in G6).
3. First run: two clear choices "Quick warm-up to find where to start" / "Start
   from the beginning"; wording never says "test"; no marks; nothing starts
   automatically. Skipping starts practice at the first skill of the current
   chapter with default priors. Warm-up re-offered after the 2nd completed
   session; "not now" respected and recorded; never block practice.
4. Grade-band styling (read-aloud default for band A, choices per band), source
   chips on explanations, device_timezone from the client, remove the board
   compat field.
5. Playwright: guest onboarding → map → lesson → practice → done; first login
   creates no session; skip → practice on T; warm-up offer after 2nd session.

Accept: PLAN.md G5 Accept items; coming-soon chapter cannot start via API;
Lighthouse mobile weight budget met on a lesson screen.
```

---

## P11 — G6: accounts and consent v2  [TODO]

Prerequisites: P10 DONE.

```text
Implement G6 on branch g6-accounts. Read CLAUDE.md, PLAN.md (G6),
ARCHITECTURE §18, §19. Show your step plan first.

1. Guest → family upgrade (POST /guest/{id}/upgrade) links records after
   guardian consent; nothing lost.
2. Consent scopes availability from the jurisdiction profile (tutoring,
   teacher_share, ai_processing, free_text, research_pseudonymised).
3. School mode via staff-assigned site_id; no school/surname/phone/address
   fields on students; migrate classes.board → curriculum_id.
4. Guest retention purge job (profile inactivity window); family export/delete.
5. Role matrix updated for guest.
6. UI: upgrade prompt for guests (never blocks practice), consent screens in
   plain words (en + registry fallback).

Accept: upgrade preserves events and ladder state; guest records purge after the
window (time-travel test); scoped features refused without scope per profile
fixtures; M2 tests still green.
```

---

## P12 — G7: Study Mode Ask  [TODO]

Prerequisites: P11 DONE and legal review of free-text input (PLAN.md open question) answered.

```text
Implement G7 on branch g7-ask. Read CLAUDE.md, PLAN.md (G7), ARCHITECTURE §12.
Show your step plan first.

1. passages table + loader with the licence rule (unknown licence refused);
   embeddings (pgvector) for approved passages only.
2. Ask flow: input safety → current-item guard (routes to stuck picker) → Layer A
   → scoped hybrid search → gate (answer / clarify / out_of_scope) →
   answer_doubt with citations → Layer D verify → source chip.
3. content_gaps logging (question hash unless free_text consent).
4. Meaning-preservation check; fallback to the passage text.
5. ASK_ENABLED flag; guest default off; grounding eval suite.
6. UI: an "Ask" box on the chapter page with source chips and the out-of-scope
   message.

Accept: unsupported-claim rate < 1%; correct abstention ≥ 95%; citation accuracy
≥ 98%; 100% of "solve this item" questions routed to the hint ladder; injection
set causes 0 rule changes; unknown-licence passage cannot load.
```

---

## P13 — G8: content scale-up tooling  [TODO]

Prerequisites: P12 DONE.

```text
Implement G8 on branch g8-authoring. Read CLAUDE.md, PLAN.md (G8). Show your step
plan first.

1. Authoring CLI/UI: section passages → draft_content → validator → teacher
   review queue → approve.
2. Template coverage for apply and transfer roles.
3. Review export/import with hashes extended to lessons and scenes.
4. Locale review workflow: reviewers fill per-locale strings; machine drafts
   never auto-approved.
5. UI: a simple teacher review screen (approve/edit/reject) with a preview of
   the lesson or item as the student will see it.

Accept: a chapter goes from passages to live using only the tooling + teacher
approvals; editing any approved object resets approval via its hash.
```

---

## P14 — G9: offline + sync  [TODO]

Prerequisites: P13 DONE.

```text
Implement G9 on branch g9-offline. Read CLAUDE.md, PLAN.md (G9),
ARCHITECTURE §11, §21. Show your step plan first.

1. Packs: offline-verifiable items, lessons, scenes, widgets for a chapter.
2. TypeScript mirrors of policy (R30–R40), diagnosis, ladder, BKT, ts-fsrs and
   widget predicates, driven by the same shared fixtures.
3. Sync: server re-verifies answers, ignores client correctness and widget
   results, recomputes ladder/BKT/FSRS from the event log, rejects/flags illegal
   sequences.
4. UI: offline indicator, "downloaded for offline" state, sync status; test by
   toggling the browser offline in Playwright.

Accept: all shared fixtures pass in Python and TS; an offline session synced
equals the server recompute for ladder and BKT state.
```

---

## P15 — G10: guardian and teacher views  [TODO]

Prerequisites: P14 DONE.

```text
Implement G10 on branch g10-views. Read CLAUDE.md, PLAN.md (G10). Show your step
plan first.

1. Guardian: progress by chapter status and ladder, what was learned this week,
   language switch, export/delete.
2. Weekly report job (channels from the profile); quiet hours from the profile.
3. Teacher: heatmap by ladder level, stuck-now, wheel-spinning and
   repeated-misconception alerts, review queue; consented students only.
4. UI for all of the above at 360 px and desktop; seed scenarios for a class.

Accept: reports from real events; no rankings or comparisons; teacher cannot see
a student without teacher_share; alerts resolve when the skill reaches level 4.
```

---

## P16 — G11: hardening  [TODO]

Prerequisites: P15 DONE.

```text
Implement G11 on branch g11-hardening. Read CLAUDE.md, PLAN.md (G11). Show your
step plan first.

1. PII stripping, moderation, distress script with pause and flag.
2. API rate limits (OTP/PIN limits kept).
3. Jurisdiction profile tests (strict default, retention, quiet hours in
   multiple IANA zones).
4. Error handling, demo seed, operator README.
5. Accessibility pass on student screens (labels, focus order, contrast,
   reduced motion) with fixes.

Accept: PII/moderation/profile tests green; a new operator can run a pilot from
the README.
```

---

## P17 — G12: pilot readiness  [TODO]

Prerequisites: P16 DONE; Track B content approved and live; legal review done.

```text
Implement G12 on branch g12-pilot. Read CLAUDE.md, PLAN.md (G12, Track B,
pilot metrics). Show your step plan first.

1. Verify the launch chapter is approved and live; list anything still draft.
2. Run all eval gates (ARCHITECTURE §26) and report each against its threshold.
3. Write the pilot protocol: metrics, duration, consent, optional research
   comparison design, pre-registered primary outcome.
4. Pilot metrics dashboard.
5. Produce a go/no-go checklist with evidence links.

Accept: go/no-go review items all have evidence; every eval gate met or listed
as a blocker.
```

---

## UI-1 — chat-first front door, role homes and design system  [IN PROGRESS]

Branch ui-1-chat-shell from master. Prerequisites: master clean and pushed; H1 and R1 merged (tags
harden-1-done, ui-responsive-done); server-side consent-scope validation present. Docs written first:
docs/UI_AUDIT.md, docs/UI_STANDARDS.md, docs/HOME_AND_ONBOARDING.md.

```text
PRODUCT RULE: the product opens as a chat-style interface (like ChatGPT or Claude): a welcoming screen
first, no login wall. Signing in or registering happens inside the conversation when the visitor
chooses. Once the app knows who they are it loads their details and shows workflow cards for their role.
Each workflow opens in a workspace panel (beside the chat on laptops, full screen on phones). The chat
stays as home and history.

LAYOUT: collapsible left sidebar; centred greeting in a self-hosted OFL serif display font; one large
rounded composer (grows to five lines) with mode chips; three suggestion cards; dismissible tip banner.
Own identity (Brand component, tokens file); no other product's name, logo or palette. The composer is a
deterministic topic or student finder: nothing typed is stored or logged, PII stripped, moderation on
input, "Did you mean" chips, "not in your syllabus yet", no generated answers, ASK stays off.
SuggestionCard: tone from tokens, inline SVG icon, title, tag, hover/focus/pressed, 44 px, keyboard
operable, skeleton, one primary action.

ROLES: Guest (setup cards), Student (Continue, Review due, Today's plan), Teacher and Parent (thin shells
opening the EXISTING views in the panel; clashes with the newer consent and school model are listed, not
fixed). Create account: Student = family code and PIN or "ask a grown-up"; Teacher = email code plus
school code; Parent = email code. Existing auth; scopes validated on the server.

BUILD (tests first, commit per step, targeted tests per commit)
1 Design system (tokens light/dark, shadcn/ui, assistant-ui primitives with a custom runtime and no model
  calls, self-hosted fonts, StatusChip, Choice, SuggestionCard, /dev/ui; report added JS weight; CI weight
  check).
2 Chat shell at "/" with a pure state machine (welcome, context, identity, home) and unit tests.
3 Setup chips from the registry (class, state, board, medium, subject); "coming soon" cannot start;
  guest choices on the device only.
4 Identity in chat (sign in, just try it, save my progress, parent, teacher, create account).
5 Role homes fed by the existing APIs.
6 WorkspacePanel wrapping the existing screens; deep links, back and refresh work; old routes keep
  working; structured summary message at the end of a workflow; no engine change.
7 Responsive shell (1280+, 1024-1279, 768-1023, below 768).
8 Restyle /dev; scenario logins land on the role home; fake teacher and parent in seed_scenarios.
9 Tests: PORT the existing Playwright specs (data-testid, no text selectors); new specs at 360x800,
  768x1024, 1280x800, 1536x900; overflow, clipping (English and one Indic locale) and focus checks; unit
  tests for the state machine, topic finder and registry options.
10 Self-critique against docs/UI_STANDARDS.md; fix; list remaining issues with severity.

ACCEPT: a first activity from "/" in five taps or fewer with no login; nothing typed is stored or logged
(tested at API and database level); all previously passing UI flows still pass (ported specs listed);
panel and sidebar behave at all four widths with no overflow; keyboard path works; page weight within
budget; added dependencies and licences listed; teacher and parent clashes listed.

HARD RULES: guest data on the device only; no analytics or tracking SDKs; no engine behaviour change; no
AGPL dependencies; region-neutral; strings through the locale registry; seed students only in dev. Do not
merge to master; do not push.
```
