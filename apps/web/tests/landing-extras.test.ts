import { describe, expect, it } from "vitest";
import { ask, guess, notesFor, pickedChoice, remaining, START } from "../app/brownie/chat-demo";
import { chatScenarios, learningMap, storyCaptions, trust, videoDemos } from "../app/brownie/landing-extras";

describe("the guess-first chat", () => {
  for (const scenario of chatScenarios) {
    describe(scenario.tab, () => {
      const right = scenario.diagnostic.choices.filter((c) => c.correct);
      const wrong = scenario.diagnostic.choices.filter((c) => !c.correct);

      it("has exactly one right answer and at least two wrong ones that each name the idea that slipped", () => {
        expect(right).toHaveLength(1);
        expect(wrong.length).toBeGreaterThanOrEqual(2);
        for (const choice of wrong) {
          expect(choice.reply, choice.id).toMatch(/slipped/);
          expect(choice.note.state).toBe("shaky");
        }
        expect(right[0]!.note.state).toBe("solid");
      });

      it("offers two ways of being taught, each with its own note", () => {
        expect(scenario.explanations.map((e) => e.id)).toEqual(["first", "second"]);
        expect(Object.keys(scenario.preferenceNote).sort()).toEqual(["first", "second"]);
      });

      it("writes nothing down before a guess, then one note per fact learned", () => {
        expect(notesFor(scenario, START)).toEqual([]);
        const after = guess(START, wrong[0]!.id);
        expect(notesFor(scenario, after)).toEqual([wrong[0]!.note]);
        const taught = ask(after, "second");
        expect(notesFor(scenario, taught)).toEqual([wrong[0]!.note, scenario.preferenceNote.second]);
      });
    });
  }

  it("keeps the first guess and ignores a second", () => {
    const first = chatScenarios[0]!;
    const a = guess(START, first.diagnostic.choices[0]!.id);
    const b = guess(a, first.diagnostic.choices[1]!.id);
    expect(b.picked).toBe(first.diagnostic.choices[0]!.id);
    expect(pickedChoice(first, b)?.id).toBe(first.diagnostic.choices[0]!.id);
  });

  it("does not teach before a guess, and does not repeat an explanation", () => {
    const first = chatScenarios[0]!;
    expect(ask(START, "first")).toBe(START);
    const guessed = guess(START, first.diagnostic.choices[1]!.id);
    const once = ask(guessed, "first");
    expect(ask(once, "first")).toBe(once);
    expect(remaining(first, once).map((e) => e.id)).toEqual(["second"]);
    expect(remaining(first, ask(once, "second"))).toEqual([]);
  });

  it("only the student scenario carries the six-pieces drawing", () => {
    const drawn = chatScenarios.filter((s) => s.explanations.some((e) => e.drawing));
    expect(drawn.map((s) => s.id)).toEqual(["student"]);
  });
});

describe("the story captions", () => {
  it("cover every beat in every setting, and each beat's caption differs by setting where the scene differs", () => {
    for (const setting of ["class", "work", "alone"] as const) {
      expect(Object.keys(storyCaptions[setting]).sort()).toEqual(["asked", "belief", "missed", "nod", "silence"]);
    }
    expect(storyCaptions.class.nod).not.toBe(storyCaptions.work.nod);
    expect(storyCaptions.work.nod).not.toBe(storyCaptions.alone.nod);
  });
});

describe("the learning map", () => {
  it("shows a state and evidence for each topic and never a probability or a percentage", () => {
    for (const topic of learningMap.topics) {
      expect(["solid", "shaky", "unseen"]).toContain(topic.state);
      expect(topic.evidence.length).toBeGreaterThan(0);
      expect(JSON.stringify(topic)).not.toMatch(/%|percent/i);
    }
  });
});

describe("the videos and the trust answers", () => {
  it("lists three examples, each with the fields a player and a transcript need", () => {
    expect(videoDemos.map((v) => v.id)).toEqual(["student", "work", "course"]);
    for (const video of videoDemos) {
      expect(Object.keys(video).sort()).toEqual(["captions", "id", "length", "poster", "src", "summary", "tab", "title", "transcript"]);
    }
  });

  it("answers the five doubts, and marks the wording that still needs the owner's or counsel's approval", () => {
    expect(trust.items.map((i) => i.id)).toEqual(["ai", "signup", "remember", "child", "cannot"]);
    expect(trust.items.filter((i) => "pending" in i && i.pending).map((i) => i.id)).toEqual(["remember", "child"]);
  });
});
