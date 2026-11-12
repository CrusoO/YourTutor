import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
vi.mock("@/lib/dev-auth", () => ({ ensureDevStudent: vi.fn(), skipLogin: () => false }));
vi.mock("@/components/StorageNotice", () => ({ default: () => null }));
vi.mock("@/components/legal/LegalLinks", () => ({ default: () => null }));
vi.mock("@/app/brownie/Interactions", () => ({ LandingLanguages: () => null }));

import LoginPage from "@/app/login/page";

afterEach(cleanup);

describe("the sign-in form", () => {
  it("posts, never gets, so a submit before hydration cannot put the PIN in the address", () => {
    const { container } = render(<LoginPage />);
    expect(container.querySelector("form")).toHaveAttribute("method", "post");
  });

  it("enables the submit button once the page has hydrated", async () => {
    render(<LoginPage />);
    expect(await screen.findByRole("button", { name: /sign in|log in/i })).toBeEnabled();
  });

  it("renders the button disabled in the server-rendered markup", async () => {
    const { renderToString } = await import("react-dom/server");
    expect(renderToString(<LoginPage />)).toMatch(/<button[^>]*disabled[^>]*type="submit"|<button[^>]*type="submit"[^>]*disabled/);
  });
});
