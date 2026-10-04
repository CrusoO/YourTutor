# v2 gap audit (code vs PLAN / ARCHITECTURE v2)

**Test baseline (2026-10-04, confirmed):** `apps/api` pytest **232 passed, 0 failed** on Postgres (`TEST_DATABASE_URL`), both `-p no:randomly` and `pytest-randomly` seeds 1, 2, 3. `apps/web` vitest **33 passed**; `tsc --noEmit` **ok**; region-literal check **clean**; locale generation **no diff**. `ruff check .` **156 errors** (122 E501, 16 F401, 11 I001, 5 F811, 2 UP) and `mypy .` **51 errors** (mostly missing `types-PyYAML` stubs) — pre-existing, none in files touched by the G0 verification pass; not fixed here. Playwright not run. *(Prior: 231 passed; G0 registries 222.)*

`docs/TUTOR_CONSTITUTION.md` — **present** (orchestrator/LLM/evals should cite it; code still mostly v1).

### Constitution vs current code (gaps)

| Rule | Constitution | Code today |
|------|--------------|------------|
| 5–6, R30–R31 | Diagnose before correcting; slips vs misconceptions | Wrong answers go straight to hint ladder (`policy._on_answer` → `_deliver_hint`); no `diagnosis/` |
| 5, R32 | Ask before telling (`request_help` → stuck-point) | `request_hint` only; no `ask_stuck_point` UI/API |
| 8, R38 | Worked-example-first vs problem-first by prerequisites | Single predict → worked_example → practice path |
| 9, R33–R34 | Prerequisite probe; wheel-spinning stop | Not implemented |
| 10, §11.2 | Correct ≠ mastery; explain/transfer evidence | BKT/p_known only; explain-back optional, no ladder |
| 11, R37 | Challenge after easy streak | Tier selection only; no transfer/challenge action |
| 13, R40 | Never end on failure | Caps can end after wrong/reveal without success item |
| 1–4 | Study Mode grounding, citations, no invent | No Ask/passages; practice uses authored items only |
| 14–16, §9.3 | Grade-band word limits; process praise only | Static copy; no tone evals or band limits in gateway |
| 19–20, R35–R36 | Disengagement / frustration handling | Client idle nudge only; no `break_or_switch` / de-escalation tier |
| 24 | Safeguarding script on distress | Not verified in player/API |

---

## a) Region / curriculum literals in code (G0 replacements)

| Kind | Examples (file:line) | G0 replacement |
|------|----------------------|----------------|
| Board enum + TZ map | `apps/api/app/auth/scopes.py:6–8` (`bhutan`/`seba` → `Asia/Thimphu`, `Asia/Kolkata`); validation `service.py:234–246` | `curriculum_id` + jurisdiction profile default TZ; free IANA on student |
| Board → chapter id | `service.py:847` (`bhutan_class9` / `seba_class9`) | `content/curricula/` + overlay FK by `chapter_id` |
| Default TZ fallback | `player/runtime.py:577` (`Asia/Thimphu`) | Profile or student `timezone`; no region default in code |
| Pilot/API defaults | `auth/admin.py:26` `board="bhutan"`; routers accept `board: str` | Context key from registry; drop board string API |
| Web locales | `lib/messages.ts:1` `Locale = "en"\|"ne"\|"as"`; `login/page.tsx:43` | `config/locales.yaml` + loader; fallback chain |
| Dev/e2e only (still CI grep targets) | `dev-auth.ts:33`, `admin/pilot/page.tsx:20`, `e2e/*.ts` | Test fixtures referencing `sample_board` ids |

**Allowed today:** `content/overlays/*.yaml`, `content/e2e_mini/`, seed scripts, tests — stay under `content/` / `tests/`.

---

## b) Milestones G0–G12 (vs repo)

| Milestone | Status | Evidence |
|-----------|--------|----------|
| **G0** Registries | **Met (2026-10-04)** | `config/` + `content/curricula/`; Alembic 0009–0010; `context_key`; locale FKs; `RESEARCH_MODULE`; quiet hours via jurisdiction profile |
| **G1** Ladder | **Not started** | Mastery is BKT/p_known only (`learner/`); no `item.role`; no ladder compute |
| **G2** Diagnosis + R30–R40 | **Not started** | v1 `policy.py` only; no `diagnosis/`; no stuck-point / wheel-spinning / R40 |
| **G3** Lessons/scenes/widgets | **Not started** | No `lessons/`, scenes, widget registry; player is single `session/[id]/page.tsx` |
| **G4** LLM gateway | **Not started** (was M6) | No `llm/` gateway; explain-back ungraded path partial in policy only |
| **G5** Student app v2 | **Partly done (M7a)** | Today + session player, family PIN, `can_request_hint`/`can_show_solution`, e2e mini, component tests; **no** guest, chapter map, lesson beats, scene player, locale registry |
| **G6** Accounts v2 | **Partly done (M2)** | Family OTP/PIN/consent; **no** guest/upgrade/school `site_id`/profile-scoped scopes |
| **G7** Ask / grounding B–D | **Not started** | No passages/pgvector Ask flow |
| **G8** Content scale tooling | **Partly done (M4.5)** | Validator, review export/import, templates; **no** lesson/scene authoring pipeline |
| **G9** Offline sync | **Not started** (M7b) | No TS policy mirror / sync packs |
| **G10** Parent/teacher v2 | **Partly done (M8)** | Basic teacher routes; **no** ladder heatmap / wheel-spinning alerts |
| **G11** Hardening | **Partly done (M9)** | Some security tests; JWT still localStorage; jurisdiction tests missing |
| **G12** Pilot readiness | **Not started** | Track B content still largely draft |

