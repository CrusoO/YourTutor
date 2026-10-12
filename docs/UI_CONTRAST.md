# Contrast table (UI-2b)

Generated from `app/tokens.css` by `tests/ui/tokens.test.ts` (WCAG ratios). Every pair meets its minimum in both themes; `e2e/teen.spec.ts` re-checks the computed colours and the rendered text on the home, setup, student home, practice and lesson screens.

| pair | minimum | light | dark |
|---|---|---|---|
| text on page | 7:1 | 16.52 | 16.66 |
| text on card | 7:1 | 17.69 | 15.04 |
| text on raised surface | 7:1 | 15.57 | 13.58 |
| muted text on page | 7:1 | 7.66 | 8.76 |
| muted text on card | 7:1 | 8.20 | 7.91 |
| muted text on raised surface | 7:1 | 7.21 | 7.14 |
| button label on accent | 4.5:1 | 6.29 | 5.37 |
| accent text on page | 4.5:1 | 9.28 | 12.19 |
| accent text on card | 4.5:1 | 9.93 | 11.01 |
| accent text on tint | 4.5:1 | 8.29 | 8.81 |
| ok text on its tint | 4.5:1 | 5.69 | 7.12 |
| warn text on its tint | 4.5:1 | 6.60 | 7.89 |
| info text on its tint | 4.5:1 | 5.52 | 7.05 |
| teal text on its tint | 4.5:1 | 5.54 | 6.69 |
| teal text on card | 4.5:1 | 6.37 | 9.26 |
| info text on page | 4.5:1 | 6.26 | 9.16 |
| teal icon on its tint | 3:1 | 5.54 | 6.69 |
| neutral text on its tint | 4.5:1 | 8.38 | 8.51 |
| error text on its tint | 4.5:1 | 5.46 | 5.29 |
| ok text on card | 4.5:1 | 6.52 | 9.82 |
| warn text on card | 4.5:1 | 7.41 | 10.32 |
| info text on card | 4.5:1 | 6.70 | 8.27 |
| error text on card | 4.5:1 | 6.57 | 6.23 |
| input border on page | 3:1 | 3.43 | 4.27 |
| input border on card | 3:1 | 3.67 | 3.86 |
| focus ring on page | 3:1 | 5.87 | 9.57 |
| focus ring on card | 3:1 | 6.29 | 8.64 |
| focus ring on raised surface | 3:1 | 5.53 | 7.81 |
| ok icon on its tint | 3:1 | 5.69 | 7.12 |
| warn icon on its tint | 3:1 | 6.60 | 7.89 |
| info icon on its tint | 3:1 | 5.52 | 7.05 |

Deviation from the requested values: the light muted text is `#464E6B` (requested `#4A5270`), because `#4A5270` on the raised surface `#EEF0FA` is 6.76:1, below the 7:1 required for muted text.
