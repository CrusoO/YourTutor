import { cleanup, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LESSON } from "../lessons/aiLesson";

const closeLesson = vi.fn();
vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ lesson: { id: 1, prompt: "", group: "AbC123xy" }, closeLesson }),
}));
vi.mock("@/lib/api", () => ({
  openGroup: vi.fn(),
  sendGroupResults: vi.fn(),
  explainChat: vi.fn(),
  explainLesson: vi.fn(),
  publishGroup: vi.fn(),
  myGroups: vi.fn(),
  groupSummary: vi.fn(),
  closeGroup: vi.fn(),
}));

import GroupsPage from "@/app/groups/page";
import { GroupLessonBody } from "@/components/chat/lesson/GroupLesson";
import { answersFrom } from "@/components/chat/lesson/SendResults";
import * as api from "@/lib/api";
import { groupFromSearch } from "@/lib/chat/share";
import { useLinkStart } from "@/lib/chat/useLinkStart";

const group = (over: Partial<api.GroupLesson> = {}): api.GroupLesson => ({
  code: "AbC123xy",
  prompt: "what is quantum tunnelling?",
  language: "en",
  blocks: LESSON.blocks,
  closed: false,
  results_open: true,
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
});
afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
});

describe("groupFromSearch", () => {
  it("accepts a well-formed code and nothing else", () => {
    expect(groupFromSearch("?group=AbC123xy")).toBe("AbC123xy");
    expect(groupFromSearch("?group=a_b-c_d-e1")).toBe("a_b-c_d-e1");
    for (const bad of ["", "?group=", "?group=abc", "?group=" + "a".repeat(17), "?group=../etc/passwd", "?group=a b c d e f", "?x=1"]) {
      expect(groupFromSearch(bad), bad).toBeNull();
    }
  });
});

describe("useLinkStart with a group link", () => {
  const ready = { role: "guest", identityReady: true, contextReady: {}, lessonOpen: false };

  it("opens the shared lesson by its code, once, and cleans the address", () => {
    window.history.replaceState({}, "", "/brownie-chat?group=AbC123xy");
    const submitText = vi.fn();
    renderHook(() => useLinkStart({ ...ready, submitText }));
    expect(submitText).toHaveBeenCalledTimes(1);
    expect(submitText).toHaveBeenCalledWith("", "AbC123xy");
    expect(window.location.search).toBe("");
  });

  it("prefers the group to a question when a link has both", () => {
    window.history.replaceState({}, "", "/brownie-chat?topic=slope&group=AbC123xy");
    const submitText = vi.fn();
    renderHook(() => useLinkStart({ ...ready, submitText }));
    expect(submitText).toHaveBeenCalledWith("", "AbC123xy");
  });

  it("ignores a malformed code instead of starting anything", () => {
    window.history.replaceState({}, "", "/brownie-chat?group=../x");
    const submitText = vi.fn();
    renderHook(() => useLinkStart({ ...ready, submitText }));
    expect(submitText).not.toHaveBeenCalled();
  });
});

async function toTheEnd() {
  const cont = () => screen.getByTestId("lesson-continue");
  await userEvent.click(cont());
  await userEvent.click(screen.getByTestId("confidence-sure"));
  await userEvent.click(screen.getByRole("button", { name: "It appears on the other side" })); // wrong, and sure
  await userEvent.click(cont());
  await userEvent.click(cont());
  await userEvent.click(cont());
  await userEvent.click(screen.getByRole("button", { name: "It falls quickly" })); // right
  await userEvent.click(cont());
  await userEvent.type(screen.getByLabelText("Type your answer"), "x");
  await userEvent.click(screen.getByRole("button", { name: "See a sample answer" }));
  await userEvent.click(cont());
}

