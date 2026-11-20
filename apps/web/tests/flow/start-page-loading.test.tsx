import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StartPage from "@/app/start/page";
import { getContextOptions } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/flags", () => ({ quickStartEnabled: () => false }));
vi.mock("@/components/StorageNotice", () => ({ default: () => null }));
vi.mock("@/components/legal/LegalLinks", () => ({ default: () => null }));
vi.mock("@/lib/api", () => ({ getContextOptions: vi.fn(), guestStart: vi.fn(), locale: () => "en" }));

beforeEach(() => vi.mocked(getContextOptions).mockReset());

describe("Start page (full setup) loading", () => {
  it("shows a loading line, then an error with a retry when the fetch fails", async () => {
    vi.mocked(getContextOptions).mockRejectedValueOnce(new Error("down"));
    render(<StartPage />);
    expect(screen.getByTestId("start-loading")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("We could not start. Please try again.")).toBeInTheDocument());
    expect(screen.queryByTestId("start-loading")).toBeNull();
    vi.mocked(getContextOptions).mockResolvedValueOnce({ curricula: [], languages: [] } as never);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.queryByText("We could not start. Please try again.")).toBeNull());
  });
});
