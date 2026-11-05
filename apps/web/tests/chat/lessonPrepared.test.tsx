import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const DEMO =
  "I've tried this five times and I keep getting two answers, 40 and -45, and I don't know which one is right. A train travels 360 km at a uniform speed. If the speed had been 5 km/h more, it would have taken 1 hour less. Find the speed of the train. I'm so frustrated.";
let prompt = DEMO;

vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ lesson: { id: 1, prompt }, closeLesson: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  explainLesson: vi.fn(),
  explainLessonOpening: vi.fn(),
  explainLessonRest: vi.fn(),
  explainQuestion: vi.fn(),
  explainStory: vi.fn(),
  explainChat: vi.fn(),
  createSourceVideoJob: vi.fn(),
  createStoryVideoJob: vi.fn(),
  getVideoJob: vi.fn(),
  getFinderRules: vi.fn(),
}));

import { LessonView } from "@/components/chat/LessonView";
import * as api from "@/lib/api";

const never = () => new Promise<never>(() => {});
const RULES = { max_chars: 300, pii: { email: "a^", phone: "a^", url: "a^" }, distress_terms: ["hopeless"], blocked_patterns: [], blocked_terms: [] };

beforeEach(() => {
  prompt = DEMO;
  vi.mocked(api.explainLesson).mockImplementation(never);
  vi.mocked(api.explainLessonOpening).mockImplementation(never);
  vi.mocked(api.explainLessonRest).mockImplementation(never);
  vi.mocked(api.explainQuestion).mockImplementation(never);
  vi.mocked(api.explainStory).mockImplementation(never);
  vi.mocked(api.getFinderRules).mockResolvedValue(RULES);
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.clearAllMocks();
});

const noModelCalls = () => {
  for (const fn of [api.explainLesson, api.explainLessonOpening, api.explainLessonRest, api.explainQuestion, api.explainStory, api.createStoryVideoJob, api.createSourceVideoJob]) {
    expect(fn).not.toHaveBeenCalled();
  }
};

describe("a prepared lesson", () => {
  it("flag on + matching question: shows the prepared lesson and video, makes no model call and no video job", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    render(<LessonView />);
    expect(await screen.findByTestId("lesson-blocks")).toBeInTheDocument();
    expect(screen.getByTestId("block-hook")).toHaveTextContent("last time you were late");
    expect(screen.getByTestId("prepared-note")).toHaveTextContent("Prepared in advance");
    expect(screen.queryByText(/generating/i)).toBeNull();
    expect(screen.queryByRole("progressbar", { name: /video/i })).toBeNull();
    const video = screen.getByTestId("prepared-video") as HTMLVideoElement;
    expect(video.getAttribute("src")).toBe("/prepared/train-360-km.mp4");
    noModelCalls();
  });

  it("the typed text is sent nowhere: the only request is the rules GET, which takes the language", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    render(<LessonView />);
    await screen.findByTestId("lesson-blocks");
    expect(api.getFinderRules).toHaveBeenCalledTimes(1);
    expect(vi.mocked(api.getFinderRules).mock.calls[0]).toEqual(["en"]);
  });

  it("offers read aloud on the prepared lesson", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    const speak = vi.fn();
    vi.stubGlobal("speechSynthesis", { speak, cancel: vi.fn() });
    vi.stubGlobal("SpeechSynthesisUtterance", class { constructor(public text: string) {} lang = "" });
    render(<LessonView />);
    await screen.findByTestId("lesson-blocks");
    await userEvent.click(await screen.findByRole("button", { name: "Listen" }));
    expect(speak).toHaveBeenCalledTimes(1);
    expect((speak.mock.calls[0]![0] as { text: string }).text).toContain("faster train take more hours");
    vi.unstubAllGlobals();
  });

  it("flag on but the screen flags the text (distress): the normal path runs, so the server's support reply applies", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    vi.mocked(api.getFinderRules).mockResolvedValue({ ...RULES, distress_terms: ["frustrated"] });
    render(<LessonView />);
    await waitFor(() => expect(api.explainLessonOpening).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId("prepared-note")).toBeNull();
  });

  it("flag on but the rules cannot be fetched: the normal path runs", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    vi.mocked(api.getFinderRules).mockRejectedValue(new Error("down"));
    render(<LessonView />);
    await waitFor(() => expect(api.explainLessonOpening).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId("prepared-note")).toBeNull();
  });

  it("flag off (the default): a matching question runs the normal path and fetches no rules", async () => {
    render(<LessonView />);
    await waitFor(() => expect(api.explainLessonOpening).toHaveBeenCalledTimes(1));
    expect(api.explainStory).toHaveBeenCalledTimes(1);
    expect(api.getFinderRules).not.toHaveBeenCalled();
    expect(screen.queryByTestId("prepared-note")).toBeNull();
  });

  it("flag on, a similar question with other numbers: the normal path runs", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    prompt = "A train travels 480 km at a uniform speed. If the speed had been 8 km/h more, it would have taken 3 hours less. Find the speed of the train.";
    render(<LessonView />);
    await waitFor(() => expect(api.explainLessonOpening).toHaveBeenCalledTimes(1));
    expect(api.getFinderRules).not.toHaveBeenCalled();
  });
});
