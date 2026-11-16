import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AnswerGroup,
  AnswerOption,
  BottomTabBar,
  ConfidenceRow,
  ContinueCard,
  EmptyState,
  FeedbackCard,
  HintLadder,
  IDontKnowButton,
  LEARN_COPY_EN as C,
  MathText,
  ProgressBar,
  QuestionCard,
  SkeletonCard,
  TopicChip,
  TrustChip,
  TRUST_LABELS,
  isCurrentTab,
  lineHeightFor,
  trustChipVisible,
} from "@/components/learn";

afterEach(cleanup);

const CONF = [
  { value: "guess", label: C.confidence.guessing },
  { value: "think", label: C.confidence.thinkSo },
  { value: "sure", label: C.confidence.sure },
] as const;
const hintLabels = { ...C.hint, hintTitle: (n: number, t: number) => `Hint ${n} of ${t}` };

describe("QuestionCard", () => {
  it("renders stem, equation with superscript, spoken label and figure slot", () => {
    render(<QuestionCard label="Q" stem="Solve." equation="x^2 + 5x = 0" equationLabel="x squared plus 5 x equals 0" figure={<i data-testid="fig" />} />);
    expect(screen.getByRole("region", { name: "Q" })).toBeInTheDocument();
    expect(screen.getByTestId("question-stem")).toHaveTextContent("Solve.");
    const eq = screen.getByRole("math", { name: "x squared plus 5 x equals 0" });
    expect(eq.querySelector("sup")).toHaveTextContent("2");
    expect(screen.getByTestId("fig")).toBeInTheDocument();
  });
  it("accepts a node as the equation and shows a loading state", () => {
    const { rerender } = render(<QuestionCard label="Q" stem="s" equation={<b data-testid="own" />} />);
    expect(screen.getByTestId("own")).toBeInTheDocument();
    rerender(<QuestionCard label="Q" stem="s" loading />);
    expect(screen.getByRole("region")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByTestId("question-stem")).toBeNull();
  });
  it("MathText handles subscripts and bracketed exponents", () => {
    const { container } = render(<MathText text="a_1 + x^(n+1)" />);
    expect(container.querySelector("sub")).toHaveTextContent("1");
    expect(container.querySelector("sup")).toHaveTextContent("n+1");
  });
});

function Group({ initial = "" }: { initial?: string }) {
  const [v, setV] = useState(initial);
  return (
    <AnswerGroup label="Pick">
      {["a", "b", "c"].map((x) => (
        <AnswerOption key={x} name="g" value={x} selected={v === x} onSelect={setV}>
          option {x}
        </AnswerOption>
      ))}
    </AnswerGroup>
  );
}

