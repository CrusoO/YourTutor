import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { applyAudience, AUDIENCE_KEY, resolveAudience } from "../../lib/audience";
import { saveUi } from "../../lib/ui";
import { useAudience } from "../../lib/useAudience";

const ATTRS = ["data-audience", "data-density", "data-mascot", "data-motion"];
function reset() {
  for (const a of ATTRS) document.documentElement.removeAttribute(a);
  window.localStorage.clear();
  window.sessionStorage.clear();
}
beforeEach(reset);
afterEach(() => {
  cleanup();
  reset();
});

describe("resolveAudience", () => {
  it("is school by default and for school grade bands", () => {
    expect(resolveAudience({})).toBe("school");
    expect(resolveAudience({ bandId: "g9-10" })).toBe("school");
    expect(resolveAudience({ stored: "nonsense", bandId: null })).toBe("school");
  });
  it("uses the stored choice first, then the grade band", () => {
    expect(resolveAudience({ stored: "work", bandId: "college-1" })).toBe("work");
    expect(resolveAudience({ bandId: "college-1" })).toBe("college");
    expect(resolveAudience({ bandId: "adult-learner" })).toBe("work");
  });
});

describe("applyAudience", () => {
  it("sets the axes for college and leaves motion reduce alone", () => {
    const root = document.documentElement;
    applyAudience("college");
    expect(root.getAttribute("data-audience")).toBe("college");
    expect(root.getAttribute("data-density")).toBe("compact");
    expect(root.getAttribute("data-mascot")).toBe("off");
    expect(root.getAttribute("data-motion")).toBe("calm");
    root.setAttribute("data-motion", "reduce");
    applyAudience("work");
    expect(root.getAttribute("data-motion")).toBe("reduce");
    applyAudience("school");
    expect(root.getAttribute("data-motion")).toBe("reduce");
    expect(root.getAttribute("data-mascot")).toBe("on");
  });
  it("school clears a calm motion left by another audience", () => {
    applyAudience("work");
    applyAudience("school");
    expect(document.documentElement.hasAttribute("data-motion")).toBe(false);
    expect(document.documentElement.getAttribute("data-density")).toBe("regular");
  });
});

describe("useAudience", () => {
  it("defaults to school and writes the school attributes", () => {
    const { result } = renderHook(() => useAudience());
    expect(result.current.audience).toBe("school");
    expect(result.current.theme.mascot).toBe(true);
    expect(document.documentElement.getAttribute("data-audience")).toBe("school");
  });
  it("reads a stored choice", () => {
    window.localStorage.setItem(AUDIENCE_KEY, "college");
    const { result } = renderHook(() => useAudience());
    expect(result.current.audience).toBe("college");
    expect(document.documentElement.getAttribute("data-mascot")).toBe("off");
  });
  it("follows the grade band when the student signs in", () => {
    const { result } = renderHook(() => useAudience());
    expect(result.current.audience).toBe("school");
    act(() => saveUi({ band_id: "adult-learner", read_aloud_default: false, target_size: "normal", choice: "x" }));
    expect(result.current.audience).toBe("work");
    expect(document.documentElement.getAttribute("data-density")).toBe("compact");
  });
});
