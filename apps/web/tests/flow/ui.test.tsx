import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ReadAloud from "@/components/flow/ReadAloud";
import { bodyClasses, readAloudOn, speak, type BandUi } from "@/lib/ui";

afterEach(cleanup);

const primary: BandUi = { band_id: "primary", read_aloud_default: true, target_size: "large", choice: "two_options" };
const upper: BandUi = { band_id: "upper_secondary", read_aloud_default: false, target_size: "normal", choice: "plan_editing" };

describe("band styling", () => {
  it("turns the band settings into body classes", () => {
    expect(bodyClasses(primary)).toEqual(["band-primary", "target-large"]);
    expect(bodyClasses(upper)).toEqual(["band-upper_secondary", "target-normal"]);
    expect(bodyClasses(undefined)).toEqual([]);
  });

  it("reads aloud by the band default until the student chooses", () => {
    expect(readAloudOn(primary, null)).toBe(true);
    expect(readAloudOn(upper, null)).toBe(false);
    expect(readAloudOn(primary, "off")).toBe(false);
    expect(readAloudOn(upper, "on")).toBe(true);
    expect(readAloudOn(undefined, null)).toBe(false);
  });
});

describe("speak", () => {
  it("cancels what is playing, then speaks in the student's language", () => {
    vi.stubGlobal("SpeechSynthesisUtterance", function (this: { text: string }, text: string) {
      this.text = text;
    });
    const synth = { cancel: vi.fn(), speak: vi.fn() };
    expect(speak("What is x?", "en", synth as unknown as SpeechSynthesis)).toBe(true);
    expect(synth.cancel).toHaveBeenCalledTimes(1);
    expect(synth.speak).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });

  it("does nothing without speech support or text", () => {
    expect(speak("hello", "en", undefined)).toBe(false);
    expect(speak("   ", "en", { cancel: vi.fn(), speak: vi.fn() } as unknown as SpeechSynthesis)).toBe(false);
  });
});

describe("ReadAloud", () => {
  function stubSpeech() {
    const synth = { cancel: vi.fn(), speak: vi.fn() };
    vi.stubGlobal("speechSynthesis", synth);
    vi.stubGlobal("SpeechSynthesisUtterance", function (this: { text: string }, text: string) {
      this.text = text;
    });
    return synth;
  }

  it("speaks the text when the band default is on and lets the student turn it off", async () => {
    const synth = stubSpeech();
    render(<ReadAloud text="What is x?" lang="en" ui={primary} />);
    expect(synth.speak).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole("button", { name: /read aloud/i }));
    expect(screen.getByRole("button", { name: /read aloud/i })).toHaveAttribute("aria-pressed", "false");
    vi.unstubAllGlobals();
  });

  it("stays quiet for a band that is off by default, and plays on a tap", async () => {
    const synth = stubSpeech();
    render(<ReadAloud text="What is x?" lang="en" ui={upper} />);
    expect(synth.speak).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /listen/i }));
    expect(synth.speak).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });

  it("renders nothing when the browser cannot speak", () => {
    vi.stubGlobal("speechSynthesis", undefined);
    const { container } = render(<ReadAloud text="What is x?" lang="en" ui={primary} />);
    expect(container).toBeEmptyDOMElement();
    vi.unstubAllGlobals();
  });
});
