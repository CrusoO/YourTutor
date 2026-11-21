# Contrast table (UI-2b)

Generated from `app/tokens.css` by `tests/ui/tokens.test.ts` (WCAG ratios). Every pair meets its minimum in both themes (table refreshed 2026-11-22 from the live test output; the earlier values had drifted); `e2e/teen.spec.ts` re-checks the computed colours and the rendered text on the home, setup, student home, practice and lesson screens.

| pair | minimum | light | dark |
|---|---|---|---|
| text on page | 7:1 | 15.06 | 17.74 |
| text on card | 7:1 | 16.89 | 17.01 |
| text on raised surface | 7:1 | 14.50 | 15.81 |
| muted text on page | 7:1 | 7.38 | 7.89 |
| muted text on card | 7:1 | 8.28 | 7.56 |
| muted text on raised surface | 7:1 | 7.11 | 7.03 |
| text on the flat home page | 7:1 | 15.06 | 17.74 |
| muted text on the flat home page | 7:1 | 7.38 | 7.89 |
| text on a solid home card | 7:1 | 16.89 | 17.14 |
| muted text on a solid home card | 7:1 | 8.28 | 7.62 |
| text on the darkest page zone | 7:1 | 13.87 | 17.85 |
| muted text on the darkest page zone (6.9 measured) | 4.5:1 | 6.80 | 7.94 |
| text on lesson surface | 7:1 | 16.89 | 17.74 |
| muted text on lesson surface | 7:1 | 8.28 | 7.89 |
| accent text on lesson surface | 4.5:1 | 5.42 | 9.59 |
| ok text on lesson surface | 4.5:1 | 6.52 | 9.19 |
| warn text on lesson surface | 4.5:1 | 7.41 | 11.09 |
| input border on lesson surface | 3:1 | 3.84 | 4.22 |
| focus ring on lesson surface | 3:1 | 5.18 | 11.52 |
| button label on accent | 4.5:1 | 5.18 | 7.02 |
| accent text on page | 4.5:1 | 4.83 | 9.59 |
| accent text on card | 4.5:1 | 5.42 | 9.19 |
| accent text on tint | 4.5:1 | 4.53 | 7.23 |
| ok text on its tint | 4.5:1 | 5.69 | 7.63 |
| warn text on its tint | 4.5:1 | 6.60 | 8.65 |
| info text on its tint | 4.5:1 | 5.52 | 7.05 |
| teal text on its tint | 4.5:1 | 5.54 | 6.69 |
| teal text on card | 4.5:1 | 6.37 | 10.07 |
| info text on page | 4.5:1 | 5.98 | 9.38 |
| teal icon on its tint | 3:1 | 5.54 | 6.69 |
| neutral text on its tint | 4.5:1 | 8.38 | 8.51 |
| error text on its tint | 4.5:1 | 5.46 | 5.29 |
| ok text on card | 4.5:1 | 6.52 | 8.81 |
| warn text on card | 4.5:1 | 7.41 | 10.63 |
| info text on card | 4.5:1 | 6.70 | 8.99 |
| error text on card | 4.5:1 | 6.57 | 6.78 |
| input border on page | 3:1 | 3.43 | 4.22 |
| input border on card | 3:1 | 3.84 | 4.05 |
| focus ring on page | 3:1 | 4.62 | 11.52 |
| focus ring on card | 3:1 | 5.18 | 11.04 |
| focus ring on raised surface | 3:1 | 4.44 | 10.26 |
| ok icon on its tint | 3:1 | 5.69 | 7.63 |
| warn icon on its tint | 3:1 | 6.60 | 8.65 |
| info icon on its tint | 3:1 | 5.52 | 7.05 |



## UI-6 P0: candidate colours checked (2026-11-22, computed, nothing changed in the app)

Ratios use the WCAG 2 formula. These are candidates for UI-6 P1; none is applied to `tokens.css` yet.

| pair | minimum | ratio | verdict |
|---|---|---|---|
| white label on light accent `#0b6bd3` (current) | 4.5:1 | 5.18 | passes; a comment in `tokens.css` said 6.6:1, now corrected |
| light accent `#0b6bd3` as text on page `#f6f8fc` | 4.5:1 | 4.87 | passes narrowly; keep for buttons, use the darker link below for long link text |
| proposed light link `#0a5fbd` on page / white | 4.5:1 | 5.84 / 6.20 | passes |
| proposed control border `#7a849b` on white / page | 3:1 | 3.75 / 3.53 | passes |
| current dark text `#f1f4f9` on `#0a0c11` | 7:1 | 17.74 | passes; very bright |
| proposed dark text `#e6e9ef` on `#0b0d12` / card `#161a22` | 7:1 | 15.98 / 14.33 | passes, softer |
| current dark muted `#9ca5b6` on card `#161a22` | 7:1 | 7.03 | passes barely (on a lighter card than the one in use) |
| proposed dark muted `#b8c0ce` on card / page | 7:1 | 9.52 / 10.61 | passes with margin |
| current dark accent `#38b6ff` on card `#161a22` | 4.5:1 | 7.72 | passes |
| proposed dark accent `#6cc4ff` on card; label `#021626` on it | 4.5:1 | 9.11; 9.58 | passes |
| proposed dark control border `#737d90` on card / page | 3:1 | 4.20 / 4.69 | passes |
| mistake `#9c3d00` on `#fde8da` (light); `#ff9a62` on `#33190c` (dark) | 4.5:1 | 5.75; 7.82 | passes |
| mastered `#5b3aa8` on `#ece6fb` (light); `#b9a2ff` on `#231a3d` (dark) | 4.5:1 | 6.61; 7.52 | passes |

Not measured: APCA scores, and the pairs on real devices. Contrast says nothing about how a font looks, which is why P0 also needs native readers for the font specimens.

### Font file sizes (2026-11-22, WOFF2 from the Google Fonts service, per file)

| font | Latin | Devanagari | note |
|---|---|---|---|
| Geist (self-hosted today) | 12.5 KB per weight | none | 5 weights in `public/fonts`; Inter is 23.7 and 24.5 KB per weight |
| Noto Sans Devanagari 400 (today's Hindi fallback) | 9.9 KB | 48.7 KB | the variable file is 24.5 and 117.2 KB |
| Google Sans, variable 400 to 700 (candidate) | 35.2 KB | 48.9 KB | one file per script covers all weights |
| Source Serif 4 400 (optional Book) | 19.6 KB | none | |
| Noto Serif Devanagari 400 (optional Book) | 11.6 KB | 49.8 KB | |
| Atkinson Hyperlegible Next 400 (single weight) | 11.8 KB | none | |
| Atkinson Hyperlegible Next, variable 200 to 800 (owner-chosen interface font, 2026-11-22) | 33.2 KB | none | one file covers all weights; Hindi and Nepali keep Noto Sans Devanagari |
| Mukta 400 | 20.0 KB | 97.0 KB | heavier than the others |

Update 2026-11-22: the owner chose Atkinson Hyperlegible Next (Easy-read) as the interface font, so Google Sans is no longer a candidate. One Atkinson variable file (33 KB) plus today's Noto Sans Devanagari (49 KB) is lighter than today's five Geist weights (62 KB) plus Noto Sans Devanagari.

Earlier reading (Google Sans, kept for the record): one Google Sans variable file per script (35 and 49 KB) costs about the same as today's Geist weights plus Noto Sans Devanagari (62 and 49 KB) and removes the two-family mismatch. The 0 KB font rule on lesson screens still needs an owner decision (cached from earlier screens, or an approved exception). These are single-file transfer sizes, not a full page measurement.
