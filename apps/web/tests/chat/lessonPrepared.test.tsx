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
    expect(screen.queryByTestId("prepared-video")).toBeNull(); // the video opens when the student chooses Watch
    await userEvent.click(screen.getByTestId("mode-watch"));
    const video = screen.getByTestId("prepared-video") as HTMLVideoElement;
    expect(video.getAttribute("src")).toBe("/prepared/train-360-km.mp4");
    expect(screen.getByText(/Prepared in advance. Brownie builds videos like this/)).toBeInTheDocument();
    noModelCalls();
  });

  it("the typed text is sent nowhere: the only request is the rules GET, which takes the language", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    render(<LessonView />);
    await screen.findByTestId("lesson-blocks");
    expect(api.getFinderRules).toHaveBeenCalledTimes(1);
    expect(vi.mocked(api.getFinderRules).mock.calls[0]).toEqual(["en"]);
  });

  it("Read mode (the start): Brownie's recording for the step is there but does not start by itself; a picture sits beside the step", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    const play = vi.spyOn(window.HTMLMediaElement.prototype, "play").mockResolvedValue();
    render(<LessonView />);
    await screen.findByTestId("lesson-blocks");
    expect(screen.getByTestId("mode-read")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Brownie reading this step").getAttribute("src")).toBe("/prepared/audio/train-360-km/b0.m4a");
    expect(play).not.toHaveBeenCalled();
    expect(screen.getByTestId("art-runwalk")).toHaveAttribute("aria-label", expect.stringContaining("running"));
    play.mockRestore();
  });

  it("Listen mode: the step's recording starts by itself, the next step brings its own recording, and the video is one tap away", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    const play = vi.spyOn(window.HTMLMediaElement.prototype, "play").mockResolvedValue();
    vi.spyOn(window.HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
    render(<LessonView />);
    await screen.findByTestId("lesson-blocks");
    await userEvent.click(screen.getByTestId("mode-listen"));
    expect(play).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("listen-note")).toHaveTextContent("same voice as the video");
    await userEvent.click(screen.getByTestId("listen-to-watch"));
    expect(screen.getByTestId("prepared-video")).toBeInTheDocument();
    expect(screen.queryByTestId("step-voice")).toBeNull(); // the video has its own sound
    vi.restoreAllMocks();
  });

  it("after two wrong answers Brownie says the video is ready, and Watch opens it", async () => {
    vi.stubEnv("NEXT_PUBLIC_PREPARED_LESSONS", "true");
    render(<LessonView />);
    await screen.findByTestId("lesson-blocks");
    const next = async () => userEvent.click(screen.getByTestId("lesson-continue"));
    await next(); // the hook
    await userEvent.click(screen.getByRole("button", { name: "Train A, the slower one" })); // wrong answer 1
    expect(screen.queryByTestId("help-offer")).toBeNull();
    await next();
    await next(); // the slider
    await next(); // the idea
    await next(); // the steps
    await userEvent.click(screen.getByRole("button", { name: "−45 km/h" })); // wrong answer 2
    expect(screen.getByTestId("help-offer")).toHaveTextContent("Your video on this is ready");
    await userEvent.click(screen.getByRole("button", { name: "Watch the video" }));
    expect(screen.getByTestId("prepared-video")).toBeInTheDocument();
    expect(screen.getByTestId("mode-watch")).toHaveAttribute("aria-pressed", "true");
  }, 30_000);

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
