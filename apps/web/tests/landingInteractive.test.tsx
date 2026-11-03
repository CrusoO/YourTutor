import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("../app/fonts", () => ({
  instrumentSerif: { variable: "" },
  inter: { variable: "" },
  notoSerifDevanagari: { variable: "" },
}));

import BrownieLanding from "../app/brownie/Landing";
import { VideoDemos } from "../app/brownie/LandingExtras";
import { chatScenarios, heroExtras, storyCaptions, trust, videoDemos } from "../app/brownie/landing-extras";

beforeEach(() => {
  window.localStorage.clear();
  window.history.replaceState({}, "", "/");
});
afterEach(cleanup);

const GENDERED = /\b(he|him|his|she|her|hers|boy|girl)\b/i;

describe("the English copy", () => {
  it("never gives Robin a gender or limits Robin to students", () => {
    const text = [
      heroExtras.description,
      heroExtras.note,
      ...Object.values(storyCaptions).flatMap((beats) => Object.values(beats)),
    ];
    for (const line of text) expect(line, line).not.toMatch(GENDERED);
  });

  it("does not promise what Brownie will not do, or claim something the page does not keep", () => {
    expect(heroExtras.description).not.toMatch(/never laughs|uncomfortable/i);
    expect(heroExtras.note).not.toMatch(/free/i);
  });
});

describe("the landing page in English", () => {
  it("shows the new promise, and a picture with a caption for every beat of Robin's story", () => {
    render(<BrownieLanding />);
    expect(screen.getByTestId("landing-hero-copy")).toHaveTextContent("Brownie starts with one small question");
    for (const beat of ["nod", "silence", "missed", "belief", "asked"] as const) {
      const art = screen.getByTestId(`story-art-${beat}`);
      expect(within(art).getByRole("img")).toHaveAccessibleName(storyCaptions.class[beat]);
      expect(art).toHaveTextContent(storyCaptions.class[beat]);
    }
    expect(screen.getAllByTestId("story-beat")).toHaveLength(5);
  });

  it("draws every picture in full when no scroll watcher runs, so nothing depends on an animation", () => {
    render(<BrownieLanding />);
    for (const beat of ["nod", "silence", "missed", "belief", "asked"] as const) {
      const art = screen.getByTestId(`story-art-${beat}`);
      expect(art).toHaveAttribute("data-armed", "false");
      expect(art).toHaveAttribute("data-seen", "true");
    }
  });

  it("redraws every picture and caption for the setting the reader picks", async () => {
    render(<BrownieLanding />);
    await userEvent.click(screen.getByTestId("robin-scene-work"));
    expect(screen.getByTestId("story-art-nod")).toHaveTextContent(storyCaptions.work.nod);
    expect(screen.getByTestId("story-art-asked")).toHaveTextContent(storyCaptions.work.asked);
    await userEvent.click(screen.getByTestId("robin-scene-alone"));
    expect(screen.getByTestId("story-art-nod")).toHaveTextContent(storyCaptions.alone.nod);
    expect(screen.getByTestId("robin-opening")).toHaveTextContent("learning alone");
  });

  it("asks before it explains: a wrong guess names the idea that slipped and writes a note", async () => {
    render(<BrownieLanding />);
    const chat = screen.getByTestId("demo-chat");
    const scenario = chatScenarios[0]!;
    expect(within(chat).getByTestId("demo-diagnostic")).toHaveTextContent(scenario.diagnostic.prompt);
    expect(within(chat).getByTestId("demo-notes")).toHaveTextContent("Nothing yet");
    expect(within(chat).queryByTestId("demo-reply")).toBeNull();

    const wrong = scenario.diagnostic.choices.find((c) => !c.correct)!;
    await userEvent.click(within(chat).getByTestId(`demo-choice-${wrong.id}`));
    expect(within(chat).getByTestId("demo-misconception")).toHaveTextContent("The idea that slipped");
    expect(within(chat).getByTestId("demo-reply")).toHaveTextContent(wrong.reply);
    expect(within(chat).getByTestId("demo-note-0")).toHaveTextContent("Needs another look");
    expect(within(chat).getByTestId("demo-note-0")).toHaveTextContent(wrong.note.evidence);
    expect(within(chat).queryByTestId(`demo-choice-${wrong.id}`)).toBeNull();
  });

  it("a right guess is confirmed without a slip tag, then teaches in the way asked for, with the drawing", async () => {
    render(<BrownieLanding />);
    const chat = screen.getByTestId("demo-chat");
    const scenario = chatScenarios[0]!;
    const right = scenario.diagnostic.choices.find((c) => c.correct)!;
    await userEvent.click(within(chat).getByTestId(`demo-choice-${right.id}`));
    expect(within(chat).queryByTestId("demo-misconception")).toBeNull();
    expect(within(chat).getByTestId("demo-note-0")).toHaveTextContent("Got it");

    await userEvent.click(within(chat).getByRole("button", { name: "Show me with pieces" }));
    expect(within(chat).getByTestId("demo-follow-up-first")).toHaveTextContent("3/6 + 2/6 = 5/6");
    expect(within(chat).getByTestId("fraction-pieces")).toHaveAttribute(
      "aria-label",
      "Six equal pieces: three from one half, two from one third",
    );
    expect(within(chat).getByTestId("demo-note-1")).toHaveTextContent("Asked for a picture");

    await userEvent.click(within(chat).getByRole("button", { name: /Why can.t we add the bottoms\?/ }));
    expect(within(chat).getByTestId("demo-follow-up-second")).toHaveTextContent("1/2 = 3/6");
    expect(within(chat).getByTestId("demo-try-own")).toHaveAttribute("href", "/brownie-chat");

    await userEvent.click(within(chat).getByTestId("demo-restart"));
    expect(within(chat).queryByTestId("demo-reply")).toBeNull();
    expect(within(chat).getByTestId("demo-notes")).toHaveTextContent("Nothing yet");
  });

  it("starts over when another situation is picked, and the work and coding examples are real examples", async () => {
    render(<BrownieLanding />);
    const chat = screen.getByTestId("demo-chat");
    await userEvent.click(within(chat).getByTestId(`demo-choice-${chatScenarios[0]!.diagnostic.choices[0]!.id}`));
    await userEvent.click(within(chat).getByTestId("demo-scenario-work"));
    expect(within(chat).queryByTestId("demo-reply")).toBeNull();
    expect(within(chat).getByTestId("demo-diagnostic")).toHaveTextContent("VLOOKUP");
    await userEvent.click(within(chat).getByTestId("demo-scenario-code"));
    expect(within(chat).getByTestId("demo-diagnostic")).toHaveTextContent("x = 5");
  });

  it("shows the learning map as states with evidence, never a percentage", () => {
    render(<BrownieLanding />);
    const map = screen.getByTestId("learning-map");
    expect(map).toHaveTextContent("Needs another look");
    expect(map).toHaveTextContent("Not tried yet");
    expect(map).toHaveTextContent("3 of 5 right");
    expect(map.textContent).not.toMatch(/%/);
  });

  it("shows no video picker to visitors, and a coming-soon note while no video exists", () => {
    render(<BrownieLanding />);
    expect(screen.queryByText(/Drop your demo video/)).toBeNull();
    expect(screen.queryByText("Choose video")).toBeNull();
    expect(videoDemos.every((v) => !v.src)).toBe(true);
    expect(screen.getByTestId("video-soon")).toBeInTheDocument();
  });

  it("keeps the owner's local video picker behind ?preview=1", async () => {
    window.history.replaceState({}, "", "/?preview=1");
    render(<BrownieLanding />);
    expect(await screen.findByText("Choose video")).toBeInTheDocument();
  });

  it("says in order what Brownie looks at, once, and that it is only an estimate", () => {
    render(<BrownieLanding />);
    const how = screen.getByTestId("how-it-works");
    for (const id of ["ask", "read", "teach", "check", "show"]) expect(within(how).getByTestId(`how-${id}`)).toBeInTheDocument();
    expect(how).toHaveTextContent("it can be wrong");
    // the promise is said once: the old second opening section is gone
    expect(screen.queryByText("Everyone is taught one way.")).toBeNull();
  });

  it("is honest about the languages that are not here yet, and says sorry", () => {
    render(<BrownieLanding />);
    const soon = screen.getByTestId("coming-soon");
    expect(soon).toHaveTextContent("We are sorry");
    expect(within(soon).getByTestId("soon-languages")).toHaveTextContent("Nepali lessons are not here yet");
  });

  it("answers the five doubts without any placeholder wording", () => {
    render(<BrownieLanding />);
    const section = screen.getByTestId("trust");
    for (const item of trust.items) {
      expect(within(section).getByTestId(`trust-${item.id}`)).toHaveTextContent(item.q);
    }
    expect(section).not.toHaveTextContent(/to be confirmed/i);
  });
});

