/**
 * The interactive lesson prepared in advance for the NCERT Class 10 train problem (360 km, 5 km/h more, 1 hour less).
 * It is written by hand in the same block shapes the live lesson uses, so the same player draws it. Plain words,
 * one idea at a time, built from first principles: time = distance / speed, then the equation, then which answer to keep.
 *
 * Checked by hand and in tests: 360/40 = 9 h, 360/45 = 8 h, 360/x - 360/(x+5) = 1 gives x^2 + 5x - 1800 = (x+45)(x-40).
 * The practice bus (240 km, 20 km/h more): x^2 + 20x - 4800 = (x+80)(x-60), so 60 km/h (4 h and 3 h).
 * The spaced-review car (120 km, 10 km/h more): x^2 + 10x - 1200 = (x+40)(x-30), so 30 km/h (4 h and 3 h).
 */
import type { AiBlock } from "./ai-lesson";

export const PREPARED_TRAIN_BLOCKS: AiBlock[] = [
  {
    kind: "hook",
    text: "Think of the last time you were late and had to run. You got there sooner, because you went faster. A train works in the same way.",
    question: "On the same road, does a faster train take more hours, or fewer hours?",
  },
  {
    kind: "predict",
    prompt: "The road is 360 km long. Train A goes 40 km every hour. Train B goes 45 km every hour. Which train reaches first?",
    free_text: false,
    options: ["Train A, the slower one", "Train B, the faster one", "They reach together"],
    correct: 1,
    reveal_after: "Train B. The road is the same, and it covers more kilometres every hour, so it needs fewer hours.",
    misconceptions: ["faster means more hours", null, "speed does not change the time"],
  },
  {
    kind: "widget",
    widget_kind: "slider_sim",
    controls: [],
    what_to_notice: "Slide the speed up. The hours go down. At 40 km/h it is 9 hours. At 45 km/h it is 8 hours. Five more km/h saves exactly 1 hour.",
    spec: { variable: "speed", unit: "km/h", min: 20, max: 90, step: 5, formula: "360/speed", output_label: "Hours for 360 km", output_unit: "hours" },
  },
  {
    kind: "explain",
    text: "Here is the one idea we need. Time is the distance divided by the speed. The road is 360 km, so a train going x km every hour needs 360 ÷ x hours.",
    analogy: "If you walk 4 km every hour, a 12 km walk takes 12 ÷ 4 = 3 hours.",
  },
  {
    kind: "widget",
    widget_kind: "step_through",
    controls: [],
    what_to_notice: "Go one step at a time. Each line says the same thing as the line before it, in a new way.",
    spec: {
      steps: [
        { label: "The slow train", description: "It goes x km every hour. Its time is 360 ÷ x hours." },
        { label: "The faster train", description: "It goes (x + 5) km every hour. Its time is 360 ÷ (x + 5) hours." },
        { label: "One hour less", description: "The slow time minus the fast time is 1 hour: 360 ÷ x − 360 ÷ (x + 5) = 1." },
        { label: "Clear the fractions", description: "Multiply everything by x(x + 5). We get 360(x + 5) − 360x = x(x + 5), which is x² + 5x − 1800 = 0." },
        {
          label: "Two answers",
          description: "Split it into brackets: (x + 45)(x − 40) = 0. So x = 40, or x = −45.",
          picture: { kind: "line", min: -50, max: 50, marks: [{ at: -45, label: "−45" }, { at: 40, label: "40" }], jump: null },
        },
      ],
    },
  },
  {
    kind: "check",
    question: "Which of the two answers can be the speed of the train?",
    options: ["40 km/h", "−45 km/h", "Both, we keep them both"],
    correct: 0,
    feedback_per_option: [
      "Yes. A speed tells you how far you go in one hour, so it cannot be negative. 40 km/h works.",
      "Not this one. A train cannot go minus 45 km every hour. We leave it out.",
      "Not both. The maths gives two answers, but we keep only the one that makes sense in real life.",
    ],
    hint_ladder: ["Think of a speedometer. Can it show a number below zero?", "A speed is how many km you cover in one hour. Can you cover minus 45?"],
    misconceptions: [null, "a speed can be negative", "keeping both answers"],
  },
  {
    kind: "check",
    question: "Now check 45 km/h on the same 360 km road. How many hours does it take?",
    options: ["8 hours", "9 hours", "10 hours"],
    correct: 0,
    feedback_per_option: [
      "Yes. 360 ÷ 45 = 8 hours. That is 1 hour less than the 9 hours at 40 km/h.",
      "Not quite. 9 hours is for 40 km/h. A faster train needs fewer hours.",
      "Not quite. More speed means fewer hours, not more.",
    ],
    hint_ladder: ["Time is the distance divided by the speed.", "Try 360 ÷ 45. How many times does 45 go into 360?"],
    misconceptions: [null, "mixing up the two speeds", "faster means more hours"],
  },
  {
    kind: "transfer",
    scenario: "A bus goes 240 km. If it went 20 km/h faster, it would take 1 hour less.",
    question: "Write the first equation, the same way we did for the train. Then say which answer you keep.",
    model_answer:
      "240 ÷ x − 240 ÷ (x + 20) = 1. This becomes x² + 20x − 4800 = 0, so (x + 80)(x − 60) = 0. The answers are 60 and −80. Keep 60 km/h, because a speed is not negative. Check: 240 ÷ 60 = 4 hours and 240 ÷ 80 = 3 hours.",
  },
  {
    kind: "recap",
    three_bullets: [
      "Time is distance divided by speed. On the same road, a faster train takes fewer hours.",
      "Write the slow time minus the fast time equals 1 hour. That gives x² + 5x − 1800 = 0.",
      "The two answers are 40 and −45. A speed cannot be negative, so the train goes 40 km/h.",
    ],
    spaced_review_question: "Try this tomorrow: a car goes 120 km. At 10 km/h faster it takes 1 hour less. What is its speed?",
  },
];
