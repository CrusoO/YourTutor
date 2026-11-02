import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import SourceChips from "@/components/flow/SourceChips";

afterEach(cleanup);

describe("SourceChips", () => {
  it("shows one chip per source with its title", () => {
    render(
      <SourceChips
        label="Source"
        sources={[
          { id: "NOTE.A", title: "Inverse operations (authored note)" },
          { id: "NOTE.B", title: "One-step equations (authored note)" },
        ]}
      />,
    );
    expect(screen.getByLabelText("Source")).toBeInTheDocument();
    expect(screen.getByText("Inverse operations (authored note)")).toBeInTheDocument();
    expect(screen.getByText("One-step equations (authored note)")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders nothing when there are no sources", () => {
    const { container } = render(<SourceChips label="Source" sources={[]} />);
    expect(container).toBeEmptyDOMElement();
    const missing = render(<SourceChips label="Source" sources={undefined} />);
    expect(missing.container).toBeEmptyDOMElement();
  });
});
