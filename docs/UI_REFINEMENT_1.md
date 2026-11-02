# UI refinement 1 (UI-2)

Branch `ui-2-refine`, based on master after UI-1 was merged locally (not pushed). This is fixing and polishing what
exists. No new features, no change to orchestrator, verifier or mastery behaviour.

## Inputs

**Input 1: the user's findings.** None yet (the list was left empty). Add rows here as `U-n | screen | expected |
what happened` and they are triaged in the next pass.

**Input 2: the UI-1 "remaining issues" list** (from the self-critique), plus the page-weight finding.

## Triage

Severity: blocker (cannot finish a task), major (confusing or wrong for most users), minor, polish.

| id | screen | expected | actual | severity | probable cause | planned fix | test |
|----|--------|----------|--------|----------|----------------|-------------|------|
| R-01 | Lesson player | The title only | A raw skill id (for example `m10.quad.roots`) sits above the title | major | `LessonPlayer.tsx` renders `lesson.skill_id` in `.lp-subj` | Show the chapter or lesson kind in words, or nothing; never an id | e2e: no text matching an id pattern on the lesson screen; unit test on the header |
| R-02 | Home, Continue card | "Continue: <topic>" | Title reads `Continue: <skill id>` | major | `HomeCards.tsx` builds the title from `current.skill` | Use the chapter title only; drop the id | e2e on `card-continue`; no id pattern |
| R-03 | Workspace panel (embedded legacy screens) | Follow the app theme | Stay light in dark mode | minor | The iframe page has the legacy CSS with no `data-theme` hand-over | Pass the theme to the framed page (query flag or `yt:theme` message) and set `data-theme` on the root there | e2e: dark scheme, framed `body` background is dark |
| R-04 | Workspace panel | Browser Back leaves the panel step by step | Back is approximate: it can leave the app or skip a screen | minor | The iframe history is separate from the address `/?w=`; only `yt:nav` updates it | Push a history entry per `yt:nav`; on popstate set the frame source | e2e: open two screens, Back returns to the first, then to the chat |
| R-05 | Chat strings | Own language | English fallback in every other locale | minor | New `chat*` keys have no approved translations; machine translation is not allowed | Keep the fallback; list the keys needing human translation in `docs/` | locale-coverage test lists the missing keys (no failure) |
| R-06 | Setup chips (board, state) | Readable names | Ids shown (`cbse`) | minor | Registry has no display titles for boards or states | Add optional `titles:` to the registry content (content, not code) | unit test on label fallback; content validate |
| R-07 | Home, page weight | 150 KB | 272 KB (limit 275) | major | React and Next about 103 KB; assistant-ui about 100 KB | See Decisions needed D-1 | `check:weight` |
| P-01 to P-09 | Whole app | The polish list a to i in the prompt | Checked in step 4 | | | | |

Merged duplicates: the skill id appears in two places (R-01, R-02); both are fixed in the same step.

## Decisions needed

**D-1: page weight of `/`.** Option A: keep assistant-ui and keep the documented 275 KB limit. Option B: replace it with a
small hand-built message list and composer (about 177 KB estimated, still over 150 KB, and a larger change).
Recommendation: A for now. B only if real 4G numbers (step 4h) show a slow first paint. Not implemented here.

**D-2: guest to family upgrade screen.** The API exists (`upgrade_guest`), there is no screen. Option A: a "Save my
progress" card that opens the existing create-account flow with the guest data. Option B: leave it out until the pilot.
Recommendation: A, but it is a new feature, so it belongs in the next round.

**D-3: teacher sign-in school code.** The newer school model expects a school code. Option A: add the field to the
sign-in. Option B: keep teacher sign-in as is until the school onboarding is built. Recommendation: B.

## Next round

- Guest to family upgrade screen (D-2).
- School code on the teacher sign-in (D-3).
- Replace assistant-ui if D-1 goes to option B.
- Human translations for the `chat*` strings (R-05).

## Status (end of round, 2026-10-12)

| id | status | note |
|----|--------|------|
| R-01 | fixed | Lesson header no longer shows the skill id. Failing unit test first (`tests/lessons/LessonPlayer.test.tsx`), then the fix. |
| R-02 | fixed | The Continue card title is the plain "Continue"; the chapter is in the description. Guarded by `e2e/refine.spec.ts`. |
| R-03 | not fixed, next round | The legacy stylesheet has 44 hard-coded colours; a partial dark theme would put dark text on light cards. Needs a restyle of the legacy screens, which is more than a small fix. |
| R-04 | not reproduced | In Chromium the browser steps the framed screen back through the joint session history: Back returns to the previous screen, then closes the panel. The spec stays as a guard (360 and 1280 px). Safari and Firefox were not tried. |
| R-05 | not fixed (by rule) | No machine translation. The English fallback stays until a human translates the `chat*` strings. |
| R-06 | needs content | The `titles:` mechanism works; the display names for boards and states are for the curriculum lead to supply in `curriculum.yaml`. I did not invent official names. |
| R-07 | needs decision (D-1) | Home page is still 272 KB (limit 275). |

## Polish pass (step 4)

| item | result |
|------|--------|
| a first ten seconds | Checked in UI-1 (one primary action: the start cards or the composer). No change. |
| b states | Home cards have skeleton, error and empty states from UI-1. No gap found in the screens reached by the specs. Not audited: every legacy screen's offline state (next round). |
| c copy | Scanned English strings for skill, mastery, ladder, diagnosis, test, fail, wrong. Changed "Start diagnostic" to "Find where to start" and "this skill" to "this topic" in the skip-ahead message. Left "skills you can do" and "Your skills" (plain words, and two tests assert them). The Indic locales still transliterate "diagnostic"; that is for a human translator. Teacher screens use "skill" and "level" on purpose (audience). |
| d feedback tone | No change; covered by UI-1 and the existing lesson tests. Not re-audited. |
| e accessibility | The UI-1 specs already cover 44 px targets, visible focus and the keyboard path. No new finding. Contrast in dark mode was not re-measured. |
| f responsive | New specs pass for 1280x700, landscape phone 800x360, 200% zoom (640x400 viewport) and 1024x768: no horizontal scroll, composer inside the viewport. Screenshots `shape-*.png`. |
| g navigation | Back, deep links and refresh covered (R-04 spec and UI-1 shell spec). Switching roles on one device: covered by the UI-1 one-role-per-device tests. |
| h performance | Throttled 4G (1.6 Mbps down, 150 ms): shell on screen after about 0.25 s, all scripts loaded after about 1.8 s, layout shift 0.014 (limit 0.1), 284 KB transferred. The home is 272 KB gzip. |
| i friction (taps from the open home) | Guest to first lesson 5 (UI-1 spec); student to resume 1; student to start a review 1; teacher to heatmap 1. Before and after are the same: UI-2 changed no flow, so these are the UI-1 numbers. |

## Results

vitest 351 passed (350 before, plus the R-01 test). Playwright UI suite 71 passed (61 plus 10 new in `e2e/refine.spec.ts`).
`check:weight` ok (home 272 of 275 KB). Region check OK; locale generation no diff. No backend code changed, so ruff and mypy were not
re-run. Full API suite was run at the end of UI-1 (1297 passed) and is unaffected.
