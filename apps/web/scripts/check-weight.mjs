#!/usr/bin/env node
/**
 * Bundle weight check — called by `pnpm check:weight` after `pnpm build`.
 * Reads the Next.js build manifest, gzip-measures each JS and CSS chunk,
 * and exits 1 when any budget is exceeded.
 *
 * Budgets (gzip):
 *   JS for the chat route  ≤ 100 KB
 *   CSS (all pages)        ≤  25 KB
 */

import { createReadStream, existsSync, readdirSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { createGzip } from "node:zlib";

const DIST = join(process.cwd(), ".next");
const JS_BUDGET_KB = 100;
const CSS_BUDGET_KB = 25;

if (!existsSync(DIST)) {
  console.error("ERROR: .next/ not found — run `pnpm build` first");
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

/** Resolve a manifest-relative path to an absolute .next/ path. */
function resolve(relativePath) {
  // Paths in manifests are like "static/chunks/…" or "_next/static/…"
  const cleaned = relativePath.startsWith("_next/") ? relativePath.slice(6) : relativePath;
  return join(DIST, cleaned);
}

// ── find chunks for the root chat route ──────────────────────────────────────

let jsFiles = [];

const appManifestPath = join(DIST, "app-build-manifest.json");
const buildManifestPath = join(DIST, "build-manifest.json");

if (existsSync(appManifestPath)) {
  const manifest = JSON.parse(await readFile(appManifestPath, "utf8"));
  // App Router: pages keyed by file path, e.g. "page" or "(root)/page"
  const rootChunks =
    manifest.pages?.["page"] ??
    manifest.pages?.["(root)/page"] ??
    manifest.pages?.["app/page"] ??
    [];
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

// Fallback: all chunks (gives the most conservative total)
if (jsFiles.length === 0) {
  const chunksDir = join(DIST, "static", "chunks");
  if (existsSync(chunksDir)) {
    jsFiles = readdirSync(chunksDir)
      .filter((f) => f.endsWith(".js"))
      .map((f) => join(chunksDir, f));
  }
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

// ── report ────────────────────────────────────────────────────────────────────

console.log("\n=== Bundle weight check ===");
console.log(`JS  (gzip): ${jsTotalKB} KB  budget: ${JS_BUDGET_KB} KB`);
console.log(`CSS (gzip): ${cssTotalKB} KB  budget: ${CSS_BUDGET_KB} KB`);
if (jsResults.length > 0) {
  console.log("\nTop JS chunks:");
  for (const r of jsResults.slice(0, 10)) {
    const kb = (r.gz / 1024).toFixed(1).padStart(6);
    console.log(`  ${kb} KB  ${r.file}`);
  }
}

let failed = false;
if (parseFloat(jsTotalKB) > JS_BUDGET_KB) {
  console.error(`\nFAIL: JS ${jsTotalKB} KB exceeds ${JS_BUDGET_KB} KB budget`);
  failed = true;
}
if (parseFloat(cssTotalKB) > CSS_BUDGET_KB) {
  console.error(`\nFAIL: CSS ${cssTotalKB} KB exceeds ${CSS_BUDGET_KB} KB budget`);
  failed = true;
}
if (!failed) {
  console.log("\nPASS: all budgets met");
}

process.exit(failed ? 1 : 0);