describe("Hindi and Nepali", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("keep the older translated page: no new English copy, pictures, chat, map or trust section", async () => {
    // the older chart reads matchMedia, which jsdom does not provide
    vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
    window.history.replaceState({}, "", "/?lang=hi");
    render(<BrownieLanding />);
    await screen.findByTestId("landing-hero-copy");
    expect(screen.getByTestId("brownie-landing")).toHaveAttribute("lang", "hi");
    expect(screen.getByTestId("landing-hero-copy")).not.toHaveTextContent("Brownie starts with one small question");
    expect(screen.queryByTestId("story-art-nod")).toBeNull();
    expect(screen.queryByTestId("demo-notes")).toBeNull();
    expect(screen.queryByTestId("learning-map")).toBeNull();
    expect(screen.queryByTestId("trust")).toBeNull();
    expect(screen.getAllByTestId("story-beat")).toHaveLength(5);
  });
});

describe("the video demos", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows a tab and a player with captions and a transcript only for videos that exist", async () => {
    const source = videoDemos.map((v) => ({ ...v }));
    source[0]!.src = "/demo/student.mp4";
    source[0]!.captions = "/demo/student.vtt";
    source[0]!.transcript = "A learner asks a question.";
    source[1]!.src = "/demo/work.mp4";
    // the module's list is read at render time, so patch it in place for this test
    const original = videoDemos.map((v) => ({ ...v }));
    videoDemos.forEach((v, i) => Object.assign(v, source[i]));
    try {
      render(<VideoDemos />);
      expect(screen.getByTestId("video-tab-student")).toBeInTheDocument();
      expect(screen.getByTestId("video-tab-work")).toBeInTheDocument();
      expect(screen.queryByTestId("video-tab-course")).toBeNull();
      const player = document.querySelector("video")!;
      expect(player).toHaveAttribute("src", "/demo/student.mp4");
      expect(player.querySelector("track")).toHaveAttribute("src", "/demo/student.vtt");
      expect(screen.getByText("Read the transcript")).toBeInTheDocument();
      expect(screen.getByText(/AI-generated/)).toBeInTheDocument();
      await userEvent.click(screen.getByTestId("video-tab-work"));
      expect(document.querySelector("video")).toHaveAttribute("src", "/demo/work.mp4");
      expect(screen.queryByText("Read the transcript")).toBeNull();
    } finally {
      videoDemos.forEach((v, i) => Object.assign(v, original[i]));
    }
  });
});
