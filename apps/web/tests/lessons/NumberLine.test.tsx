import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import NumberLine from "@/components/lessons/NumberLine";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const slider = () => screen.getByRole("slider");
const btn = (name: string | RegExp) => screen.getByRole("button", { name });
const val = () => Number(slider().getAttribute("aria-valuenow"));
const MINUS = "−";

describe("NumberLine: safe range", () => {
  it("refuses numbers it cannot draw instead of drawing nonsense", () => {
    render(<NumberLine start={18} delta={9} />);
    expect(screen.getByRole("alert")).toHaveTextContent("only shows whole numbers");
    expect(screen.queryByRole("slider")).toBeNull();
    cleanup();
    render(<NumberLine start={1.5} delta={2} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    cleanup();
    render(<NumberLine start={4} delta={0} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

describe("NumberLine: predict", () => {
  it("opens on the start and hides the answer before the guess", () => {
    render(<NumberLine start={-8} delta={5} reducedMotion narrate={false} />);
    expect(val()).toBe(-8);
    expect(screen.getByTestId("nl-start")).toHaveTextContent(`${MINUS}8`);
    expect(screen.getByTestId("nl-move")).toHaveTextContent("+5");
    expect(screen.getByTestId("nl-result")).toHaveTextContent("?");
    expect(screen.queryByText("answer")).toBeNull();
    expect(btn("That is my guess")).toBeDisabled();
  });

  it("moves by keyboard: arrows, page keys, Home and End, never past the drawn line", async () => {
    render(<NumberLine start={-8} delta={5} reducedMotion narrate={false} />);
    slider().focus();
    await userEvent.keyboard("{ArrowRight}{ArrowRight}");
    expect(val()).toBe(-6);
    await userEvent.keyboard("{ArrowLeft}");
    expect(val()).toBe(-7);
    await userEvent.keyboard("{PageUp}");
    expect(val()).toBe(-2);
    await userEvent.keyboard("{End}");
    const max = val();
    await userEvent.keyboard("{ArrowRight}");
    expect(val()).toBe(max);
    await userEvent.keyboard("{Home}");
    const min = val();
    await userEvent.keyboard("{ArrowLeft}");
    expect(val()).toBe(min);
    expect(min).toBeLessThanOrEqual(-13); // the other-way guess is always reachable
    expect(btn("That is my guess")).toBeEnabled();
  });

  it("moves by the +1 / -1 step buttons", async () => {
    render(<NumberLine start={-8} delta={5} reducedMotion narrate={false} />);
    await userEvent.click(btn("+1 step"));
    await userEvent.click(btn("+1 step"));
    await userEvent.click(btn(`${MINUS}1 step`));
    expect(val()).toBe(-7);
  });

  it("commits a tapped point on the line", () => {
    render(<NumberLine start={-8} delta={5} reducedMotion narrate={false} />);
    const svg = screen.getByRole("group", { name: /Number line/ });
    svg.getBoundingClientRect = () => ({ left: 0, top: 0, width: 340, height: 150, right: 340, bottom: 150, x: 0, y: 0, toJSON: () => ({}) });
    fireEvent.pointerDown(svg, { clientX: 340, clientY: 80, pointerId: 1 });
    expect(val()).toBeGreaterThan(-8);
    fireEvent.pointerUp(svg, { pointerId: 1 });
  });

  it("has an accessible name, value text in words and a focusable slider", () => {
    render(<NumberLine start={-8} delta={5} reducedMotion narrate={false} />);
    expect(screen.getByRole("group", { name: `Number line: ${MINUS}8 + 5` })).toBeInTheDocument();
    expect(slider()).toHaveAttribute("aria-label", "Your guess");
    expect(slider()).toHaveAttribute("aria-valuetext", "minus eight");
    expect(slider()).toHaveAttribute("tabindex", "0");
    expect(screen.getByText(/Add \(\+\): move right/)).toBeInTheDocument();
    expect(screen.getByText(/Subtract \(.\): move left/)).toBeInTheDocument();
  });

  it("says right at once for a correct guess (check mode)", async () => {
    const onLocked = vi.fn();
    render(<NumberLine start={-9} delta={4} after="check" reducedMotion narrate={false} onLocked={onLocked} />);
    for (let i = 0; i < 4; i++) await userEvent.click(btn("+1 step"));
    await userEvent.click(btn("That is my guess"));
    expect(screen.getByTestId("nl-reason")).toHaveTextContent(`Yes. ${MINUS}9 + 4 lands on ${MINUS}5.`);
    expect(onLocked).toHaveBeenCalledWith(expect.objectContaining({ correct: true, guess: -5 }));
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("shows a wrong guess against the true landing with the reason in plain words", async () => {
    render(<NumberLine start={-8} delta={5} after="check" reducedMotion narrate={false} />);
    for (let i = 0; i < 5; i++) await userEvent.click(btn(`${MINUS}1 step`));
    await userEvent.click(btn("That is my guess"));
    const reason = screen.getByTestId("nl-reason");
    expect(reason).toHaveTextContent("same number of steps, but left");
    expect(reason).toHaveTextContent(`lands on ${MINUS}3`);
    expect(reason.textContent?.toLowerCase()).not.toMatch(/wrong|incorrect|mistake/);
    expect(screen.getByText("answer")).toBeInTheDocument();
    expect(screen.getByText("your guess")).toBeInTheDocument();
    await userEvent.click(btn("Try again"));
    expect(val()).toBe(-8);
    expect(btn("That is my guess")).toBeDisabled();
  });

  it("hold mode reports each move and never reveals the answer", async () => {
    const onGuess = vi.fn();
    render(<NumberLine start={-6} delta={15} after="hold" reducedMotion narrate={false} onGuess={onGuess} />);
    expect(screen.queryByRole("button", { name: "That is my guess" })).toBeNull();
    await userEvent.click(btn("+1 step"));
    expect(onGuess).toHaveBeenLastCalledWith(-5);
    expect(screen.getByRole("status")).toHaveTextContent("Guess saved");
    expect(screen.getByTestId("nl-result")).toHaveTextContent("?");
  });

  it("follows a choice tapped elsewhere (externalGuess)", () => {
    const { rerender } = render(<NumberLine start={-6} delta={15} after="hold" reducedMotion narrate={false} externalGuess={null} />);
    rerender(<NumberLine start={-6} delta={15} after="hold" reducedMotion narrate={false} externalGuess={9} />);
    expect(val()).toBe(9);
  });
});

describe("NumberLine: reveal", () => {
  it("hops one unit at a time, announcing each hop and updating the numbers", () => {
    vi.useFakeTimers();
    render(<NumberLine start={-8} delta={5} mode="reveal" narrate={false} reducedMotion={false} hopMs={100} />);
    expect(screen.queryByRole("slider")).toBeNull();
    const live = screen.getByTestId("nl-live");
    expect(live).toHaveAttribute("aria-live", "polite");
    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(live).toHaveTextContent("Hop 1 of 5: minus seven.");
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}7`);
    expect(document.querySelectorAll("[data-hop]")).toHaveLength(1);
    for (let i = 0; i < 4; i++) act(() => void vi.advanceTimersByTime(100));
    expect(live).toHaveTextContent("Hop 5 of 5: minus three. You land on minus three.");
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}3`);
    expect(document.querySelectorAll("[data-hop]")).toHaveLength(5);
    expect(screen.getByText(`${MINUS}8 + 5 = ${MINUS}3`)).toBeInTheDocument();
    expect(btn("Move it yourself")).toBeInTheDocument();
  });

  it("locks in a prediction, then hops, and compares a wrong guess with the landing", () => {
    vi.useFakeTimers();
    render(<NumberLine start={-8} delta={5} narrate={false} reducedMotion={false} hopMs={50} />);
    for (let i = 0; i < 5; i++) fireEvent.click(btn(`${MINUS}1 step`));
    fireEvent.click(btn("That is my guess"));
    for (let i = 0; i < 8; i++) act(() => void vi.advanceTimersByTime(50));
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}3`);
    expect(screen.getByTestId("nl-reason")).toHaveTextContent(`${MINUS}13 is the same number of steps, but left`);
  });

  it("shows a prior guess from the Guess step against the answer", () => {
    render(<NumberLine start={-6} delta={15} mode="reveal" autoPlay={false} priorGuess={-9} narrate={false} reducedMotion />);
    fireEvent.click(btn("Jump to the answer"));
    expect(screen.getByTestId("nl-reason")).toHaveTextContent("lands on 9");
  });
});

describe("NumberLine: reduced motion", () => {
  it("shows the whole path as still arrows and steps by button, with no timers", () => {
    vi.useFakeTimers();
    render(<NumberLine start={-8} delta={5} mode="reveal" reducedMotion narrate={false} hopMs={10} />);
    expect(document.querySelectorAll("[data-hop]")).toHaveLength(5);
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}8`);
    fireEvent.click(btn("Next hop"));
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}7`);
    expect(screen.getByTestId("nl-live")).toHaveTextContent("Hop 1 of 5");
    fireEvent.click(btn("Back one hop"));
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}8`);
    fireEvent.click(btn("Jump to the answer"));
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}3`);
  });

  it("reads the media query when the prop is not given", () => {
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("reduce"), media: q, addEventListener() {}, removeEventListener() {} }));
    render(<NumberLine start={-8} delta={5} mode="reveal" narrate={false} />);
    expect(document.querySelectorAll("[data-hop]")).toHaveLength(5);
    expect(btn("Next hop")).toBeInTheDocument();
  });
});

describe("NumberLine: explore", () => {
  it("moves with the step buttons and the slider and shows the move as a signed number", () => {
    render(<NumberLine start={3} delta={-7} mode="explore" reducedMotion narrate={false} />);
    expect(screen.getByTestId("nl-move")).toHaveTextContent("0");
    fireEvent.click(btn("+1 step"));
    expect(screen.getByTestId("nl-move")).toHaveTextContent("+1");
    fireEvent.click(btn(`${MINUS}1 step`));
    fireEvent.click(btn(`${MINUS}1 step`));
    expect(screen.getByTestId("nl-move")).toHaveTextContent(`${MINUS}1`);
    expect(screen.getByTestId("nl-result")).toHaveTextContent("2");
    const range = screen.getByLabelText("Move the dot along the line", { selector: "input" });
    fireEvent.change(range, { target: { value: "-4" } });
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}4`);
    expect(screen.getByTestId("nl-move")).toHaveTextContent(`${MINUS}7`);
  });
});