describe("AnswerOption", () => {
  it("is a radiogroup; arrow keys move and select, Space selects", async () => {
    render(<Group initial="a" />);
    expect(screen.getByRole("radiogroup", { name: "Pick" })).toBeInTheDocument();
    const [a, b, c] = screen.getAllByRole("radio");
    expect(a).toBeChecked();
    a.focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(b).toBeChecked();
    expect(b).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(c).toBeChecked();
    await userEvent.keyboard("{ArrowUp}");
    expect(b).toBeChecked();
  });
  it("click selects and calls onSelect with the value", async () => {
    const onSelect = vi.fn();
    render(<AnswerOption name="x" value="v" onSelect={onSelect}>text</AnswerOption>);
    await userEvent.click(screen.getByText("text"));
    expect(onSelect).toHaveBeenCalledWith("v");
  });
  it("selected, correct, look-again, disabled and loading states", () => {
    render(
      <AnswerGroup label="g">
        <AnswerOption name="s" value="1" selected>sel</AnswerOption>
        <AnswerOption name="s" value="2" state="correct" stateLabel={C.correct}>ok</AnswerOption>
        <AnswerOption name="s" value="3" state="look-again" stateLabel={C.lookAgain}>again</AnswerOption>
        <AnswerOption name="s" value="4" disabled>off</AnswerOption>
        <AnswerOption name="s" value="5" loading>wait</AnswerOption>
      </AnswerGroup>,
    );
    const states = Array.from(document.querySelectorAll("label")).map((l) => l.getAttribute("data-state"));
    expect(states).toEqual(["selected", "correct", "look-again", "disabled", "loading"]);
    // the result is words as well as an icon, and is the radio's description
    expect(screen.getByRole("radio", { name: /^ok/ })).toHaveAccessibleDescription(C.correct);
    expect(screen.getByRole("radio", { name: /^again/ })).toHaveAccessibleDescription(C.lookAgain);
    expect(screen.getByText(C.correct).querySelector("svg")).not.toBeNull();
    expect(screen.getByText(C.lookAgain).querySelector("svg")).not.toBeNull();
    expect(screen.getByRole("radio", { name: /^off/ })).toBeDisabled();
    expect(document.querySelector('[data-state="loading"] input')).toBeDisabled();
  });
  it("a result state without words does not show (never colour alone)", () => {
    render(<AnswerOption name="n" value="1" state="correct">plain</AnswerOption>);
    expect(document.querySelector("label")).toHaveAttribute("data-state", "default");
  });
  it("disabled options cannot be selected", async () => {
    const onSelect = vi.fn();
    render(<AnswerOption name="d" value="1" disabled onSelect={onSelect}>x</AnswerOption>);
    await userEvent.click(screen.getByText("x"));
    expect(onSelect).not.toHaveBeenCalled();
  });
});

describe("ConfidenceRow", () => {
  it("is a radiogroup named by its legend with three options and arrow-key movement", async () => {
    const onChange = vi.fn();
    render(<ConfidenceRow legend={C.confidenceLegend} options={CONF} value="guess" onChange={onChange} />);
    const g = screen.getByRole("radiogroup", { name: C.confidenceLegend });
    const radios = within(g).getAllByRole("radio");
    expect(radios.map((r) => (r as HTMLInputElement).value)).toEqual(["guess", "think", "sure"]);
    radios[0].focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenCalledWith("think");
  });
  it("marks the selected one with an icon, and disables as a whole", () => {
    const { container, rerender } = render(<ConfidenceRow legend="L" options={CONF} value="sure" />);
    expect(screen.getByRole("radio", { name: "Sure" })).toBeChecked();
    expect(container.querySelectorAll("svg")).toHaveLength(1);
    rerender(<ConfidenceRow legend="L" options={CONF} value="sure" disabled />);
    screen.getAllByRole("radio").forEach((r) => expect(r).toBeDisabled());
    rerender(<ConfidenceRow legend="L" options={CONF} loading />);
    expect(screen.getByRole("radiogroup")).toHaveAttribute("aria-busy", "true");
  });
});

describe("IDontKnowButton", () => {
  it("fires onClick by click, Enter and Space; disabled and loading do nothing", async () => {
    const onClick = vi.fn();
    const { rerender } = render(<IDontKnowButton label={C.idk} onClick={onClick} />);
    const b = screen.getByRole("button", { name: C.idk });
    await userEvent.click(b);
    b.focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard(" ");
    expect(onClick).toHaveBeenCalledTimes(3);
    rerender(<IDontKnowButton label={C.idk} onClick={onClick} disabled />);
    expect(screen.getByRole("button")).toBeDisabled();
    rerender(<IDontKnowButton label={C.idk} onClick={onClick} loading />);
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(3);
  });
});

