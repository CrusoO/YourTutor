import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/agreements-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/agreements-api")>()),
  getCatalog: vi.fn(),
  myAgreements: vi.fn(),
  acceptAgreement: vi.fn(),
  withdrawItem: vi.fn(),
  getConsentText: vi.fn(),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  staffToken: () => "t",
}));

import AgreementForm from "@/components/agreement/AgreementForm";
import AgreementSettings from "@/components/agreement/AgreementSettings";
import ChildNotice from "@/components/agreement/ChildNotice";
import { CONSENT_TEXT_SCOPES, items as copy, withdrawal } from "@/lib/agreement-copy";
import * as api from "@/lib/agreements-api";

const catalog: api.Catalog = {
  role: "guardian",
  version: "agreement-v1",
  items: [
    { id: "confirm_guardian", required: true, scope: null },
    { id: "tutoring", required: true, scope: "tutoring" },
    { id: "ai_processing", required: true, scope: "ai_processing" },
    { id: "math_check", required: false, scope: "math_check" },
  ],
};
const mine = (items: string[]): api.MyAgreements => ({
  version: "agreement-v1",
  needed: [],
  agreements: [{ role: "guardian", version: "agreement-v1", items, granted_at: "2026-11-17", complete: true }],
});
const text = (scope: string): api.ConsentText => ({
  scope,
  version: "v1",
  lang: "en",
  guardian: { text: `GUARDIAN WORDS for ${scope}`, sha256: "a".repeat(64) },
  child: { text: `CHILD WORDS for ${scope}`, sha256: "b".repeat(64) },
});
const base = ["confirm_guardian", "tutoring", "ai_processing"];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getCatalog).mockResolvedValue(catalog);
  vi.mocked(api.getConsentText).mockImplementation(async (scope) => text(scope));
});
afterEach(cleanup);

describe("consent scope copy", () => {
  it("has a label for every scope with wording and a withdrawal line saying what is deleted", () => {
    for (const scope of CONSENT_TEXT_SCOPES) {
      for (const role of ["guardian", "adult"] as const) expect(copy[role][scope].label, `${role} ${scope}`).toBeTruthy();
      expect(withdrawal[scope].length, scope).toBeGreaterThan(40);
    }
    expect(Object.keys(withdrawal).sort()).toEqual([...CONSENT_TEXT_SCOPES].sort());
  });

  it("claims no legal approval", () => {
    const all = JSON.stringify([copy, withdrawal]);
    expect(all).not.toMatch(/legal(ly)? (approved|sign|review(ed)? by)|compliant|DPDP/i);
  });
});

describe("the scope switches in Settings", () => {
  it("shows the approved guardian wording with its version, and the child wording on request", async () => {
    vi.mocked(api.myAgreements).mockResolvedValue(mine(base));
    render(<AgreementSettings />);
    const section = await screen.findByTestId("scope-math_check");
    expect(await within(section).findByTestId("guardian-text-math_check")).toHaveTextContent("GUARDIAN WORDS for math_check");
    expect(within(section).getByText(/Wording version: v1/)).toBeInTheDocument();
    expect(within(section).queryByTestId("child-text-math_check")).toBeNull();
    await userEvent.click(within(section).getByRole("button", { name: /what your child is told/i }));
    expect(within(section).getByTestId("child-text-math_check")).toHaveTextContent("CHILD WORDS");
  });

  it("is off by default and switching it on records only that scope item", async () => {
    vi.mocked(api.myAgreements).mockResolvedValue(mine(base));
    vi.mocked(api.acceptAgreement).mockResolvedValue(mine([...base, "math_check"]));
    render(<AgreementSettings />);
    const section = await screen.findByTestId("scope-math_check");
    const box = within(section).getByRole("switch");
    expect(box).not.toBeChecked();
    await within(section).findByTestId("guardian-text-math_check");
    await userEvent.click(box);
    await waitFor(() => expect(api.acceptAgreement).toHaveBeenCalledWith("guardian", "agreement-v1", [...base, "math_check"]));
    await waitFor(() => expect(within(screen.getByTestId("scope-math_check")).getByRole("switch")).toBeChecked());
  });

  it("cannot be switched on when no approved wording is available", async () => {
    vi.mocked(api.myAgreements).mockResolvedValue(mine(base));
    vi.mocked(api.getConsentText).mockRejectedValue(new Error("404"));
    render(<AgreementSettings />);
    const section = await screen.findByTestId("scope-math_check");
    await within(section).findByText(/cannot be switched on/);
    expect(within(section).getByRole("switch")).toBeDisabled();
  });

  it("explains what is deleted before withdrawing, and withdraws only after confirmation", async () => {
    vi.mocked(api.myAgreements).mockResolvedValue(mine([...base, "math_check"]));
    vi.mocked(api.withdrawItem).mockResolvedValue(mine(base));
    render(<AgreementSettings />);
    const section = await screen.findByTestId("scope-math_check");
    await userEvent.click(within(section).getByRole("switch"));
    const dialog = within(section).getByRole("alertdialog");
    expect(dialog).toHaveTextContent(withdrawal.math_check);
    expect(api.withdrawItem).not.toHaveBeenCalled();
    await userEvent.click(within(dialog).getByRole("button", { name: /keep it on/i }));
    expect(within(section).queryByRole("alertdialog")).toBeNull();
    expect(api.withdrawItem).not.toHaveBeenCalled();
    await userEvent.click(within(section).getByRole("switch"));
    await userEvent.click(within(within(section).getByRole("alertdialog")).getByRole("button", { name: /switch off and delete/i }));
    await waitFor(() => expect(api.withdrawItem).toHaveBeenCalledWith("guardian", "math_check"));
  });

  it("is not offered as a blind tick in the sign-up agreement", async () => {
    render(<AgreementForm role="guardian" onSubmit={vi.fn()} />);
    await screen.findByTestId("group-required");
    expect(screen.queryByTestId("tick-math_check")).toBeNull();
  });
});

describe("the child notice", () => {
  it("shows the approved child wording and calls back on OK or Cancel", async () => {
    const ok = vi.fn();
    const cancel = vi.fn();
    render(<ChildNotice scope="ai_help_typed" onAccept={ok} onCancel={cancel} />);
    const notice = await screen.findByRole("alertdialog");
    expect(notice).toHaveTextContent("CHILD WORDS for ai_help_typed");
    expect(notice).not.toHaveTextContent("GUARDIAN WORDS");
    await userEvent.click(screen.getByRole("button", { name: /ok, i understand/i }));
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(ok).toHaveBeenCalledTimes(1);
    expect(cancel).toHaveBeenCalledTimes(1);
  });

  it("shows nothing and offers no way to continue when the wording is unavailable", async () => {
    vi.mocked(api.getConsentText).mockRejectedValue(new Error("404"));
    render(<ChildNotice scope="photo_check" onAccept={vi.fn()} />);
    await waitFor(() => expect(screen.queryByText("…")).toBeNull());
    expect(screen.queryByRole("button")).toBeNull();
  });
});
