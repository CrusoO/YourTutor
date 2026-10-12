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
  set; dark follows the system. WCAG AA contrast (4.5:1 text, 3:1 large text and controls) in both.
* Status chips (solid, can do it, learning, review due, not started, coming soon) are always text plus
  colour (and an icon shape), never colour alone.
* Icons are never used without a text label (an accessible name counts only for decorative repeats).
* Motion is CSS only, short, and off under `prefers-reduced-motion`.
* Wrong answers: neutral colour and a clear next step. No red flashes, no buzzers, no shaking. Red is for
  real errors only (network failure, invalid input).
* No confetti, streak threats, leaderboards, badges that shame, countdown pressure or rankings.
* Fonts: self-hosted, OFL-licensed, with per-script fallbacks and per-script line-height tokens
  (Latin 1.5, Devanagari and Bengali-Assamese 1.7, others set in the token file).

## Input and access

* Touch targets at least 44 px. Hover is an enhancement only, never the only way to do something.
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
