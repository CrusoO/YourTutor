import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Brand } from "@/components/ui/brand";
import { Button } from "@/components/ui/button";
import { Choice } from "@/components/ui/choice";
import { StatusChip } from "@/components/ui/status-chip";
import { SuggestionCard, SuggestionCardSkeleton } from "@/components/ui/suggestion-card";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/cn";
import { statusLabel } from "@/lib/flow";
import { t } from "@/lib/messages";

afterEach(cleanup);
const copy = t("en");

describe("design-system components", () => {
  it("a SuggestionCard is one keyboard-operable action with a text title and tag", async () => {
    const onClick = vi.fn();
    render(<SuggestionCard icon="refresh" title="Review due" tag="3 cards" tone="success" onClick={onClick} />);
    const card = screen.getByRole("button", { name: /Review due/ });
    expect(card).toHaveTextContent("3 cards");
    card.focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard(" ");
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("a disabled SuggestionCard does nothing and says so to assistive tech", async () => {
    const onClick = vi.fn();
    render(<SuggestionCard icon="book" title="My notes" tag="Soon" disabled onClick={onClick} />);
    const card = screen.getByRole("button", { name: /My notes/ });
    expect(card).toBeDisabled();
    expect(card).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(card);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("a link SuggestionCard renders a real link", () => {
    render(<SuggestionCard icon="calendar" title="Today's plan" href="/today" />);
    expect(screen.getByRole("link", { name: /Today's plan/ })).toHaveAttribute("href", "/today");
  });

  it("icons are hidden from assistive tech: the text label carries the meaning", () => {
    const { container } = render(<SuggestionCard icon="alert" title="Stuck now" onClick={() => {}} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("the skeleton is hidden from assistive tech", () => {
    const { container } = render(<SuggestionCardSkeleton />);
    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
  });

  it("a Choice shows its selected state with a mark and aria-pressed, and a disabled one gives its reason", async () => {
    const onClick = vi.fn();
    render(
      <>
        <Choice selected onClick={onClick}>Class 9</Choice>
        <Choice disabled tag="Coming soon">Class 10</Choice>
      </>,
    );
    const nine = screen.getByRole("button", { name: /Class 9/ });
    expect(nine).toHaveAttribute("aria-pressed", "true");
    expect(nine).toHaveTextContent("✓");
    const ten = screen.getByRole("button", { name: /Class 10/ });
    expect(ten).toBeDisabled();
    expect(ten).toHaveTextContent("Coming soon");
    await userEvent.click(ten);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("every status chip carries words and a shape, never colour alone", () => {
    for (const status of ["not_started", "learning", "can_do_it", "solid", "review_due", "coming_soon"] as const) {
      const { container, unmount } = render(<StatusChip status={status} copy={copy} />);
      const chip = container.firstElementChild as HTMLElement;
      expect(chip.textContent).toContain(statusLabel(copy, status));
      expect(chip.querySelector('[aria-hidden="true"]')?.textContent).toBeTruthy();
      unmount();
    }
  });

  it("a Button defaults to type=button so it never submits a form by accident", () => {
    render(<Button>Go</Button>);
    expect(screen.getByRole("button", { name: "Go" })).toHaveAttribute("type", "button");
  });

  it("the brand name comes from one place", () => {
    render(<Brand />);
    expect(screen.getByText(BRAND.name)).toBeInTheDocument();
  });

  it("cn lets a later utility win", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });
});
