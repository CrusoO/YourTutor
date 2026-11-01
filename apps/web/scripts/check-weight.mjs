#!/usr/bin/env node
/**
 * Bundle weight check — called by `pnpm check:weight` after `pnpm build`.
 * Reads the Next.js build manifest, gzip-measures each JS and CSS chunk,
 * and exits 1 when any budget is exceeded.
 *
 * Budgets (gzip):
 *   JS for the homepage route  ≤ 125 KB
 *   CSS (all pages)            ≤  25 KB
 *   Homepage JS + all CSS      ≤ 150 KB
 */

import { createReadStream, existsSync, readdirSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { createGzip } from "node:zlib";

const DIST = join(process.cwd(), ".next");
const JS_BUDGET_KB = 125;
const CSS_BUDGET_KB = 25;
const PAGE_BUDGET_KB = 150;

if (!existsSync(DIST)) {
  console.error("ERROR: .next/ not found — run the production build first");
  process.exit(1);
}

async function gzipSize(filePath) {
  return new Promise((resolve, reject) => {
    let size = 0;
    createReadStream(filePath)
      .pipe(createGzip({ level: 9 }))
      .on("data", (c) => {
        size += c.length;
      })
      .on("end", () => resolve(size))
      .on("error", reject);
  });
}

/** Resolve a manifest-relative path to an absolute build-output path. */
function resolve(relativePath) {
  // Paths in manifests are like "static/chunks/…" or "_next/static/…"
  const cleaned = relativePath.startsWith("_next/") ? relativePath.slice(6) : relativePath;
  return join(DIST, cleaned);
}

// ── find chunks for the homepage route ────────────────────────────────────────

let jsFiles = [];

const appManifestPath = join(DIST, "app-build-manifest.json");
const buildManifestPath = join(DIST, "build-manifest.json");

if (existsSync(appManifestPath)) {
  const manifest = JSON.parse(await readFile(appManifestPath, "utf8"));
  // App Router: keys vary by Next version; current builds use "/page".
  const rootChunks = [
    manifest.pages?.["/page"],
    manifest.pages?.["page"],
    manifest.pages?.["(root)/page"],
    manifest.pages?.["app/page"],
  ].find((chunks) => Array.isArray(chunks) && chunks.length > 0) ?? [];
  jsFiles = rootChunks
    .filter((f) => f.endsWith(".js"))
    .map(resolve)
    .filter(existsSync);
}

if (jsFiles.length === 0 && existsSync(buildManifestPath)) {
  const manifest = JSON.parse(await readFile(buildManifestPath, "utf8"));
  const rootChunks = manifest.pages?.["/"] ?? [];
  jsFiles = rootChunks
    .filter((f) => f.endsWith(".js"))
    .map(resolve)
    .filter(existsSync);
}

if (jsFiles.length === 0) {
  console.error("ERROR: homepage JS chunks were not found in the Next.js build manifests");
  process.exit(1);
}

// ── CSS ───────────────────────────────────────────────────────────────────────

const cssDir = join(DIST, "static", "css");
const cssFiles = existsSync(cssDir)
  ? readdirSync(cssDir)
      .filter((f) => f.endsWith(".css"))
      .map((f) => join(cssDir, f))
  : [];

// ── measure ───────────────────────────────────────────────────────────────────

const jsResults = [];
let jsTotalBytes = 0;
for (const f of jsFiles) {
  const gz = await gzipSize(f);
  jsTotalBytes += gz;
  jsResults.push({ file: f.replace(process.cwd(), "").replace(/\\/g, "/"), gz });
}
jsResults.sort((a, b) => b.gz - a.gz);

let cssTotalBytes = 0;
for (const f of cssFiles) {
  cssTotalBytes += await gzipSize(f);
}

const jsTotalKB = (jsTotalBytes / 1024).toFixed(1);
const cssTotalKB = (cssTotalBytes / 1024).toFixed(1);
const pageTotalBytes = jsTotalBytes + cssTotalBytes;
const pageTotalKB = (pageTotalBytes / 1024).toFixed(1);

// ── report ────────────────────────────────────────────────────────────────────

console.log("\n=== Bundle weight check ===");
console.log(`JS  (gzip): ${jsTotalKB} KB  budget: ${JS_BUDGET_KB} KB`);
console.log(`CSS (gzip): ${cssTotalKB} KB  budget: ${CSS_BUDGET_KB} KB`);
console.log(`Page (gzip): ${pageTotalKB} KB  budget: ${PAGE_BUDGET_KB} KB`);
if (jsResults.length > 0) {
  console.log("\nTop JS chunks:");
  for (const r of jsResults.slice(0, 10)) {
    const kb = (r.gz / 1024).toFixed(1).padStart(6);
    console.log(`  ${kb} KB  ${r.file}`);
  }
}

let failed = false;
if (jsTotalBytes > JS_BUDGET_KB * 1024) {
  console.error(`\nFAIL: JS ${jsTotalKB} KB exceeds ${JS_BUDGET_KB} KB budget`);
  failed = true;
}
if (cssTotalBytes > CSS_BUDGET_KB * 1024) {
  console.error(`\nFAIL: CSS ${cssTotalKB} KB exceeds ${CSS_BUDGET_KB} KB budget`);
  failed = true;
}
if (pageTotalBytes > PAGE_BUDGET_KB * 1024) {
  console.error(`\nFAIL: page ${pageTotalKB} KB exceeds ${PAGE_BUDGET_KB} KB budget`);
  failed = true;
}
if (!failed) {
  console.log("\nPASS: all budgets met");
}

process.exit(failed ? 1 : 0);
