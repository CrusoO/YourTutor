# Video engine integration (consumer side)

Status: DRAFT. Contract version in use: none yet (the engine's contract is v0, draft). The video engine is a separate repository with its own VS Code window and Claude session. It is never edited from this repository, and this repository never copies its source, docs, prompts or change orders. The contract is `docs/ENGINE_INTERFACE.md` in the engine repository.

## What YourTutor does

- Receives a static engine package (player, lesson JSON, audio, captions, a manifest with hashes). It imports no engine code.
- Copies the package with a script that reads the sibling folder (`../EduVideoEngine/dist/engine-package`), writes it into the static assets and verifies every manifest hash.
- Loads the player lazily, only when a lesson opens.
- Releases pin one engine package version, verify every manifest hash, and keep the previous version so a release can be rolled back. In CI the package comes from the engine's versioned archive, not from a sibling folder.
- Owns the lesson sheet, the light and dark theme for the controls, the font files, accounts, progress, personalisation and the analytics it chooses to store.

## Hosts

The web app comes first: responsive, installable as a PWA. The phone application comes later as a Capacitor wrapper around this same web app, using the same engine package and player. Lessons are never rebuilt as native screens. Rules for both:

- A lesson loads from a URL: http(s) on the web, an app-local URL in the wrapper. Correctness never depends on a service worker.
- Offline: a service worker may cache packages on the web. In the wrapper the app downloads packages into its own file storage, because iOS WebViews provide service workers only for a few app-bound domains and not reliably offline.
- The player sits in a slot sized from its own container, not the window. The host passes the safe-area insets and reports size and orientation changes.
- Desktop gives keyboard and pointer input; touch targets are at least 44 px.
- The same package is tested in the web app and in the wrapper before each release.
- Support floor (a proposal, decided by an ADR in the engine repository): Chrome and Android WebView 100, Safari 15.4, Firefox 100.

## What YourTutor must keep true

| Item | Rule |
| --- | --- |
| Fonts | The font files and their URLs stay byte-identical to the hashes in the engine manifest. Tell the engine side before changing one |
| Home-page budget | 255 KB JS and CSS, fonts 70 KB English and 125 KB Hindi. The player must not count toward it |
| Stage height | Measured on 2026-10-15: the existing lesson sheet has 272 to 298 px of chrome at 360 by 640 (header 53, step path 51 to 70, caption area 80 to 104, controls 97, fixed bottom bar 77), so it cannot host an engine lesson as it is. An engine lesson needs a dedicated compact layout with at most 184 px of chrome (header 48, captions 48, controls 56, padding 32), sized in dvh, or a stage slot of at least the lesson's `minStagePx` from the manifest |
| Audio | The first play comes from a user gesture |
| Version | The manifest's contract version matches the version this repository records below; a mismatch is refused |
| Drafts | With `ALLOW_DRAFT_CONTENT=false` an engine lesson is served only when its manifest state is approved. Draft lessons play only where drafts are allowed (development, staging). Today every engine lesson is draft |
| Consent | Lesson events (answers, progress) are stored only within the consent scopes the family gave: `tutoring` for the student's own progress; anything used for authoring analytics needs the pseudonymised research scope. Student free text is never logged |
| Operator check | `python -m app.operator check` gains an engine line: package present, contract version matches, every hash verifies, each lesson's state |
| Placement | The package lives in `apps/web/public/engine/` (or the reverse proxy's static folder). Hashed lesson files get long cache headers and the manifest a short one; set both explicitly |

## Checklist before turning it on

1. A fixture package is checked in or copied by the script; the smoke test mounts a lesson, plays to the first question point, answers it and reaches the end.
2. The home-page budget test passes with the player not loaded.
3. A manifest with a different contract version is refused with a clear message.
4. The lesson works offline after load (network cut in the browser test).
5. An ADR records the contract version adopted and where the question interface lives.

## Do not

Keep engine prompts, change orders or ADRs here. Put a copy of the engine's docs here. Reach into the engine repository from application code. Change the engine's fonts or budgets from this side.

## Contract version adopted

None yet.
