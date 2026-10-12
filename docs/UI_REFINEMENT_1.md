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

## Status

Filled in at the end of the round (fixed, not fixed with reason, needs decision).