describe("NumberLine: narration through Read aloud", () => {
  function stubSpeech() {
    const synth = { cancel: vi.fn(), speak: vi.fn() };
    vi.stubGlobal("speechSynthesis", synth);
    vi.stubGlobal("SpeechSynthesisUtterance", function (this: { text: string }, text: string) {
      this.text = text;
    });
    return synth;
  }

  it("reads the setup before the guess and the full hop script after, never a model call", async () => {
    const synth = stubSpeech();
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    render(<NumberLine start={-8} delta={5} reducedMotion />);
    await userEvent.click(screen.getByRole("button", { name: "Listen" }));
    expect(synth.speak.mock.calls.at(-1)?.[0].text).toBe(
      "Start at minus eight. Add five: five steps to the right. Where do you think you land?",
    );
    fireEvent.click(btn("+1 step"));
    fireEvent.click(btn("That is my guess"));
    await userEvent.click(screen.getByRole("button", { name: "Listen" }));
    expect(synth.speak.mock.calls.at(-1)?.[0].text).toBe(
      "Start at minus eight. Add five: five steps to the right. Minus seven, minus six, minus five, minus four, minus three. You land on minus three.",
    );
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("offers no speech controls when the browser cannot speak, and the text is still on screen", () => {
    vi.stubGlobal("speechSynthesis", undefined);
    render(<NumberLine start={-8} delta={5} mode="reveal" reducedMotion />);
    expect(screen.queryByRole("button", { name: "Listen" })).toBeNull();
    fireEvent.click(btn("Jump to the answer"));
    expect(within(screen.getByTestId("number-line")).getByText(`${MINUS}8 + 5 = ${MINUS}3`)).toBeInTheDocument();
  });
});