describe("TrustChip honesty rule", () => {
  it("renders nothing when the verified flag is not passed", () => {
    const { container } = render(<TrustChip variant="checked-by-code" />);
    expect(container).toBeEmptyDOMElement();
  });
  it("refuses the checked variant unless verified === true", () => {
    for (const v of [false, undefined] as const) {
      const { container, unmount } = render(<TrustChip variant="checked-by-code" verified={v} />);
      expect(container).toBeEmptyDOMElement();
      unmount();
    }
    // truthy but not boolean true (a bad caller) is refused too
    const { container } = render(<TrustChip variant="checked-by-code" verified={"yes" as unknown as boolean} />);
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByText(TRUST_LABELS["checked-by-code"])).toBeNull();
  });
  it("the verified hints variant also needs true", () => {
    expect(trustChipVisible("hints-from-verified-steps", false)).toBe(false);
    expect(trustChipVisible("hints-from-verified-steps", true)).toBe(true);
  });
  it("shows the honest wording only for verified items", () => {
    render(<TrustChip variant="checked-by-code" verified />);
    expect(screen.getByText("Checked by code")).toBeInTheDocument();
  });
  it("not-verified shows only for verified === false and never says Checked by code", () => {
    const { container, rerender } = render(<TrustChip variant="not-verified" verified={false} />);
    expect(container).toHaveTextContent(TRUST_LABELS["not-verified"]);
    expect(container.textContent).not.toMatch(/checked by code/i);
    rerender(<TrustChip variant="not-verified" verified />);
    expect(container).toBeEmptyDOMElement();
  });
  it("only the checked label says 'Checked by code'", () => {
    const others = Object.entries(TRUST_LABELS).filter(([k]) => k !== "checked-by-code");
    for (const [, label] of others) expect(label).not.toMatch(/checked by code/i);
  });
});

describe("HintLadder", () => {
  it("opens hints one at a time, in order, inside an aria-live region", async () => {
    const onReveal = vi.fn();
    render(<HintLadder hints={["h1", "h2"]} labels={hintLabels} onReveal={onReveal} />);
    expect(screen.getByTestId("hint-list")).toHaveAttribute("aria-live", "polite");
    expect(screen.queryByText("h1")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: C.hint.first }));
    expect(screen.getByText("h1")).toBeInTheDocument();
    expect(screen.queryByText("h2")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: C.hint.next }));
    expect(within(screen.getByTestId("hint-list")).getByText("h2")).toBeInTheDocument();
    expect(screen.queryByTestId("hint-next")).toBeNull();
    expect(onReveal.mock.calls).toEqual([[0], [1]]);
  });
  it("gates Show full steps until a hint was opened", async () => {
    const onShowSteps = vi.fn();
    render(<HintLadder hints={["h1"]} labels={hintLabels} steps={<span>the steps</span>} onShowSteps={onShowSteps} />);
    const gate = screen.getByTestId("hint-steps");
    expect(gate).toBeDisabled();
    expect(gate).toHaveAccessibleDescription(C.hint.stepsLocked);
    await userEvent.click(gate);
    expect(onShowSteps).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("hint-next"));
    expect(gate).toBeEnabled();
    await userEvent.click(gate);
    expect(onShowSteps).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("full-steps")).toHaveTextContent("the steps");
  });
  it("disabled and loading block the buttons", () => {
    const { rerender } = render(<HintLadder hints={["h"]} labels={hintLabels} disabled />);
    expect(screen.getByTestId("hint-next")).toBeDisabled();
    rerender(<HintLadder hints={["h"]} labels={hintLabels} loading />);
    expect(screen.getByTestId("hint-next")).toBeDisabled();
    expect(screen.getByTestId("hint-list")).toHaveAttribute("aria-busy", "true");
  });
});

describe("FeedbackCard", () => {
  it("look-again is a status region with an icon and words, not red", () => {
    render(<FeedbackCard variant="look-again" title={C.lookAgainTitle}>body</FeedbackCard>);
    const s = screen.getByRole("status");
    expect(s).toHaveTextContent("Not quite, let's look at this");
    expect(s.querySelector("svg")).not.toBeNull();
    expect(s.className).toMatch(/warning/);
    expect(s.className).not.toMatch(/danger/);
  });
  it("correct variant is green with words", () => {
    render(<FeedbackCard variant="correct" title={C.correctTitle} />);
    expect(screen.getByRole("status")).toHaveAttribute("data-variant", "correct");
    expect(screen.getByRole("status").className).toMatch(/success/);
  });
});

