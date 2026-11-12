import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/agreements-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/agreements-api")>()),
  getCatalog: vi.fn(),
  myAgreements: vi.fn(),
  acceptAgreement: vi.fn(),
  withdrawItem: vi.fn(),
  lookupApproval: vi.fn(),
  approveChild: vi.fn(),
  declineChild: vi.fn(),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getContextOptions: vi.fn().mockResolvedValue({ curricula: [{ id: "bhutan", grades: [{ grade: 9, subjects: [] }] }], languages: [] }),
  setStaffToken: vi.fn(),
  staffToken: () => "t",
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

import AgreementForm from "@/components/agreement/AgreementForm";
import AgreementSettings from "@/components/agreement/AgreementSettings";
import ApprovePage from "@/app/approve/page";
import { DRAFT_BANNER, items as copy, PLACEHOLDER } from "@/lib/agreement-copy";
import * as api from "@/lib/agreements-api";

const guardian: api.Catalog = {
  role: "guardian",
  version: "agreement-v1",
  items: [
    { id: "confirm_guardian", required: true, scope: null },
    { id: "tutoring", required: true, scope: "tutoring" },
    { id: "ai_processing", required: true, scope: "ai_processing" },
    { id: "teacher_share", required: false, scope: "teacher_share" },
    { id: "progress_reports", required: false, scope: null },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getCatalog).mockResolvedValue(guardian);
});
afterEach(cleanup);

describe("the agreement form", () => {
  it("gives every item its own tick box, required ones in their own group", async () => {
    render(<AgreementForm role="guardian" onSubmit={vi.fn()} />);
    const needed = await screen.findByTestId("group-required");
    const optional = screen.getByTestId("group-optional");
    expect(within(needed).getAllByRole("checkbox")).toHaveLength(3);
    expect(within(optional).getAllByRole("checkbox")).toHaveLength(2);
    expect(within(optional).getByTestId("tick-teacher_share")).toBeInTheDocument();
    for (const box of screen.getAllByRole("checkbox")) expect(box).not.toBeChecked();
  });

  it("will not continue until every required box is ticked, and optional ones are never forced", async () => {
    const onSubmit = vi.fn();
    render(<AgreementForm role="guardian" onSubmit={onSubmit} />);
    const go = await screen.findByRole("button", { name: "Agree and continue" });
    expect(go).toBeDisabled();
    for (const id of ["confirm_guardian", "tutoring"]) await userEvent.click(within(screen.getByTestId(`tick-${id}`)).getByRole("checkbox"));
    expect(go).toBeDisabled();
    await userEvent.click(within(screen.getByTestId("tick-ai_processing")).getByRole("checkbox"));
    expect(go).toBeEnabled();
    await userEvent.click(go);
    expect(onSubmit).toHaveBeenCalledWith(["confirm_guardian", "tutoring", "ai_processing"], "agreement-v1");
  });

  it("sends the optional items only when they were ticked", async () => {
    const onSubmit = vi.fn();
    render(<AgreementForm role="guardian" onSubmit={onSubmit} />);
    await screen.findByTestId("group-required");
    for (const box of screen.getAllByRole("checkbox")) await userEvent.click(box);
    await userEvent.click(screen.getByRole("button", { name: "Agree and continue" }));
    expect(onSubmit.mock.calls[0][0]).toContain("teacher_share");
  });

  it("has wording for every item the server lists, and no invented contact", () => {
    for (const item of guardian.items) expect(copy.guardian[item.id], item.id).toBeTruthy();
    expect(DRAFT_BANNER).toBe("Draft: under legal review. Not yet in force.");
    const all = JSON.stringify(copy);
    expect(all).toContain(PLACEHOLDER);
    expect(all).not.toMatch(/@[a-z0-9-]+\.[a-z]{2,}|\+\d{6,}|https?:\/\//i);
  });

  it("teacher terms are three required lines", () => {
    expect(Object.keys(copy.teacher)).toEqual(["terms_counts_only", "terms_no_sharing_codes", "terms_no_exporting_names"]);
  });
});

describe("settings", () => {
  const mine = (items: string[]): api.MyAgreements => ({
    version: "agreement-v1",
    needed: [],
    agreements: [{ role: "guardian", version: "agreement-v1", items, granted_at: "2026-11-11", complete: true }],
  });

  it("withdraws an optional item with one untick", async () => {
    vi.mocked(api.myAgreements).mockResolvedValue(mine(["confirm_guardian", "tutoring", "ai_processing", "teacher_share"]));
    vi.mocked(api.withdrawItem).mockResolvedValue(mine(["confirm_guardian", "tutoring", "ai_processing"]));
    render(<AgreementSettings />);
    const box = within(await screen.findByTestId("tick-teacher_share")).getByRole("checkbox");
    expect(box).toBeChecked();
    await userEvent.click(box);
    await waitFor(() => expect(api.withdrawItem).toHaveBeenCalledWith("guardian", "teacher_share"));
    await waitFor(() => expect(within(screen.getByTestId("tick-teacher_share")).getByRole("checkbox")).not.toBeChecked());
  });

  it("asks before withdrawing a required item", async () => {
    vi.mocked(api.myAgreements).mockResolvedValue(mine(["confirm_guardian", "tutoring", "ai_processing"]));
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<AgreementSettings />);
    await userEvent.click(within(await screen.findByTestId("tick-tutoring")).getByRole("checkbox"));
    expect(confirm).toHaveBeenCalled();
    expect(api.withdrawItem).not.toHaveBeenCalled();
  });

  it("ticks an optional item again", async () => {
    vi.mocked(api.myAgreements).mockResolvedValue(mine(["confirm_guardian", "tutoring", "ai_processing"]));
    vi.mocked(api.acceptAgreement).mockResolvedValue(mine(["confirm_guardian", "tutoring", "ai_processing", "teacher_share"]));
    render(<AgreementSettings />);
    await userEvent.click(within(await screen.findByTestId("tick-teacher_share")).getByRole("checkbox"));
    await waitFor(() =>
      expect(api.acceptAgreement).toHaveBeenCalledWith("guardian", "agreement-v1", ["confirm_guardian", "tutoring", "ai_processing", "teacher_share"]),
    );
  });
});

