import type { AiLesson } from "@/lib/lessons/ai-lesson";

/** A small, valid interactive lesson used by the lesson tests (canned: no model is called). */
export const LESSON: AiLesson = {
  kind: "lesson",
  level: "school",
  objectives: ["Explain why a thicker barrier makes tunnelling rarer"],
  blocks: [
    { kind: "hook", text: "An electron can end up where it never had the energy to go.", question: "How does it get through the wall?" },
    {
      kind: "predict",
      prompt: "A ball lacks the energy to climb a hill. What happens?",
      free_text: false,
      options: ["It rolls back", "It appears on the other side"],
      correct: 0,
      reveal_after: "A ball rolls back, but an electron is a wave and behaves differently.",
      misconceptions: [null, "thinks a ball can pass through the hill"],
    },
    {
      kind: "widget",
      widget_kind: "slider_sim",
      spec: { variable: "width", unit: "nm", min: 0, max: 4, step: 0.5, formula: "exp(-2 * width)", output_label: "chance of tunnelling", output_unit: "" },
      controls: [],
      what_to_notice: "notice how the chance falls fast as the width grows",
    },
    { kind: "explain", text: "The wave shrinks inside the barrier but does not vanish.", analogy: "like a voice fading through a thick wall" },
    {
      kind: "check",
      question: "What happens to the chance if the barrier gets thicker?",
      options: ["It rises", "It falls quickly", "It stays the same", "It becomes certain"],
      correct: 1,
      feedback_per_option: ["Thicker means less wave gets through.", "Yes: the fall is very steep.", "Width matters a lot.", "It is never certain."],
      hint_ladder: ["Think about the wave inside the wall.", "The wave shrinks as it goes deeper.", "Less wave out the far side means a smaller chance."],
      misconceptions: ["thinks a thicker barrier helps", null, "thinks width does not matter", "thinks it becomes certain"],
    },
    { kind: "transfer", scenario: "Two nuclei in the Sun must get close.", question: "Why does tunnelling help the Sun shine?", model_answer: "It lets nuclei fuse without enough energy to climb the barrier." },
    { kind: "recap", three_bullets: ["Waves leak into barriers", "Thicker barriers cut the chance fast", "The Sun relies on it"], spaced_review_question: "Why does width matter so much?" },
  ],
};