---

## c) Schema (ARCH §22) — migration order (proposed)

1. **G0a:** `locales`, `curricula`, `books`, `chapters`, `sections`; seed `sample_board` from `bhutan_class9` / `seba_class9` overlays.
2. **G0b:** `students`: add `curriculum_id`, `book_id`, `account_mode`; migrate `board` → `curriculum_id` (`bhutan`→`sample_board` mapping table); `home_language`/`exam_language` → FK `locales.code`; keep `timezone` text.
3. **G0c:** `overlays.section_map`; items `section_id` nullable backfill.
4. **G1+:** `items.role`, mastery `ladder_level` + `ladder_evidence`, `teacher_alerts`, `content_gaps`, `passages`, `lessons`, `scenes`, `widgets` — **separate migrations per milestone**, not in G0.

---

## d) Tests likely to break or need rewrites

- **Board/timezone:** `tests/conftest.py`, auth tests, pilot enrol, `test_locale_gate.py` — switch to registry ids.
- **Policy/orchestrator:** New diagnosis + R30–R40 fixtures; some v1 transition tests extended, not deleted.
- **Player contract:** Rename `can_request_hint` → `can_request_help` alias when G2 lands; keep alias tests.
- **Postgres loader:** Already flaky/failing seed count — fix when content paths change for `sample_board`.
- **Playwright:** Enrol uses `board: bhutan` — update to curriculum context API (G5/G0).

---

## e) Doc vs code conflicts (do not resolve here)

| Issue | Docs say | Code today | Recommended choice |
|-------|----------|------------|-------------------|
| Hint event name | `request_help` (+ alias) | `request_hint` | G2: accept alias; migrate client to `request_help` |
| Action flags | `can_request_help` | `can_request_hint` | G2: add alias field; deprecate old name in OpenAPI |
| T / mastery target | Ladder level &lt; 4 | p_known &lt; 0.95 | G1 before changing selection tests |
| Quiet hours | Jurisdiction profile | Hard-coded 21:00–07:00 + board TZ | G0 profile loader; keep behaviour until profile wired |
| i18n | Locale registry + next-intl (Arch layout) | `lib/messages.ts` hand locales | G5 decision: registry-driven messages without next-intl until G5 |
| Research | `RESEARCH_MODULE=off` hides routes | Checkpoint always mounted | G0 flag + 404 tests |
| Context picker | Required before practice | Pilot sets chapter implicitly | G5 guest + GET `/curricula/...` |

---

## f) G0 refined steps (ordered, with proof tests)

1. **Add `config/locales.yaml`, `grade_bands.yaml`, `jurisdictions/default_strict.yaml`** + pure loaders. *Tests:* loader unit tests; YAML schema smoke.
2. **Add `content/curricula/sample_board/`** mirroring existing chapter/skills; overlays reference `curriculum_id`. *Tests:* validator still green; overlay refs resolve.
3. **DB: `locales` + curriculum tables** (Alembic 0007). *Tests:* migration up/down on Postgres.
4. **Migrate `students.board` → `curriculum_id` + `book_id`** with data migration from bhutan/seba. *Tests:* existing M2 auth tests updated; no `board` in API responses (compat field optional one release).
5. **Remove `DEFAULT_TIMEZONE` map**; set TZ from profile default + student override. *Tests:* quiet-hours unit tests use profile fixture.
6. **`RESEARCH_MODULE` config**; mount checkpoint/analytics routers only when on. *Tests:* 404 when off; M5 checkpoint tests with on.
7. **Context key dataclass** used in session start + content lookup (ids only, no I/O in policy). *Tests:* session start stores key on session row JSON.
8. **CI grep:** fail on `\bbhutan\b|\bseba\b|Asia/Thimphu` outside allowlist paths. *Tests:* meta-test or script in CI.

**Stop here for G0** — do not start G1 until review.
