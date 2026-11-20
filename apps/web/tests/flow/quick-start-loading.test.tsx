import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import QuickStartForm from "@/components/flow/QuickStartForm";
import { getContextOptions } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/components/ui/language-switch", () => ({ LanguageSwitch: () => null }));
vi.mock("@/lib/api", () => ({
  getContextOptions: vi.fn(),
  guestStart: vi.fn(),
  today: vi.fn(),
  locale: () => "en",
}));
vi.mock("@/lib/quick-start", async (orig) => ({ ...(await orig<object>()), startFirstQuestion: vi.fn() }));

const options = {
  languages: [],
  grades: [6],
  curricula: [{ id: "cbse", grades: [{ grade: 6, subjects: [{ id: "MATH" }] }] }],
} as never;

beforeEach(() => vi.mocked(getContextOptions).mockReset());

describe("Quick start loading", () => {
  it("shows a plain loading line and aria-busy until the options arrive", async () => {
    let resolve!: (v: never) => void;
    vi.mocked(getContextOptions).mockReturnValue(new Promise((r) => (resolve = r as never)));
    render(<QuickStartForm />);
    expect(screen.getByTestId("quick-loading").textContent).toBe("Getting the classes ready.");
    expect(screen.getByTestId("quick-grades").getAttribute("aria-busy")).toBe("true");
    resolve(options);
    await waitFor(() => expect(screen.queryByTestId("quick-loading")).toBeNull());
    expect(screen.getByTestId("quick-grades").getAttribute("aria-busy")).toBe("false");
  });

  it("shows an error and a retry button when the fetch fails, and recovers on retry", async () => {
    vi.mocked(getContextOptions).mockRejectedValueOnce(new Error("down"));
    render(<QuickStartForm />);
    await waitFor(() => expect(screen.getByTestId("quick-load-error")).toBeInTheDocument());
    expect(screen.queryByTestId("quick-loading")).toBeNull();
    vi.mocked(getContextOptions).mockResolvedValueOnce(options);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.queryByTestId("quick-load-error")).toBeNull());
    expect(getContextOptions).toHaveBeenCalledTimes(2);
  });
});