describe("a shared lesson", () => {
  it("opens by code with no model call, shows the question and says who chose it", async () => {
    vi.mocked(api.openGroup).mockResolvedValue(group());
    render(<GroupLessonBody code="AbC123xy" />);
    expect(await screen.findByTestId("block-hook")).toBeInTheDocument();
    expect(api.openGroup).toHaveBeenCalledWith("AbC123xy");
    expect(api.explainLesson).not.toHaveBeenCalled();
    expect(screen.getByTestId("lesson-prompt")).toHaveTextContent("what is quantum tunnelling?");
    expect(screen.getByTestId("group-note")).toHaveTextContent("Chosen by the person who shared it");
    expect(screen.queryByTestId("lesson-new")).toBeNull(); // the big way out waits for the end
  });

  it("says plainly when the link does not work, and offers the way out", async () => {
    for (const fail of ["reject", "unusable"] as const) {
      if (fail === "reject") vi.mocked(api.openGroup).mockRejectedValue(new Error("404"));
      else vi.mocked(api.openGroup).mockResolvedValue(group({ blocks: [] }));
      render(<GroupLessonBody code="AbC123xy" />);
      expect(await screen.findByTestId("group-missing")).toHaveTextContent("not working");
      cleanup();
    }
  });

  it("offers to send results at the end, says what goes, and sends only the answers", async () => {
    vi.mocked(api.openGroup).mockResolvedValue(group());
    vi.mocked(api.sendGroupResults).mockResolvedValue({ accepted: 2 });
    render(<GroupLessonBody code="AbC123xy" />);
    await screen.findByTestId("block-hook");
    expect(screen.queryByTestId("send-results")).toBeNull();
    await toTheEnd();
    const box = screen.getByTestId("send-results");
    expect(box).toHaveTextContent("No name, no account");
    await userEvent.click(within(box).getByTestId("send-results-button"));
    await waitFor(() => expect(screen.getByTestId("send-results-status")).toHaveTextContent("Sent. Thank you."));
    const [code, items] = vi.mocked(api.sendGroupResults).mock.calls[0]!;
    expect(code).toBe("AbC123xy");
    expect(items).toHaveLength(2);
    expect(items[0]).toEqual({
      question: expect.any(String),
      kind: "predict",
      right: false,
      confidence: "sure",
      idea: "thinks a ball can pass through the hill",
    });
    expect(Object.keys(items[0]!).sort()).toEqual(["confidence", "idea", "kind", "question", "right"]);
    expect(within(box).getByTestId("send-results-button")).toBeDisabled();
  });

  it("says so when sending fails, and lets the learner try again", async () => {
    vi.mocked(api.openGroup).mockResolvedValue(group());
    vi.mocked(api.sendGroupResults).mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce({ accepted: 2 });
    render(<GroupLessonBody code="AbC123xy" />);
    await screen.findByTestId("block-hook");
    await toTheEnd();
    await userEvent.click(screen.getByTestId("send-results-button"));
    await waitFor(() => expect(screen.getByTestId("send-results-status")).toHaveTextContent("Couldn't send it"));
    await userEvent.click(screen.getByTestId("send-results-button"));
    await waitFor(() => expect(screen.getByTestId("send-results-status")).toHaveTextContent("Sent"));
  });

  it("offers no sending when results are not open, and says so when the group is closed", async () => {
    vi.mocked(api.openGroup).mockResolvedValue(group({ results_open: false }));
    render(<GroupLessonBody code="AbC123xy" />);
    await screen.findByTestId("block-hook");
    await toTheEnd();
    expect(screen.queryByTestId("send-results")).toBeNull();
    expect(screen.queryByTestId("group-closed")).toBeNull();
    cleanup();

    vi.mocked(api.openGroup).mockResolvedValue(group({ results_open: false, closed: true }));
    render(<GroupLessonBody code="AbC123xy" />);
    await screen.findByTestId("block-hook");
    await toTheEnd();
    expect(screen.getByTestId("group-closed")).toBeInTheDocument();
  });

  it("builds the payload from the evidence with nothing extra", () => {
    const sent = answersFrom([
      { id: "1", kind: "check", question: "Q", options: ["a", "b"], correct: 1, right: false, confidence: null, idea: null },
    ]);
    expect(sent).toEqual([{ question: "Q", kind: "check", right: false, confidence: null, idea: null }]);
    expect(Object.keys(sent[0]!)).not.toContain("options");
  });
});

