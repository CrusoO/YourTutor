/** Footer disclaimer (fixed wording from the owner's rights research, 2026-11-11; no board or
 *  publisher names since 2026-11-24, on the owner's say-so). Kept in its own
 *  tiny module so the landing page can show it without pulling in the whole copy table
 *  (lib/messages.ts re-exports it as `independenceFooter`); mirrors apps/api/app/content/labels.py. */
export const INDEPENDENCE_FOOTER =
  "Brownie is independent and is not affiliated with, endorsed by or approved by any exam board or textbook publisher. Official papers: cbseacademic.nic.in.";
