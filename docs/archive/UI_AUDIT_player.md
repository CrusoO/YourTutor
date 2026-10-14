<!-- Archived: dated audit of the student player before UI-1 (2026-10-04); superseded by docs/UI_AUDIT.md and docs/UI_STANDARDS.md. -->

# Student player UI audit (read-only)

## 1. Where is the student player?

All routes live under `apps/web`. There is no separate diagnostic/checkpoint route: **Today** starts a session; **`/session/[id]`** renders every session type (practice, diagnostic, checkpoint).

| File | Role |
|------|------|
| `app/page.tsx` | Home redirect: `/today` if `yt_token`, else `/login`. |
| `app/login/page.tsx` | Family code + PIN sign-in; language toggles (en/ne/as). |
| `app/today/page.tsx` | Goal, remaining minutes, resume, start practice/diagnostic/checkpoint. |
| `app/session/[id]/page.tsx` | **Session player** (all action types + done). |
| `app/layout.tsx` | Root shell: 360px `.phone` wrapper, metadata. |
| `app/globals.css` | Tap targets, stack layout, player styling. |
| `app/admin/pilot/page.tsx` | Pilot enrol form + printable login card (family code + PIN). |
| `app/api/health/route.ts` | Web health check for Docker/Playwright. |
| `lib/api.ts` | Fetch client, JWT + student/locale storage, session APIs. |
| `lib/messages.ts` | Static en/ne/as strings via `t()` (not next-intl). |
| `next.config.ts` | Rewrites `/checkpoints/*` to API (paper/study forms; not M7a player). |
| `app/checkpoints/[checkpointId]/forms/[form]/page.tsx` | Server redirect to API checkpoint HTML forms; **not** the student checkpoint player. |

## 2. Action type → component

All rendering is in `app/session/[id]/page.tsx` unless noted.

| Action | Component / block | Notes |
|--------|-------------------|--------|
| `warmup_item` | Lines 177–210 (shared) | **3 types → 1 block** with `show_item`, `similar_item`. |
| `predict` | Lines 105–115 | |
| `worked_example` | Lines 118–135 | Step reveal is local `step` state only. |
| `show_item` | Lines 177–210 | |
| `feedback` | Lines 240–246 | |
| `hint` | Lines 138–158 | |
| `reveal_solution` | Lines 161–174 | |
| `similar_item` | Lines 177–210 | |
| `explain_back_prompt` | Lines 213–231 | **2 types → 1 block** with `explain_back_result`. |
| `nudge` | Lines 234–237 | **Also:** idle overlay 92–103 is **not** `action.type === "nudge"`; it is client-only before `idle_nudge` event. |
| `end_session` | Lines 71–82 (done) | **2 types → 1 block** with `checkpoint_score`. |
| `checkpoint_score` | Lines 71–82 | |
| *(extra)* `content_gap` | Lines 249–252 | Not in API list; has UI. |

No listed action lacks a branch. Shared blocks are intentional but blur per-type UI.

## 3. Teaching logic in the UI (should be server-only)

| Leak | File:line | What |
|------|-----------|------|
| Reveal button gated on `hint_level_shown >= 2` | `session/[id]/page.tsx:153–157, 205–208` | Client decides when “Show the solution” appears; server should expose a single flag. |
| Hint button gated on `hintReady` + `wrongOnce` | `session/[id]/page.tsx:26–28, 57–60, 200–204` | 60s timer OK; **`wrongOnce` forces hint UI immediately** after wrong answer (partial policy). |
| `idle_nudge` keeps prior `action` when response is `nudge` | `session/[id]/page.tsx:50–53` | Correct resume UX; not pedagogy. |
| Worked-example step index | `session/[id]/page.tsx:126–133` | Presentation only; `continue` sent to API after last step. |
| Feedback copy from `action.correct` | `session/[id]/page.tsx:242` | Display only. |

No BKT, caps, or next-item selection in the web app. **`e2e/smoke.spec.ts`** implements its own event loop for diagnostic/checkpoint (not UI).

## 4. Quality notes

- **Duplication:** MCQ + `AnswerForm` repeated in `hint` and `show_item` blocks; predict yes/no mirrors MCQ pattern.
- **Oversized:** `app/session/[id]/page.tsx` **~317 lines** (whole file); default export ~248 lines — split candidate.
- **Typing:** `ActionPayload.type` is `string`; `today()` and `enrolPilot()` return untyped JSON; `req()` returns `any`-ish.
- **i18n:** **No `next-intl`.** Uses `lib/messages.ts`. Hardcoded UI: `session/[id]/page.tsx:69` (`…`), `:77` (`Score:`), `:91` (raw `session_type`); `admin/pilot/page.tsx` (all labels); `today/page.tsx:38` (`Could not start`); `layout.tsx` metadata strings.

## 5. API client & storage; offline (M7b)

- **Storage:** `yt_token` (Bearer), `yt_student`, `yt_locale` in `localStorage` (`lib/api.ts`).
- **Calls:** `studentLogin`, `today`, `startSession`, `getSession`, `postEvent`, `enrolPilot` — all `fetch`; no retry/offline queue.
- **Offline would break:** login, Today, session load/resume, every `postEvent` (orchestrator state lives server-side). Local timers (60s/90s) would fire without sync; `client_event_id` UUIDs need durable outbox; token/session id useless without API; worked-example steps could desync from server phase.

## 6. Tests vs screens

| Test | Coverage |
|------|----------|
| `e2e/smoke.spec.ts` | Login → Today → diagnostic (I don’t know via API drain) → practice (predict, worked example, wrong, hint, reveal) → checkpoint (API drain) → done heading. Does **not** assert pilot admin UI or resume/idle/nudge/explain_back. |
| `tests/health.test.ts` (Vitest) | **`/api/health` only** — no player screens. |

## 7. Commands

**Docker (full stack):** from repo root: `docker compose up -d` → web http://localhost:3000, API :8000.

**Web only (host):** `cd apps/web && npm install && npm run dev` (needs API + `NEXT_PUBLIC_API_URL`).

**Vitest:** `cd apps/web && npm test`

**Playwright:** `cd apps/web && npm run test:e2e`  
With stack already up: `$env:PLAYWRIGHT_NO_WEB="1"; $env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"; npx playwright test`

**Typecheck:** `cd apps/web && npm run lint`
