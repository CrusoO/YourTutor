import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import ItemLabels from "@/components/session/ItemLabels";
import { t } from "@/lib/messages";

afterEach(cleanup);

describe("ItemLabels", () => {
  it("shows nothing without labels", () => {
    const { container } = render(<ItemLabels labels={undefined} />);
    expect(container.firstChild).toBeNull();
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
      "Brownie is independent and is not affiliated with, endorsed by or approved by CBSE, NCERT, or Nepal's CDC or NEB. These names are used only to describe syllabus alignment. Official papers: cbseacademic.nic.in.",
    );
  });
});