describe("the guardian's approval screen", () => {
  const view: api.ApprovalView = { nickname: "Tiger", grade: 9, curriculum_id: "bhutan", expires_at: "x", agreement: guardian };

  it("says the link is not valid when there is none", async () => {
    window.location.hash = "";
    render(<ApprovePage />);
    expect(await screen.findByTestId("approve-invalid")).toBeInTheDocument();
    expect(api.lookupApproval).not.toHaveBeenCalled();
  });

  it("shows the nickname, needs no account, and approves with the ticks", async () => {
    window.location.hash = "#tok-abcdefghij";
    vi.mocked(api.lookupApproval).mockResolvedValue(view);
    vi.mocked(api.approveChild).mockResolvedValue({ access_token: "g", student_id: "s", display_name: "Tiger" });
    render(<ApprovePage />);
    expect(await screen.findByTestId("approve-nickname")).toHaveTextContent("Tiger");
    expect(api.lookupApproval).toHaveBeenCalledWith("tok-abcdefghij");
    for (const id of ["confirm_guardian", "tutoring", "ai_processing", "teacher_share"])
      await userEvent.click(within(screen.getByTestId(`tick-${id}`)).getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Say yes and agree" }));
    await waitFor(() => expect(screen.getByTestId("approve-done")).toBeInTheDocument());
    expect(api.approveChild).toHaveBeenCalledWith({
      token: "tok-abcdefghij",
      version: "agreement-v1",
      accepted: ["confirm_guardian", "tutoring", "ai_processing", "teacher_share"],
    });
  });

  it("can say no, and then nothing is kept", async () => {
    window.location.hash = "#tok-abcdefghij";
    vi.mocked(api.lookupApproval).mockResolvedValue(view);
    vi.mocked(api.declineChild).mockResolvedValue({ status: "declined" });
    render(<ApprovePage />);
    await userEvent.click(await screen.findByRole("button", { name: "No, delete this request" }));
    expect(await screen.findByTestId("approve-declined")).toBeInTheDocument();
    expect(api.declineChild).toHaveBeenCalledWith("tok-abcdefghij");
  });
});
