# ADR 0005: Doubt solver, structured maths expressions only

**Status:** Proposed (2026-11-16). The owner has not approved it. Nothing in this ADR is switched on by the code that accompanies it.
**Scope:** the "Ask Brownie" doubt solver for maths typed or photographed by a student.
**Related:** `apps/web/lib/doubt/*` (on-device core), ADR 0004 (content factory kernel), the standing rule in `ChatApp.tsx` and `finder_rules_route` that typed text is matched in the browser and never sent, stored or logged.

---

## Context

The standing rule is that what a student types into the chat composer is matched in the browser and never sent, stored or logged. Only the explicit, consented AI paths (explain, lesson, chat) may send text.

A doubt solver wants to do two things that pull against that rule. It wants to work out maths from text and, later, from photos. And it would like the factory kernel (`apps/api/app/factory/kernel`, exact, standard library only) to certify the answer, but the kernel runs on the server.

The first part is solved on the device: `lib/doubt` detects, solves, builds hints and checks the student's own attempts in the browser with exact arithmetic, with no network, storage or logging (a test proves it). This ADR records the rule for the second part, so that nothing is built that quietly breaks the privacy design.

## Decision

1. **Images and free text never leave the device on any doubt-solver path.** A photo is decoded, cropped and read in the browser; its pixels are not uploaded, stored or cached beyond the tab's memory. Typed text is detected and solved on the device. It is not posted for routing, not stored and not logged.
2. **Only a confirmed, PII-screened, structured maths expression may ever be sent for server solving.** It is a JSON object of numeric coefficients and enumerated operators (`doubt-expr/1`). It has no free-text field, caps numbers at nine digits (so a phone number or an Aadhaar number cannot fit), and is built by the device from text that has already passed the device's own safety and PII screen and that the student has seen and confirmed.
3. **It is sent only under a consent scope** (proposed name `math_check`, guardian-only like the other optional scopes), after the student taps an explicit control. A guest, or a learner without the scope, never sends it.
4. **It is never stored.** The server does not store it, does not log it (including in validation errors), and does not pass it to a model. At most it keeps an aggregate counter with no learner, address or expression. Rate-limit windows live in process memory only.
5. **Labels stay honest.** Work done on the device is labelled "Worked out on your device". The words "Checked by code" are reserved for results the kernel accepted in the same response.
6. **Any later model use is a separate decision.** Rewording an already verified trace with a model, if ever wanted, sends structured ids and numbers only, never the student's words, under the existing `ai_processing` scope.
7. **Tests enforce it:** the device core is network-isolated (stubbed `fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket`, storage and `console` see zero calls), `lib/doubt` imports nothing from `lib/api` or any network module, and (when the server route is built) the request schema has no free-text field and no route accepts an upload.

## Consequences

- The on-device solver needs no server contact and no new consent. Detecting that a line is maths is done in the browser; what could later be sent is a structure, not the line.
- A server check adds one consent scope and one route, and cannot be switched on without the owner's approval of this ADR.
- The kernel cannot certify every doubt (irrational roots, arithmetic and simplify have no kind yet), so many answers will carry the device label, not the verified one.
- A student who types personal data into a "maths" box is protected twice: the device screen runs first, and the schema cannot carry words.

## Hint wording rule (owner decision)

Hints and worked steps teach "do the same operation to both sides" (inverse operations). They never teach "move it across and flip the sign". A test scans the authored copy and every generated hint for the shortcut wording.

## Owner approval checklist

1. This ADR text, in particular points 1 to 4.
2. The new consent scope name (`math_check`) and its plain-language wording (to be written with counsel).
3. That the on-device solver ships without a consent tick, because nothing leaves the device.
4. The two label wordings: "Worked out on your device" and the reserved "Checked by code".
5. That guests are excluded from any server check by default.
6. The aggregate-counter design (day, kind, outcome, count; no learner key; 400-day retention).
7. The order of work: device solver first, server check later.
8. That any Web Share Target (photo sharing from other apps) waits for counsel's answer to question 7 below.

## Questions for counsel

1. Is a schema-restricted, non-stored structured expression, sent with a bearer token and a source address, "personal data" of a child? If yes, is the guardian's `math_check` consent enough, or is notice under a legitimate-use ground acceptable for this narrow processing?
2. Does on-device OCR of a photo (no transfer) count as the Data Fiduciary processing at all? Does the camera permission need to be treated as a separate consent?
3. Do aggregate counters with no key and no per-learner history avoid the "tracking or behavioural monitoring" bar for children?
4. May a misconception tag be kept on the device only (not on our server) to power "review later", given the child-profiling bar?
5. Is the proposed in-app notice (once before the first server check, plus the guardian's tick) adequate, and do the 22-language and plain-language duties apply to the in-app card?
6. If a minor photographs a page that also shows another person's data and the photo is processed only on the device, is there any obligation?
7. Web Share Target: is a transient server round trip of an image (service worker not yet active) acceptable? Otherwise only the file input and the in-app camera ship.
8. Is "Checked by code" a claim that needs legal vetting as a claim substantiation, beyond the existing "Answer checked by calculation" wording?
9. Cross-border: does the host region matter for a request that carries no stored data?
10. Edge and host access logs record paths and query strings: is a GET carrying only closed-registry ids (skill id, misconception tag) acceptable?

## What this ADR does not do

It enables nothing. There is no consent scope, route, flag or migration in the change that proposes it.
