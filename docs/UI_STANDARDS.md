# UI standards

Applies to every student, teacher and parent screen. Developer pages (`/dev`) use the same tokens
but are exempt from the page-weight budget.

## Layout and devices

* Breakpoints: 360, 768, 1024, 1280, 1536 px. Phone and laptop are equal targets.
* 1280 and wider: sidebar, chat and workspace panel side by side. 1024 to 1279: sidebar and chat, the
  panel is an overlay. 768 to 1023: collapsible sidebar. Below 768: drawer sidebar, composer docked at
  the bottom above the keyboard, cards stacked or in a horizontal scroller.
* Reading width about 70ch. `dvh` units, safe-area insets, no horizontal page scroll at any width.
* One primary action per screen (per card). Everything else is secondary or a link.

## Look and feel

* Calm, focused, modern. One accent colour. Colours are CSS variables (tokens) with a light and a dark
  set; dark follows the system. Contrast in both: text 4.5:1, body and muted text 7:1, borders of inputs, focus rings and meaningful
  icons 3:1. Every pair is listed in `lib/contrast.ts` and checked by `tests/ui/tokens.test.ts` and, on
  the rendered screens, by `e2e/teen.spec.ts`.
* Status chips (solid, can do it, learning, review due, not started, coming soon) are always text plus
  colour (and an icon shape), never colour alone.
* Icons are never used without a text label (an accessible name counts only for decorative repeats).
* Motion is CSS only, short, and off under `prefers-reduced-motion`.
* Wrong answers: amber ("not quite") with a marker, words and a next step; right answers: quiet green
  with a check and words. Feedback is a `role="status"` region. No red flashes, no buzzers, no shaking.
  Red is for real errors only (a failed save, a network failure, invalid input).
* No confetti, streak threats, leaderboards, badges that shame, countdown pressure or rankings.
* Fonts: sans-serif (system stack with per-script fallbacks) for everything a student reads; the serif
  (Fraunces, self-hosted, OFL) only for the one-line greeting. Body 16 px minimum on phones; question and
  lesson text 18 px at line height 1.5; per-script line-height tokens (Latin 1.5, Devanagari and
  Bengali-Assamese 1.75).

## Input and access

* Touch targets at least 48 px on touch screens (44 px is the floor for dense desktop controls). Hover is an enhancement only, never the only way to do something.
* Full keyboard navigation in a logical order with a visible focus ring (3:1 against its background).
  Enter checks an answer. Esc closes a panel or sheet and returns focus to where it came from.
* Screen readers: landmarks (nav, main, complementary), live regions for feedback and new chat
  messages, labelled controls, no focus traps outside dialogs.
* Text scales to 200% without loss. No text clipping in English or in an Indic locale.

## Performance

* Page weight budget: 150 KB transferred per screen, excluding audio (CI check; the lesson screen is
  the measured reference). Skeleton screens while loading. No third-party scripts, analytics or tracking.

## Testing

* Playwright projects at 360x800, 768x1024, 1280x800 and 1536x900 with screenshots. Fail on horizontal
  overflow, clipped text (English and one Indic locale) or a missing focus style. Light and dark are
  looked at once per screen.
* Stable `data-testid` attributes on key controls; tests never select by button text.

## Critique checklist (run on every screenshot)

1. Is there exactly one primary action? 2. Can it be done with keyboard only? 3. Is every chip text plus
colour? 4. Any icon without a label? 5. Contrast in light and dark? 6. Any overflow or clipping at 360
and 1280? 7. Is a wrong answer neutral with a next step? 8. Does the layout match the breakpoint rules?
9. Is anything typed shown, stored or logged that should not be? 10. Is the weight inside budget?

## Theme and comfort (UI-2b)

* Theme: Auto (follows the device), Light or Dark; stored on the device; applied before first paint by
  an inline script, so the wrong theme never flashes. A switch lives in the sidebar and in Settings.
* Comfort (Settings): text size (small 16 px, medium 17 px, large 19 px base), line spacing (normal or
  roomy), motion (follow the device or less motion). Stored on the device; applied without a reload.
* Page background is never pure black or pure white (`--c-bg`); white cards on the light page are fine.
  The one exception is the lesson and practice surface (`--c-lesson`): pure white in light and the dark
  background in dark (UI-4).
* Transitions 150 to 250 ms (`--dur`), off under reduced motion. No confetti.
* Home: no streak counter, no loss framing, no leaderboard or rank anywhere. The weekly row only shows
  the days active this week, read from dates kept on the device.

## Copy guide

Write for 15 to 18 year olds: direct, warm, short. Say what happened and what to do next. No baby talk, no
"Oops!", no exclamation marks, no fear words (test, fail, wrong, mistake) and no jargon (skill id,
mastery, ladder, diagnosis). Every wrong-answer message ends in something to do. Strings go through the
locale registry; a new string is English only until a human translates it.

| Before | After | Why |
|---|---|---|
| Not yet. Try again. | Not quite. Look at it once more, or tap Hint. | Gives a next step. |
| Could not load this page. Try again. | That didn't load. Check your connection and try again. | Says the likely cause. |
| Start diagnostic | Find where to start | No jargon. |
| Every try helps. Come back when you are ready. | Nothing new this time. Come back whenever you're ready. | No pep talk, no pressure. |
| Try a lesson | See a short lesson | Says what you get. |

## Plain paper and boards (UI-4)

* Lessons, practice and widget areas use plain surfaces from the tokens. No graph-paper or other texture
  behind text, ever; a test asserts `background-image: none` on every lesson surface.
* The earlier graph-paper look is reversed: it was visually irritating. A grid is opt-in: Settings >
  Comfort > Board paper, Plain (default) or Light grid. It affects only the grid lines of the graph
  widget, persists on the device (`yt.comfort`, `data-paper` on `<html>`) and never touches lesson text.
* Board (BOARD-1 amendment, not built yet). When the Excalidraw board is added it must: open with the
  grid off (`gridModeEnabled: false`) and `viewBackgroundColor: "#FFFFFF"` in light; take its `theme`
  prop from our Auto, Light and Dark choice, so dark mode shows its near-black canvas; start from the
  light and dark student templates (`lesson-board-integers-student.excalidraw` and `-dark.excalidraw`,
  generated by `make_lesson_board.py`); and snap to whole numbers from tick positions, never from the grid.
