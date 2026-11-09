import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Helplines } from "@/components/chat/Helplines";

const LIST = [
  { id: "tele_manas", kind: "mental_health", name: "Tele-MANAS", number: "14416", hours: null, verified: true },
  { id: "childline", kind: "child_protection", name: "Childline", number: "1098", hours: "24 hours", verified: true },
];

afterEach(cleanup);

describe("Helplines", () => {
  it("shows each name and number as a phone link", () => {
    render(<Helplines list={LIST} />);
    const link = screen.getByRole("link", { name: /Tele-MANAS/ });
    expect(link).toHaveAttribute("href", "tel:14416");
    expect(link).toHaveTextContent("14416");
    expect(screen.getByRole("link", { name: /Childline/ })).toHaveAttribute("href", "tel:1098");
  });

  it("shows the hours when the owner has confirmed them", () => {
    render(<Helplines list={LIST} />);
    expect(screen.getByTestId("helplines")).toHaveTextContent("24 hours");
  });

  it("renders nothing when there is no list, so a missing field never breaks the reply", () => {
    const { container } = render(<Helplines list={undefined} />);
    expect(container).toBeEmptyDOMElement();
    const empty = render(<Helplines list={[]} />);
    expect(empty.container).toBeEmptyDOMElement();
  });

  it("keeps only digits and a plus sign in the phone link", () => {
    render(<Helplines list={[{ ...LIST[0], number: "1800 599 0019" }]} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "tel:18005990019");
  });
});
