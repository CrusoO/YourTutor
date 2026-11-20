import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SessionPage from "@/app/session/[id]/page";
import { AnotherWay } from "@/components/session/AnotherWay";
import { getSession, postEvent, type ActionPayload } from "@/lib/api";
import { t } from "@/lib/messages";
import { offeredWays, readReason } from "@/lib/session/ways";
import { actionFixture } from "./actionFixtures";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "sess-test" }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getSession: vi.fn(),
  postEvent: vi.fn(),
  locale: () => "en",
}));

const copy = t("en");

describe("offeredWays", () => {
  const all = { picture: true, steps: true, worked: true, video: true };

  it("keeps the server's order and only the known, available families, each once", () => {
    expect(offeredWays(["worked", "picture", "worked", "steps"], all)).toEqual(["worked", "picture", "steps"]);
    expect(offeredWays(["picture", "steps", "worked"], { steps: true, worked: true })).toEqual(["steps", "worked"]);
  });

  it("ignores anything it does not know or that is not a list", () => {
    expect(offeredWays(["<script>", 3, null, "steps"], all)).toEqual(["steps"]);
    for (const bad of [undefined, null, "steps", { 0: "steps" }, 5]) expect(offeredWays(bad, all)).toEqual([]);
  });

  it("returns nothing when none can be shown on this screen", () => {
    expect(offeredWays(["picture", "video"], { steps: true })).toEqual([]);
  });
});

describe("readReason", () => {
  it("reads the offer from the server extras and nothing else", () => {
    expect(readReason({ reason: { offer: ["steps"], cause: "misconception:MC.X" } })).toEqual({ offer: ["steps"] });
    expect(readReason({})).toBeNull();
    expect(readReason(undefined)).toBeNull();
    expect(readReason({ reason: "steps" })).toBeNull();
  });
});

describe("AnotherWay", () => {
  afterEach(cleanup);

  it("lists the offered kinds of help, plainly, with no grade or label", () => {
    render(<AnotherWay copy={copy} ways={["picture", "steps"]} busy={false} onChoose={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Want to try it another way?" })).toBeInTheDocument();
    expect(screen.getByTestId("way-picture")).toHaveTextContent("Show me a picture");
    expect(screen.getByTestId("way-steps")).toHaveTextContent("Break it into smaller steps");
    expect(screen.queryByTestId("way-video")).toBeNull();
  });

  it("sends the chosen kind once and is disabled while a request is in flight", async () => {
    const onChoose = vi.fn();
    const { rerender } = render(<AnotherWay copy={copy} ways={["steps"]} busy={false} onChoose={onChoose} />);
    await userEvent.click(screen.getByTestId("way-steps"));
    expect(onChoose).toHaveBeenCalledTimes(1);
    expect(onChoose).toHaveBeenCalledWith("steps");
    rerender(<AnotherWay copy={copy} ways={["steps"]} busy onChoose={onChoose} />);
    expect(screen.getByTestId("way-steps")).toBeDisabled();
  });

  it("renders nothing when there is nothing to offer", () => {
    const { container } = render(<AnotherWay copy={copy} ways={[]} busy={false} onChoose={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("SessionPage another way", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  function mockSession(action: ActionPayload) {
    const view = {
      id: "sess-test",
      session_id: "sess-test",
      type: "practice",
      student_id: "stu-1",
      action,
      progress: { items_completed: 0, active_ms: 0, resumable: false },
    };
    vi.mocked(getSession).mockResolvedValue(view as never);
    vi.mocked(postEvent).mockImplementation(async () => view as never);
  }

  async function open(action: ActionPayload) {
    mockSession(action);
    render(<SessionPage />);
    await waitFor(() => expect(getSession).toHaveBeenCalled());
    await screen.findByRole("main");
  }

  const hint = (extras: Record<string, unknown>) =>
    actionFixture("hint", {
      text: "Try undoing the + 4.",
      hint_level: 1,
      can_request_hint: true,
      can_request_help: true,
      can_show_solution: true,
      extras,
    });

  it("offers the kinds of help the server sent and replaces the two plain buttons with them", async () => {
    await open(hint({ reason: { band: "likely", offer: ["worked", "steps"], level: 2 } }));
    expect(await screen.findByTestId("another-way")).toBeInTheDocument();
    expect(screen.getByTestId("way-worked")).toBeInTheDocument();
    expect(screen.queryByTestId("help-button")).toBeNull();
    expect(screen.getByTestId("hint-text")).toHaveTextContent("Try undoing the + 4.");
  });

  it("records the choice and then does the same thing the old button did", async () => {
    const action = hint({ reason: { band: "maybe", offer: ["steps", "worked"], level: 2 } });
    await open(action);
    await userEvent.click(await screen.findByTestId("way-steps"));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "move_chosen", { family: "steps" }, action.item_id);
    expect(postEvent).toHaveBeenCalledWith("sess-test", "request_help", expect.anything(), action.item_id);
  });

  it("shows exactly what it showed before when the server sends no reason", async () => {
    await open(hint({}));
    expect(screen.queryByTestId("another-way")).toBeNull();
    expect(screen.getByTestId("help-button")).toBeInTheDocument();
  });

  it("falls back to the plain buttons when none of the offered kinds can be shown here", async () => {
    await open(hint({ reason: { band: "unclear", offer: ["video"], level: 2 } }));
    expect(screen.queryByTestId("another-way")).toBeNull();
    expect(screen.getByTestId("help-button")).toBeInTheDocument();
  });
});
