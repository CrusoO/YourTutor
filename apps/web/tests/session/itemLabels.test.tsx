import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import ItemLabels from "@/components/session/ItemLabels";
import { t } from "@/lib/messages";

afterEach(cleanup);

describe("ItemLabels", () => {
  it("never shows nothing: without labels or a check field it says Not checked", () => {
    render(<ItemLabels labels={undefined} />);
    expect(screen.getByTestId("check-stamp")).toHaveTextContent("Not checked");
    expect(screen.getByTestId("check-stamp").dataset.state).toBe("not_checked");
    expect(screen.getByTestId("check-hint")).toHaveTextContent(
      "No rule could check this answer. Compare it with your book or teacher.",
    );
    expect(screen.queryByTestId("item-badge")).toBeNull();
  });

  it("shows Checked only for the exact checked state", () => {
    render(<ItemLabels check="checked" />);
    expect(screen.getByTestId("check-stamp")).toHaveTextContent("Checked");
    expect(screen.getByTestId("check-stamp").dataset.state).toBe("checked");
    expect(screen.queryByTestId("check-hint")).toBeNull();
  });

  it("treats an unknown value as Not checked", () => {
    // @ts-expect-error a stale or hostile value must not read as checked
    render(<ItemLabels check="Checked" />);
    expect(screen.getByTestId("check-stamp").dataset.state).toBe("not_checked");
  });

  it("uses a dashed border for Not checked and a solid one for Checked", () => {
    const { rerender } = render(<ItemLabels check="not_checked" />);
    expect(screen.getByTestId("check-stamp").className).toContain("is-unchecked");
    rerender(<ItemLabels check="checked" />);
    expect(screen.getByTestId("check-stamp").className).toContain("is-checked");
  });

  it("shows the question label and badge, and the pattern and reviewed badge when sent", () => {
    render(
      <ItemLabels
        labels={{
          question: "Original invented question label.",
          badge: "Answer checked by calculation",
          pattern: "Invented pattern tag.",
          reviewed: "Reviewed by a teacher",
        }}
      />,
    );
    expect(screen.getByText("Original invented question label.")).toBeInTheDocument();
    expect(screen.getByTestId("item-pattern")).toHaveTextContent("Invented pattern tag.");
    expect(screen.getByTestId("item-badge")).toHaveTextContent(
      "Answer checked by calculation · Reviewed by a teacher",
    );
  });

  it("omits the pattern tag when none is sent", () => {
    render(<ItemLabels labels={{ question: "Q", badge: "B" }} />);
    expect(screen.queryByTestId("item-pattern")).toBeNull();
  });
});

describe("footer disclaimer copy", () => {
  it("is the fixed wording", () => {
    expect(t("en").independenceFooter).toBe(
      "Brownie is independent and is not affiliated with, endorsed by or approved by any exam board or textbook publisher. Official papers: cbseacademic.nic.in.",
    );
  });
});
