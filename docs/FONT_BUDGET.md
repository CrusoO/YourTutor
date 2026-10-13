# Font budget (UI-5)

Status: **ceilings approved (2026-10-13) and enforced** by `apps/web/scripts/check-weight.mjs` (`npm run check:weight` after `next build`): home JS and CSS 255 KB, English fonts 70 KB, Hindi fonts 125 KB. Raising any of them needs an explicit change to that script in the same pull request, with the reason. The branch is still not merged.
Launch languages: English and Hindi only (UI-5 scope change). All fonts are OFL-1.1, self-hosted in `apps/web/public/fonts`
(licence texts in `LICENSES.txt` next to them), Latin and Devanagari subsets only. No CDN, no other script.
Measured 2026-10-13 on the production build (`next build`, gzip JS and CSS from `scripts/check-weight.mjs`, fonts as
transferred, woff2 is already compressed).

## 1. Every file, measured

| File | Bytes | KB | Used for | Loaded when |
|---|---:|---:|---|---|
| geist-mono-latin-300 | 10,020 | 9.8 | display line (headline) | English, first view, **preloaded** |
| geist-mono-latin-500 | 10,116 | 9.9 | labels, nav, tags, short buttons | English, first view, **preloaded** |
| inter-latin-400 | 23,664 | 23.1 | every reading surface | English, first view, **preloaded** |
| inter-latin-600 | 24,452 | 23.9 | emphasis: card titles, buttons, headings | English, first view, not preloaded (swap) |
| noto-sans-devanagari-deva-400 | 50,416 | 49.2 | Hindi body | Hindi only, after first paint |
| noto-sans-devanagari-deva-500 | 53,620 | 52.4 | Hindi display, labels, emphasis | Hindi only, after first paint |
| noto-sans-devanagari-latin-400 | 10,512 | 10.3 | Latin words inside Hindi lines (Class 12, Maths) | Hindi only, after first paint |
| noto-sans-devanagari-latin-500 | 10,728 | 10.5 | same, display weight | Hindi only, after first paint |

English first view: 4 files, **66.7 KB** (the four Latin files: Geist Mono 300 and 500, Inter 400 and 600).
Hindi: 4 files, **122.3 KB**, and **no Geist or Inter at all** (the Noto Latin subset keeps Latin words in the same family
as the Hindi around them; a test checks this). English users never download any Devanagari file (a test checks this).
Hindi uses at most weights 400 and 500, with `font-synthesis: none`, so the browser never fakes a bold or italic.

## 2. Home page weight, before and after

| | JS and CSS (gzip) | Fonts | **Total** |
|---|---:|---:|---:|
| Before (UI-4): English and Hindi alike | 244.5 | 18.0 (Fraunces latin 500) | **262.5** (limit 265) |
| After: English | 249.7 | 66.7 | **316.4** |
| After: Hindi | 249.7 | 122.3 | **372.0** |

The old script counted only the one home font, so the like-for-like change is +53.9 KB for English and +109.5 KB for
Hindi. JS and CSS grew 5.2 KB (language store, the Hindi string file, identity CSS, new components); the 265 KB limit on
JS and CSS alone would still hold (249.7), it is the fonts that do not fit inside it.

## 3. Proposal

**(a) A separate fonts budget, with its own number and reason.** Stop folding fonts into the JS and CSS number.

| Budget | Proposed limit | Measured | Reason |
|---|---:|---:|---|
| Home JS and CSS (gzip) | 255 KB (was 265 incl. a font) | 249.7 | React and Next are 103 KB and assistant-ui about 100 KB before any of our code; the limit is the measured value plus about 5 KB, so it can only shrink unnoticed |
| Fonts, English first view | 70 KB | 66.7 | The identity needs a mono display face and a reading face; four files is the minimum that gives a display weight, a label weight, a body weight and an emphasis weight |
| Fonts, Hindi | 125 KB | 122.3 | Devanagari is 50 KB per weight and cannot be subset further without breaking conjuncts; two weights and the matching Latin subset is the floor for a readable Hindi UI |
| Fonts, Hindi first paint | 0 KB | 0 | Loaded after first paint, so it never competes with the first view (system Devanagari shows until the faces arrive) |

Preload: only the three Latin files used above the fold (Geist Mono 300, Geist Mono 500, Inter 400, 43.1 KB) and only
when the language is English (the init script in `<head>` skips them for Hindi). Inter 600 is not preloaded.

**(b) What was trimmed elsewhere to compensate.** Honestly: only Fraunces (-18.0 KB) is gone. Nothing else was cut from
the JavaScript, and JS and CSS grew 5.2 KB. The Hindi page does not download the Latin faces it would not use
(-66.7 KB for Hindi against a naive "load everything" approach), and Devanagari is never fetched for English (-122.3 KB
for English). No extra trimming is claimed beyond that.

**(c) Options to cut further, if you want a smaller number.**

| Option | English fonts | Hindi fonts | Cost |
|---|---:|---:|---|
| Proposal as measured | 66.7 | 122.3 | none |
| One variable Inter file (`wght`, 47.1 KB) instead of 400 and 600 (47.0 KB) | 66.8 (+0.1) | 122.3 | **no saving at two weights**; a variable file only pays off from three weights |
| Drop Inter 600; emphasis by Geist Mono 500 and size only | 42.8 (-23.9) | 122.3 | reading text loses a bold; headings and card titles would lean on the mono face, which the identity limits to short strings |
| Hindi at weight 400 only (emphasis by size) | 66.7 | 59.5 incl. Latin 400 (-62.8) | the Hindi display line loses its heavier weight; matras look thinner on the headline |
| Drop Geist Mono 300 (use 500 for the headline too) | 56.9 (-9.8) | 122.3 | the light, airy headline of the mockup becomes heavier |
| Drop Inter 600 and Hindi 500 together | 42.8 | 59.5 | smallest viable set: about 43 KB English and 60 KB Hindi |

My recommendation: approve the proposal as measured (70 and 125 KB), and treat "drop Inter 600" as the first lever if
the budget has to come down, because it is the only one that cuts English without touching the identity's display line.

## 4. Shared with the video engine

The engine's player needs the same two scripts plus KaTeX's own maths fonts (see
`EduVideoEngine/docs/FONT_BUDGET.md`). If its player is hosted on the same origin as YourTutor and uses the **same
files** (Inter 400 and 600, Noto Sans Devanagari 400 and 500 with its Latin subset), the browser downloads each file once
and a student who has seen the home already has most of the lesson's fonts. The engine now bundles exactly these files (byte-identical, locked by hash, same URLs and `unicode-range`), so a lesson adds only
KaTeX's three maths fonts (46.9 KB) on top of the home page's fonts. Its equations are pre-rendered at build time, so the player
ships no KaTeX script (91.8 KB gzip saved). See `EduVideoEngine/docs/FONT_BUDGET.md`. Changing this set means changing both together.

## 5. How this is enforced

* `e2e/identity.spec.ts` "fonts": English never fetches a Devanagari file; Hindi fetches the Noto files and no Geist or
  Inter file; every request is same-origin.
* `scripts/check-weight.mjs` counts JS and CSS (limit 255 KB for the home) and prints one fonts line per language with the
  approved limits (70 and 125 KB); any line over fails the run (exit 1). Measured now: 249.7, 66.7 and 122.3 KB.
* The preload list lives in `COMFORT_INIT_SCRIPT` (`lib/comfort.ts`) and is unit-tested (3 links for English, none for Hindi).
