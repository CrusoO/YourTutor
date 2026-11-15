import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { AUDIENCE_NAMES, contrast, PAIRS, readAudienceOverrides, readTheme, resolveTokens, SEMANTIC_PAIRS, THEMES } from "../../lib/contrast";
import { AUDIENCES, AUDIENCE_THEMES } from "../../lib/audience";

const TOKENS = readFileSync(path.resolve(__dirname, "../../app/tokens.css"), "utf-8");
const SEMANTIC = readFileSync(path.resolve(__dirname, "../../app/semantic.css"), "utf-8").split(String.fromCharCode(13)).join("");

describe("semantic tokens: every audience, light and dark", () => {
  for (const audience of AUDIENCE_NAMES) {
    for (const theme of THEMES) {
      const tokens = resolveTokens(readTheme(TOKENS, theme), readAudienceOverrides(SEMANTIC, audience, theme), SEMANTIC);
      describe(`${audience} / ${theme}`, () => {
        for (const pair of [...PAIRS, ...SEMANTIC_PAIRS]) {
          it(`${pair.label} (${pair.fg} on ${pair.bg}) is at least ${pair.min}:1`, () => {
            expect(tokens[pair.fg], `${pair.fg} is missing`).toBeTruthy();
            expect(tokens[pair.bg], `${pair.bg} is missing`).toBeTruthy();
            const ratio = contrast(tokens[pair.fg]!, tokens[pair.bg]!);
            expect(ratio, `${audience}/${theme}: ${pair.fg} on ${pair.bg} = ${ratio.toFixed(2)}`).toBeGreaterThanOrEqual(pair.min);
          });
        }
      });
    }
  }

  it("the school theme overrides nothing, so the default look is unchanged", () => {
    expect(readAudienceOverrides(SEMANTIC, "school", "light")).toEqual({});
    expect(readAudienceOverrides(SEMANTIC, "school", "dark")).toEqual({});
    expect(SEMANTIC).not.toMatch(/html[data-audience="school"]/);
  });

  it("every semantic token is an alias of a palette token (no literal colour in the layer)", () => {
    const root = SEMANTIC.slice(SEMANTIC.indexOf(":root {"), SEMANTIC.indexOf("}", SEMANTIC.indexOf(":root {")));
    expect(root).not.toMatch(/#[0-9a-f]{3,6}\b/i);
  });

  it("themes are data: college and work are denser, calmer and have no mascot", () => {
    expect([...AUDIENCES]).toEqual([...AUDIENCE_NAMES]);
    expect(AUDIENCE_THEMES.school).toMatchObject({ density: "regular", mascot: true });
    for (const a of ["college", "work"] as const) expect(AUDIENCE_THEMES[a]).toMatchObject({ tone: "calm", density: "compact", motion: "calm", mascot: false });
  });
});