describe("TopicChip, ProgressBar, skeleton, empty state", () => {
  it("TopicChip as button toggles with aria-pressed and is 44 px; plain chip is a label", async () => {
    const onClick = vi.fn();
    const { rerender } = render(<TopicChip onClick={onClick}>Roots</TopicChip>);
    const b = screen.getByRole("button", { name: "Roots" });
    expect(b).toHaveAttribute("aria-pressed", "false");
    expect(b.className).toMatch(/min-h-11/);
    await userEvent.click(b);
    expect(onClick).toHaveBeenCalled();
    rerender(<TopicChip onClick={onClick} selected>Roots</TopicChip>);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
    rerender(<TopicChip onClick={onClick} disabled>Roots</TopicChip>);
    expect(screen.getByRole("button")).toBeDisabled();
    rerender(<TopicChip>Plain</TopicChip>);
    expect(screen.queryByRole("button")).toBeNull();
  });
  it("ProgressBar is named 'Question 2 of 5' with values", () => {
    render(<ProgressBar current={2} total={5} label="Question 2 of 5" />);
    const p = screen.getByRole("progressbar", { name: "Question 2 of 5" });
    expect(p).toHaveAttribute("aria-valuenow", "2");
    expect(p).toHaveAttribute("aria-valuemax", "5");
    expect(p).toHaveAttribute("aria-valuetext", "Question 2 of 5");
  });
  it("ProgressBar clamps out-of-range values", () => {
    render(<ProgressBar current={9} total={5} label="x" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "5");
  });
  it("SkeletonCard announces a loading status", () => {
    render(<SkeletonCard label="Loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });
  it("EmptyState has a heading and an action slot", () => {
    render(<EmptyState title="Nothing yet" action={<button>Go</button>}>Pick a topic.</EmptyState>);
    expect(screen.getByRole("heading", { name: "Nothing yet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });
});

const TABS = [
  { id: "home", label: "Home", href: "/", icon: "home" },
  { id: "practice", label: "Practice", href: "/practice", icon: "pencil" },
  { id: "progress", label: "Progress", href: "/progress", icon: "chart" },
  { id: "lessons", label: "Lessons", href: "/lessons", icon: "book" },
] as const;

describe("BottomTabBar", () => {
  it("four labelled links; current tab has aria-current from the path prop", () => {
    render(<BottomTabBar items={TABS} currentPath="/practice/3" label="Main" />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getAllByRole("link")).toHaveLength(4);
    expect(screen.getByRole("link", { name: "Practice" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Practice" })).toHaveAttribute("href", "/practice");
  });
  it("is 56 px tall per tab, becomes a side rail at md, and uses no router", () => {
    render(<BottomTabBar items={TABS} currentPath="/" label="Main" />);
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Home" }).className).toMatch(/min-h-14/);
    expect(screen.getByRole("navigation").className).toMatch(/md:w-24/);
    expect(screen.getByRole("navigation").querySelector("ul")!.className).toMatch(/md:flex-col/);
  });
  it("label text is never below 12 px (text-xs) and Enter follows the link hook", async () => {
    const onNavigate = vi.fn((_h: string, e: { preventDefault: () => void }) => e.preventDefault());
    render(<BottomTabBar items={TABS} currentPath="/" label="Main" onNavigate={onNavigate} />);
    const link = screen.getByRole("link", { name: "Lessons" });
    expect(link.className).toMatch(/text-xs/);
    link.focus();
    await userEvent.keyboard("{Enter}");
    expect(onNavigate).toHaveBeenCalledWith("/lessons", expect.anything());
  });
  it("isCurrentTab does not match prefixes of other words", () => {
    expect(isCurrentTab("/practice2", "/practice")).toBe(false);
    expect(isCurrentTab("/", "/practice")).toBe(false);
    expect(isCurrentTab("/practice", "/")).toBe(false);
  });
});

describe("ContinueCard", () => {
  it("shows a link action, progress and title", () => {
    render(<ContinueCard title="Quadratics" progress={{ current: 3, total: 8, label: "Step 3 of 8" }} actionLabel="Continue" href="/l/q" />);
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute("href", "/l/q");
    expect(screen.getByRole("progressbar", { name: "Step 3 of 8" })).toBeInTheDocument();
    expect(screen.getByRole("link").className).toMatch(/min-h-12/);
  });
  it("button action, disabled and loading states", async () => {
    const onAction = vi.fn();
    const { rerender } = render(<ContinueCard title="T" actionLabel="Go" onAction={onAction} />);
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onAction).toHaveBeenCalledTimes(1);
    rerender(<ContinueCard title="T" actionLabel="Go" onAction={onAction} disabled />);
    expect(screen.getByRole("button", { name: "Go" })).toBeDisabled();
    rerender(<ContinueCard title="" actionLabel="Go" loading loadingLabel="Loading" />);
    expect(screen.getByRole("region", { name: "Loading" })).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("cross-cutting rules", () => {
  it("line height is 1.7 for Hindi and Nepali, 1.5 for English", () => {
    expect(lineHeightFor("hi")).toBe(1.7);
    expect(lineHeightFor("ne")).toBe(1.7);
    expect(lineHeightFor("hi-IN")).toBe(1.7);
    expect(lineHeightFor("en")).toBe(1.5);
    expect(lineHeightFor(undefined)).toBe(1.5);
  });
  it("components set lang and line height on their root", () => {
    const { container } = render(
      <>
        <QuestionCard label="q" stem="s" lang="hi" />
        <FeedbackCard variant="correct" title="t" lang="ne" />
        <ContinueCard title="t" actionLabel="a" href="/" lang="hi" />
        <IDontKnowButton label="x" lang="ne" />
        <QuestionCard label="q2" stem="s" lang="en" />
      </>,
    );
    const roots = Array.from(container.children) as HTMLElement[];
    expect(roots.map((r) => r.style.lineHeight)).toEqual(["1.7", "1.7", "1.7", "1.7", "1.5"]);
    expect(roots[0]).toHaveAttribute("lang", "hi");
  });
  it("respects reduced motion: animation and transition classes are always motion-safe gated", () => {
    const { container } = render(
      <>
        <QuestionCard label="q" stem="" loading />
        <SkeletonCard label="l" />
        <IDontKnowButton label="x" loading />
        <ProgressBar current={1} total={2} label="p" />
        <ContinueCard title="" actionLabel="a" loading />
        <AnswerOption name="m" value="1" loading>x</AnswerOption>
      </>,
    );
    const bad: string[] = [];
    container.querySelectorAll("[class]").forEach((el) => {
      for (const c of el.getAttribute("class")!.split(/\s+/)) {
        if (/(^|:)(animate-|transition)/.test(c) && !c.startsWith("motion-safe:")) bad.push(c);
      }
    });
    expect(bad).toEqual([]);
    expect(container.innerHTML).toMatch(/motion-safe:animate-pulse/);
  });
  it("no component fetches (typed text and answers never leave the device)", () => {
    const f = vi.spyOn(globalThis, "fetch");
    render(
      <>
        <Group />
        <HintLadder hints={["a"]} labels={hintLabels} />
        <ConfidenceRow legend="l" options={CONF} />
      </>,
    );
    expect(f).not.toHaveBeenCalled();
    f.mockRestore();
  });
  it("interactive controls meet the 44 px floor via min-h classes", () => {
    render(
      <>
        <IDontKnowButton label="a" />
        <TopicChip onClick={() => {}}>t</TopicChip>
        <ConfidenceRow legend="l" options={CONF} />
      </>,
    );
    expect(screen.getByRole("button", { name: "a" }).className).toMatch(/min-h-12/);
    expect(screen.getByRole("button", { name: "t" }).className).toMatch(/min-h-11/);
    expect(document.querySelector("[role=radiogroup] label span")!.className).toMatch(/min-h-12/);
  });
});
