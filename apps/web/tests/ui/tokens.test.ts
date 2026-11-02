import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { contrast, PAIRS, readTheme, THEMES } from "../../lib/contrast";

const CSS = readFileSync(path.resolve(__dirname, "../../app/tokens.css"), "utf-8");

describe("design tokens: contrast", () => {
  for (const theme of THEMES) {
    describe(`${theme} theme`, () => {
      const tokens = readTheme(CSS, theme);
      for (const pair of PAIRS) {
        it(`${pair.label} is at least ${pair.min}:1`, () => {
          const ratio = contrast(tokens[pair.fg], tokens[pair.bg]);
          expect(ratio, `${pair.fg} on ${pair.bg} = ${ratio.toFixed(2)}`).toBeGreaterThanOrEqual(pair.min);
        });
      }
      it("has no pure black or pure white page background", () => {
        expect(tokens["--c-bg"].toLowerCase()).not.toBe("#000000");
        expect(tokens["--c-bg"].toLowerCase()).not.toBe("#ffffff");
        expect(tokens["--c-surface-2"].toLowerCase()).not.toBe("#000000");
      });
    });
  }

  it("the Auto dark block and the forced dark block hold identical values", () => {
    const auto = readTheme(CSS, "dark", "auto");
    const forced = readTheme(CSS, "dark", "forced");
    expect(auto).toEqual(forced);
  });

  it("prints the contrast table", () => {
    const rows: string[] = ["theme | pair | ratio | min"];
    for (const theme of THEMES) {
      const tokens = readTheme(CSS, theme);
      for (const p of PAIRS) rows.push(`${theme} | ${p.label} | ${contrast(tokens[p.fg], tokens[p.bg]).toFixed(2)} | ${p.min}`);
    }
    console.log("CONTRAST_TABLE\n" + rows.join("\n"));
    expect(rows.length).toBeGreaterThan(10);
  });
});