describe("the organiser page", () => {
  const listing = (over: Partial<api.GroupListing> = {}): api.GroupListing => ({
    code: "AbC123xy",
    path: "/brownie-chat?group=AbC123xy",
    prompt: "what is quantum tunnelling?",
    created_at: "2026-11-03T10:00:00Z",
    closed: false,
    participants: 0,
    ...over,
  });

  it("asks for a teacher's sign-in when the API refuses", async () => {
    vi.mocked(api.myGroups).mockRejectedValue(new Error("403"));
    render(<GroupsPage />);
    expect(await screen.findByTestId("groups-signin")).toHaveTextContent("Sign in as a teacher");
  });

  it("builds a lesson, shows it for reading with the right answers marked, publishes it and shows the link", async () => {
    vi.mocked(api.myGroups).mockResolvedValue({ groups: [] });
    vi.mocked(api.explainLesson).mockResolvedValue(LESSON);
    vi.mocked(api.publishGroup).mockResolvedValue({ code: "AbC123xy", path: "/brownie-chat?group=AbC123xy" });
    render(<GroupsPage />);
    await userEvent.type(await screen.findByTestId("group-topic"), "what is quantum tunnelling?");
    await userEvent.click(screen.getByTestId("group-build"));
    const review = await screen.findByTestId("group-review");
    expect(review).toHaveTextContent("You are the one checking it");
    expect(review).toHaveTextContent("✓ It falls quickly");
    expect(review).toHaveTextContent("(thinks a thicker barrier helps)");
    expect(api.publishGroup).not.toHaveBeenCalled(); // nothing is shared until the teacher says so

    await userEvent.click(screen.getByTestId("group-publish"));
    expect(api.publishGroup).toHaveBeenCalledWith("what is quantum tunnelling?", "en", LESSON.blocks);
    expect(await screen.findByTestId("group-link")).toHaveTextContent(`${window.location.origin}/brownie-chat?group=AbC123xy`);
  });

  it("says so when a lesson cannot be built, and shares nothing", async () => {
    vi.mocked(api.myGroups).mockResolvedValue({ groups: [] });
    vi.mocked(api.explainLesson).mockResolvedValue({ kind: "unavailable", reason: "checks" });
    render(<GroupsPage />);
    await userEvent.type(await screen.findByTestId("group-topic"), "slope");
    await userEvent.click(screen.getByTestId("group-build"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't build");
    expect(screen.queryByTestId("group-review")).toBeNull();
  });

  it("lists lessons with how many have answered, and shows the waiting message below the minimum", async () => {
    vi.mocked(api.myGroups).mockResolvedValue({ groups: [listing({ participants: 3 })] });
    vi.mocked(api.groupSummary).mockResolvedValue({
      code: "AbC123xy", prompt: "what is quantum tunnelling?", participants: 3, minimum: 5, cell: 3, ready: false, questions: [],
    });
    render(<GroupsPage />);
    expect(await screen.findByTestId("group-row")).toHaveTextContent("3 answered");
    await userEvent.click(screen.getByTestId("group-results"));
    expect(await screen.findByTestId("group-waiting")).toHaveTextContent("3 of 5 people have sent results");
  });

  it("shows where the group is stuck, writing a hidden count as 'fewer than' and never a made-up number", async () => {
    vi.mocked(api.myGroups).mockResolvedValue({ groups: [listing({ participants: 8 })] });
    vi.mocked(api.groupSummary).mockResolvedValue({
      code: "AbC123xy",
      prompt: "what is quantum tunnelling?",
      participants: 8,
      minimum: 5,
      cell: 3,
      ready: true,
      questions: [
        { question: "Q one", kind: "check", answered: 8, wrong: 5, sure_wrong: 4, ideas: [{ idea: "thinks thicker helps", count: 5 }] },
        { question: "Q two", kind: "check", answered: 8, wrong: null, sure_wrong: null, ideas: [] },
      ],
    });
    render(<GroupsPage />);
    await userEvent.click(await screen.findByTestId("group-results"));
    const rows = await screen.findAllByTestId("group-question");
    expect(rows[0]).toHaveTextContent("8 answered: 5 got it wrong, 4 were sure and wrong");
    expect(rows[0]).toHaveTextContent("thinks thicker helps (5)");
    expect(rows[1]).toHaveTextContent("fewer than 3 got it wrong");
    expect(rows[1]).not.toHaveTextContent(/\d+ were sure/);
  });

  it("stops collecting on request", async () => {
    vi.mocked(api.myGroups).mockResolvedValue({ groups: [listing()] });
    vi.mocked(api.closeGroup).mockResolvedValue({ closed: true });
    render(<GroupsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Stop collecting" }));
    expect(api.closeGroup).toHaveBeenCalledWith("AbC123xy");
  });
});
