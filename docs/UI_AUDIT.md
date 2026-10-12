# UI audit (before UI-1)

Taken on branch `ui-1-chat-shell` from master `a58a71a`. Screenshots (not committed, the folder is
ignored): `apps/web/test-results/screens/baseline-360-*.png` and `baseline-1280-*.png` for dev,
after-login, today, subjects, chapters, skills, practice, lessons-list, lesson.

## Routes and what they render

| Route | Renders | Who |
| --- | --- | --- |
| `/` | Redirects: to `/subjects` if a token is stored, else `/login` (dev skip-login aside). No content of its own. | everyone |
| `/login` | Family code and PIN form (existing student login). | student |
| `/start` | Guest start: curriculum, grade, subject and language selects, then `POST /guest/start`. | guest |
| `/subjects` | One Maths card, link to `/offline`, language switch. | student, guest |
| `/chapters` | Chapter cards (recommended, status chips, coming-soon cards). | student, guest |
| `/chapters/[id]` | Skill path with status chips, "Continue this chapter", skip-ahead test-out. | student, guest |
| `/today` | Goal, active minutes left, Resume, Start practice, diagnostic, checkpoint. | student, guest |
| `/session/[id]` | Practice player: stem, answer, hints, stuck picker, break, done screen, read aloud. 524 lines. | student, guest |
| `/offline` | Pack download, offline practice, sync. | student |
| `/checkpoints/[id]/forms/[form]` | Research checkpoint form (research module only). | research |
| `/staff/login` | Email code sign-in for parent and teacher. | staff |
| `/guardian` | Child list, weekly view, consent, export, delete, flags. | parent |
| `/teacher` | Classes, heatmap, stuck now, alerts, review queue. | teacher |
| `/admin/pilot` | Pilot enrolment and metrics. | admin |
| `/dev`, `/dev/lessons[/id]` | Developer tools: scenario logins, lesson list and preview. 404 unless `NEXT_PUBLIC_DEV_TOOLS`. | developer |
| `/api/health` | Health check. | ops |

`/dev` is a developer tool, not the product. Nothing in the product links to it.

## What already exists

* Guest start with registry-driven options (`GET /guest/context`: curricula, grades, subjects, books,
  languages), the first-run flow, the upgrade path (`ask a grown-up`), server-side consent-scope checks.
* The ui-responsive shell: one centred column that widens at 768, 1024 and 1280 px, card grids,
  a 640 px lesson stage and practice column. No sidebar, no panel, no chat.
* Student and staff auth (family code and PIN; email code), kept in `localStorage` (`yt_token`,
  `yt_student_id`, staff token).

## Styling state

* One global stylesheet (`app/globals.css`, ~800 lines): a handful of colour variables, hand-written
  classes (`.stack`, `.card`, `.banner`, `.flag`, `.lp-*` for lessons). Light only, no dark mode,
  no design tokens file, no component library, system fonts only.
* Status chips exist (`components/flow/StatusChip.tsx`); everything else is plain elements.
* Strings come from `lib/messages.ts` with an English fallback.
* Page weight: lesson screen 131 KB transferred (budget in `e2e/weight.spec.ts`: 200 KB total).

## Gaps UI-1 addresses

1. No front door: `/` is a redirect; a visitor meets a login form or a select list first.
2. No role homes: parent and teacher pages are standalone, reached from `/staff/login`.
3. No shared shell, navigation, history or dark mode; no tokens; no component library.
4. Tests select by button text (for example "Start practice"), so any shell change breaks them.
5. The registry has no state list and no display titles; options are ids (see Decisions in PLAN.md).

## Baseline problems seen in the screenshots

* 1280 px: single left-aligned column, large unused side areas, full-width buttons on some screens.
* 360 px: fine, but chrome is minimal (no way back to a home, no sign of who is signed in).
* Teacher and parent pages assume the older consent and school model in places (listed in the UI-1
  report, not fixed there).
