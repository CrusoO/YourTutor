# Video engine integration (consumer side)

Status: DRAFT. Contract version in use: none yet (the engine's contract is v0, draft). The video engine is a separate repository with its own VS Code window and Claude session. It is never edited from this repository, and this repository never copies its source, docs, prompts or change orders. The contract is `docs/ENGINE_INTERFACE.md` in the engine repository.

## What YourTutor does

- Receives a static engine package (player, lesson JSON, audio, captions, a manifest with hashes). It imports no engine code.
- Copies the package with a script that reads the sibling folder (`../EduVideoEngine/dist/engine-package`), writes it into the static assets and verifies every manifest hash.
- Loads the player lazily, only when a lesson opens.
- Owns the lesson sheet, the light and dark theme for the controls, the font files, accounts, progress, personalisation and the analytics it chooses to store.

## What YourTutor must keep true

| Item | Rule |
| --- | --- |
| Fonts | The font files and their URLs stay byte-identical to the hashes in the engine manifest. Tell the engine side before changing one |
| Home-page budget | 255 KB JS and CSS, fonts 70 KB English and 125 KB Hindi. The player must not count toward it |
| Stage height | The lesson sheet gives the player the screen height (dvh) or states its chrome height; measure it on the real sheet at 360 by 640 and report the number |
| Audio | The first play comes from a user gesture |
| Version | The manifest's contract version matches the version this repository records below; a mismatch is refused |

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
