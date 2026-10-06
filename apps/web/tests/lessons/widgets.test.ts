import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { balanceStart, balanceTilt, goalMet, isBalanced, sideString, snapGraphX } from "@/lib/lessons/widgets";
import type { FunctionGraphWidget, WidgetSpec } from "@/lib/lessons/types";

const DIR = path.resolve(__dirname, "../../../../packages/shared/fixtures/widgets");
const files = readdirSync(DIR).filter((f) => f.endsWith(".json")).sort();

describe("widget goal predicates: shared fixtures give the same answers as Python", () => {
  it("has a fixture per initial widget type", () => {
    expect(files).toEqual(["balance_scale.json", "function_graph.json"]);
  });
  for (const file of files) {
    const data = JSON.parse(readFileSync(path.join(DIR, file), "utf-8"));
    for (const c of data.cases) {
      it(`${data.name}: ${c.name}`, () => {
        expect(goalMet(data.widget as WidgetSpec, c.state)).toBe(c.goal_met);
      });
    }
  }
});

describe("drawing helpers", () => {
  const balance = JSON.parse(readFileSync(path.join(DIR, "balance_scale.json"), "utf-8")).widget;
  const graph = JSON.parse(readFileSync(path.join(DIR, "function_graph.json"), "utf-8"))
    .widget as FunctionGraphWidget;

  it("starts level and writes the equation", () => {
    const start = balanceStart(balance.params);
    expect(isBalanced(start, 4)).toBe(true);
    expect(sideString(start.lb, start.lw)).toBe("2x + 3");
    expect(sideString(start.rb, start.rw)).toBe("11");
    expect(sideString(1, 0)).toBe("x");
    expect(sideString(0, 0)).toBe("0");
    expect(balanceTilt(start, 4)).toBe(0);
    expect(balanceTilt({ ...start, lw: 0 }, 4)).toBeLessThan(0);
  });

  it("snaps a dragged dot to the grid and to the solution", () => {
    expect(snapGraphX(graph.params, 3.93)).toBe(4);
    expect(snapGraphX(graph.params, 1.04)).toBe(1);
    expect(snapGraphX(graph.params, 99)).toBe(8);
    expect(snapGraphX(graph.params, -3)).toBe(0);
  });
});
