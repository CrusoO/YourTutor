// Page-weight budget (UI standard: 150 KB per screen, audio excluded), checked from the build output.
// Run after `next build`:  node scripts/check-weight.mjs
// For every app route it adds the gzip size of the JavaScript and CSS the page loads, and, separately, the font files of each language, and fails if a product route is over budget. /dev routes are exempt.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join } from "node:path";

const BUDGET_KB = Number(process.env.WEIGHT_BUDGET_KB || 150);
// Documented exception (PLAN.md Decisions, "Page weight of the home"): React and Next are about 103 KB
// before any code and assistant-ui adds about 100 KB, so the chat home cannot fit 150 KB. Its limit is
// the measured value plus a little headroom, so it can only shrink unnoticed, never grow.
// UI-5 (approved ceilings, docs/FONT_BUDGET.md): fonts are counted on their own, so the JS and CSS limit of the home is
// 255 KB (measured 249.7), English fonts 70 KB (66.7) and Hindi fonts 125 KB (122.3). Raising any of them needs an explicit
// change here, in the same pull request, with the reason.
const ROUTE_BUDGET_KB = { "/": Number(process.env.WEIGHT_HOME_BUDGET_KB || 255) };
const FONT_BUDGET_KB = { english: Number(process.env.WEIGHT_FONTS_EN_KB || 70), hindi: Number(process.env.WEIGHT_FONTS_HI_KB || 125) };
const FONT_SETS = {
  english: ["geist-mono-latin-300", "geist-mono-latin-500", "inter-latin-400", "inter-latin-600"],
  hindi: ["noto-sans-devanagari-deva-400", "noto-sans-devanagari-deva-500", "noto-sans-devanagari-latin-400", "noto-sans-devanagari-latin-500"],
};
const NEXT = ".next";
const manifestPath = join(NEXT, "app-build-manifest.json");
if (!existsSync(manifestPath)) {
  console.error("No build output: run `next build` first.");
  process.exit(2);
}

const gz = (file) => gzipSync(readFileSync(join(NEXT, file)), { level: 9 }).length / 1024;
const pages = JSON.parse(readFileSync(manifestPath, "utf8")).pages;

// Fonts are self-hosted in public/fonts. Each language loads only its own set (a test checks that English never fetches
// a Devanagari file); they are measured as transferred (woff2 is already compressed) and are not part of the JS and CSS number.
const fontKB = (names) => names.reduce((sum, n) => sum + readFileSync(join("public", "fonts", `${n}.woff2`)).length / 1024, 0);

const rows = [];
for (const [page, files] of Object.entries(pages)) {
  const route = page.replace(/\/page$/, "") || "/";
  if (route.startsWith("/dev") || route.startsWith("/api") || route.includes("not-found")) continue;
  const assets = [...new Set(files)].filter((f) => /\.(js|css)$/.test(f));
  let kb = assets.reduce((sum, f) => sum + gz(f), 0);
  rows.push({ route, kb: Math.round(kb * 10) / 10 });
}
rows.sort((a, b) => b.kb - a.kb);
let failed = 0;
for (const { route, kb } of rows) {
  const limit = ROUTE_BUDGET_KB[route] ?? BUDGET_KB;
  const over = kb > limit;
  if (over) failed += 1;
  console.log(`${over ? "OVER " : "ok   "} ${String(kb).padStart(7)} KB  ${route}${limit !== BUDGET_KB ? `  (limit ${limit})` : ""}`);
}
console.log(`budget ${BUDGET_KB} KB per screen (gzip JS and CSS; fonts are counted separately below)`);
for (const [lang, names] of Object.entries(FONT_SETS)) {
  const kb = Math.round(fontKB(names) * 10) / 10;
  const limit = FONT_BUDGET_KB[lang];
  const over = kb > limit;
  if (over) failed += 1;
  console.log(`${over ? "OVER " : "ok   "} ${String(kb).padStart(7)} KB  fonts, ${lang}  (limit ${limit})`);
}
if (failed) {
  console.error(`${failed} budget line(s) over`);
  process.exit(1);
}
