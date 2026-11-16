import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { LEARN_PAIRS } from "../../components/learn/pairs";
import { contrast, readTheme, THEMES } from "../../lib/contrast";

const CSS = readFileSync(path.resolve(__dirname, "../../app/tokens.css"), "utf-8");

describe("learn components: token contrast (light and dark)", () => {
  for (const theme of THEMES) {
    const tokens = readTheme(CSS, theme);
    describe(theme, () => {
      for (const p of LEARN_PAIRS) {
        it(`${p.label}: ${p.fg} on ${p.bg} >= ${p.min}:1`, () => {
          expect(tokens[p.fg], `${p.fg} missing`).toBeTruthy();
          expect(tokens[p.bg], `${p.bg} missing`).toBeTruthy();
          const r = contrast(tokens[p.fg], tokens[p.bg]);
          expect(r, `${p.fg} on ${p.bg} = ${r.toFixed(2)}`).toBeGreaterThanOrEqual(p.min);
        });
      }
    });
  }

  it("prints the table", () => {
    const rows = ["theme | pair | ratio | min"];
    for (const theme of THEMES) {
      const tokens = readTheme(CSS, theme);
      for (const p of LEARN_PAIRS) rows.push(`${theme} | ${p.label} | ${contrast(tokens[p.fg], tokens[p.bg]).toFixed(2)} | ${p.min}`);
    }
    console.log("LEARN_CONTRAST_TABLE\n" + rows.join("\n"));
    expect(rows.length).toBe(1 + THEMES.length * LEARN_PAIRS.length);
  });
});
