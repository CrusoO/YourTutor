import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const doubtSolve = vi.fn();
vi.mock("@/lib/api", () => ({ doubtSolve: (b: string) => doubtSolve(b) }));

import ServerCheck from "@/components/chat/doubt/ServerCheck";
import type { MathCandidate } from "@/lib/doubt/types";

const cand: MathCandidate = {
  schema: "doubt-expr/1",
  kind: "poly_eq",
  variable: "x",
  display: "2x + 3 = 7",
  lhsText: "2*x + 3",
  rhsText: "7",
  lhs: ["3", "2"],
  rhs: ["7"],
};

afterEach(() => {
  cleanup();
  doubtSolve.mockReset();
  vi.unstubAllEnvs();
});

const verified = {
  schema: "doubt-result/1",
  verified: true,
  label: "checked_by_code",
  reason: null,
  answer: { kind: "values", values: ["2"] },
  steps: [{ rule: "subtract_both_sides", args: { amount: "3" }, before: "2x + 3 = 7", after: "2x = 4" }],
  proof: { kernel: "1", checker: "algebra:1" },
};

describe("ServerCheck", () => {
  it("renders nothing while the flag is off", () => {
    const { container } = render(<ServerCheck candidate={cand} />);
    expect(container).toBeEmptyDOMElement();
    expect(doubtSolve).not.toHaveBeenCalled();
  });

  it("sends nothing until the tap, then only the structured wire object", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_SERVER", "true");
    doubtSolve.mockResolvedValue({ status: 200, json: verified });
    render(<ServerCheck candidate={cand} />);
    expect(doubtSolve).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("doubt-server-check"));
    expect(doubtSolve).toHaveBeenCalledTimes(1);
    expect(JSON.parse(doubtSolve.mock.calls[0][0])).toEqual({
      schema: "doubt-expr/1",
      kind: "poly_eq",
      lhs: ["3", "2"],
      rhs: ["7"],
    });
    expect(await screen.findByTestId("doubt-server-label")).toHaveTextContent("Checked by code");
  });

  it("never shows the label for an unverified or consent-refused reply", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_SERVER", "true");
    doubtSolve.mockResolvedValueOnce({ status: 200, json: { schema: "doubt-result/1", verified: false, reason: "irrational_roots" } });
    render(<ServerCheck candidate={cand} />);
    await userEvent.click(screen.getByTestId("doubt-server-check"));
    expect(await screen.findByTestId("doubt-server-unchecked")).toBeInTheDocument();
    expect(screen.queryByText("Checked by code")).toBeNull();
    cleanup();
    doubtSolve.mockResolvedValueOnce({ status: 403, json: { detail: { code: "math_check_consent_required" } } });
    render(<ServerCheck candidate={cand} />);
    await userEvent.click(screen.getByTestId("doubt-server-check"));
    expect(await screen.findByTestId("doubt-server-refused")).toHaveTextContent("guardian");
    expect(screen.queryByText("Checked by code")).toBeNull();
  });

  it("offers nothing for a kind that is not sent", () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_SERVER", "true");
    const { container } = render(<ServerCheck candidate={{ ...cand, kind: "arith", expr: "2+2" }} />);
    expect(container).toBeEmptyDOMElement();
  });
});
