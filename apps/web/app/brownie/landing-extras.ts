/**
 * English-only landing copy that sits beside `landingContent`.
 *
 * Hindi and Nepali keep the older, fully translated text until a human translator provides these
 * (they are never machine-translated), so nothing here goes into the translation catalogue. Every
 * component that reads this module shows it only when the page language is English.
 */

export const heroExtras = {
  description:
    "Stuck on something? Ask. Brownie starts with one small question to see where you are, then explains from there, with a picture, steps or a real example, whichever works for you. Get it wrong and that is useful: Brownie shows you the exact idea that slipped.",
  note: "No sign-up needed to try it. Brownie is an AI and can make mistakes, and it says so.",
} as const;

// ── the story: one picture per beat, drawn for the setting the reader chose ───────────────────────

export type SettingId = "class" | "work" | "alone";
export type StoryBeatId = "nod" | "silence" | "missed" | "belief" | "asked";

export const storyCaptions: Record<SettingId, Record<StoryBeatId, string>> = {
  class: {
    nod: "Thirty people in a room. Almost everyone nods. One of them did not understand.",
    silence: "Robin has questions and keeps them in, because nobody else seems to need to ask.",
    missed: "One step was missed. Every step after it rests on it, so the gap grows.",
    belief: "The thought that grows: “Maybe I’m just not good at this.” It is not true.",
    asked: "Someone asks which part is confusing, and the missed step is found.",
  },
  work: {
    nod: "A team meeting. The manager asks if everyone follows. Almost everyone nods. One person did not.",
    silence: "Robin has questions about the tool and keeps them in, so as not to slow the team down.",
    missed: "One step of the tool was missed. Every task after it rests on it, so the gap grows.",
    belief: "The thought that grows: “Maybe I’m just not good at this.” It is not true.",
    asked: "Someone asks which part is confusing, and the missed step is found.",
  },
  alone: {
    nod: "One person, one screen. The video asks “Got it?” and nobody is there to answer. Robin nods anyway.",
    silence: "Robin has questions, and there is nobody to ask, so the next lesson just starts.",
    missed: "One step was missed. Every lesson after it rests on it, so the gap grows.",
    belief: "The thought that grows: “Maybe I’m just not good at this.” It is not true.",
    asked: "Something stops and asks which part is confusing, and the missed step is found.",
  },
};

// ── the sample chat: Brownie asks first, a wrong guess is useful, and it shows what it noted ──────

export type NoteState = "solid" | "shaky" | "tried";
export type Note = { label: string; state: NoteState; evidence: string };

export type ChatChoice = {
  id: string;
  text: string;
  correct: boolean;
  /** Brownie's reply to this choice. A wrong one names the idea that slipped. */
  reply: string;
  /** What Brownie writes down about the learner after this choice. */
  note: Note;
};

export type ChatScenario = {
  id: string;
  tab: string;
  topic: string;
  studentQuestion: string;
  opening: string;
  diagnostic: { prompt: string; choices: readonly ChatChoice[] };
  /** The two ways Brownie can teach it next; the first one may carry the six-pieces drawing. */
  explanations: readonly {
    id: "first" | "second";
    choice: string;
    user: string;
    text: string;
    drawing?: "pieces";
  }[];
  preferenceNote: Record<"first" | "second", Note>;
};

export const chatScenarios: readonly ChatScenario[] = [
  {
    id: "student",
    tab: "A student",
    topic: "Adding fractions",
    studentQuestion: "Why can't I just add 1/2 + 1/3 and get 2/5?",
    opening:
      "That is a reasonable thing to try, and lots of people do. Before I explain, one quick question so I start in the right place.",
    diagnostic: {
      prompt: "One pizza is cut into 2 equal slices. Another, the same size, is cut into 3 equal slices. Is one slice from each the same size?",
      choices: [
        {
          id: "same",
          text: "Yes, a slice is a slice",
          correct: false,
          reply:
            "That is the most common idea here: treating every piece as the same size. It feels right because both are “one slice”. What slipped is that the number at the bottom tells you how many pieces the whole was cut into, so more pieces means smaller pieces.",
          note: { label: "Size of a piece", state: "shaky", evidence: "Thought all pieces are the same size" },
        },
        {
          id: "smaller",
          text: "No, a slice of the 3-slice pizza is smaller",
          correct: true,
          reply: "Yes. More slices from the same pizza means each slice is smaller. That is exactly the idea that makes adding fractions work.",
          note: { label: "Size of a piece", state: "solid", evidence: "Knew more pieces means smaller pieces" },
        },
        {
          id: "bigger",
          text: "No, a slice of the 3-slice pizza is bigger",
          correct: false,
          reply:
            "That is a very common idea too: more pieces must mean bigger pieces, because the number is bigger. What slipped is that the same pizza is shared out more ways, so each share is smaller.",
          note: { label: "Size of a piece", state: "shaky", evidence: "Thought a bigger bottom number means a bigger piece" },
        },
      ],
    },
    explanations: [
      {
        id: "first",
        choice: "Show me with pieces",
        user: "Show me with pieces.",
        text: "Imagine one whole split into 6 equal pieces. One half is 3 of those pieces; one third is 2. Now the pieces are the same size, so 3/6 + 2/6 = 5/6.",
        drawing: "pieces",
      },
      {
        id: "second",
        choice: "Why can’t we add the bottoms?",
        user: "Why can’t we add the bottoms?",
        text: "The denominator names the size of each piece. Adding 2 + 3 would mix different-sized pieces. Split each half into 3 pieces and each third into 2, making sixths without changing the amounts: 1/2 = 3/6 and 1/3 = 2/6. Now count same-sized pieces: 3/6 + 2/6 = 5/6.",
      },
    ],
    preferenceNote: {
      first: { label: "How you like it explained", state: "tried", evidence: "Asked for a picture" },
      second: { label: "How you like it explained", state: "tried", evidence: "Asked for the reason, step by step" },
    },
  },
  {
    id: "work",
    tab: "At work",
    topic: "A spreadsheet lookup",
    studentQuestion: "Why does my VLOOKUP keep returning the wrong row?",
    opening: "That is a very common one, and it is rarely your fault. Before I explain, one quick question so I start in the right place.",
    diagnostic: {
      prompt: "In =VLOOKUP(A2, Prices!A:B, 2) the last part is left out. What does the formula do when it cannot find an exact match?",
      choices: [
        {
          id: "exact",
          text: "It returns nothing, because it only ever looks for an exact match",
          correct: false,
          reply:
            "That is the most common idea here: assuming the default is an exact match. It feels right because that is what you wanted. What slipped is that leaving the last part out means “approximate match”, so it quietly returns the closest value below.",
          note: { label: "VLOOKUP defaults", state: "shaky", evidence: "Assumed the default is an exact match" },
        },
        {
          id: "closest",
          text: "It assumes the list is sorted and returns the closest value below",
          correct: true,
          reply: "Yes. Left out, it means approximate match, which only works on a list sorted from smallest to largest. That is usually what has gone wrong.",
          note: { label: "VLOOKUP defaults", state: "solid", evidence: "Knew the default is an approximate match" },
        },
        {
          id: "column",
          text: "It returns the value from the first column, not the second",
          correct: false,
          reply:
            "That mixes up two things: the column it searches in and the column it returns from. What slipped is that the 2 chooses the column to return from, and the search always happens in the first column.",
          note: { label: "VLOOKUP columns", state: "shaky", evidence: "Mixed up the column searched and the column returned" },
        },
      ],
    },
    explanations: [
      {
        id: "first",
        choice: "Show me an example",
        user: "Show me an example.",
        text: "Prices sorted by name: Apple 40, Banana 20, Cherry 90. Searching “Blueberry” with the last part left out lands between Banana and Cherry, so it returns Banana’s 20, with no warning. Add FALSE at the end and it returns an error instead, which is what you want when the item is missing.",
      },
      {
        id: "second",
        choice: "Walk me through it",
        user: "Walk me through it.",
        text: "Step 1: the formula searches the first column of the table for your value. Step 2: with the last part left out, it uses approximate matching and expects that column sorted smallest to largest. Step 3: it returns the value from the column number you gave, in the row it landed on. To demand an exact match, write =VLOOKUP(A2, Prices!A:B, 2, FALSE).",
      },
    ],
    preferenceNote: {
      first: { label: "How you like it explained", state: "tried", evidence: "Asked for a worked example" },
      second: { label: "How you like it explained", state: "tried", evidence: "Asked to be walked through it" },
    },
  },
  {
    id: "code",
    tab: "Learning to code",
    topic: "What a variable is",
    studentQuestion: "Why does x = x + 1 look wrong to me?",
    opening: "It looks wrong to almost everyone the first time, because it is not how the equals sign worked in maths. One quick question first, so I start in the right place.",
    diagnostic: {
      prompt: "In a program, what does the line  x = 5  do?",
      choices: [
        {
          id: "maths",
          text: "States that x and 5 are equal, always",
          correct: false,
          reply:
            "That is the most common idea here, carried over from maths. What slipped is that in most programming languages a single = is an instruction, not a statement: it does something at that moment.",
          note: { label: "What = means in code", state: "shaky", evidence: "Read = as “is equal to, always”" },
        },
        {
          id: "box",
          text: "Puts the value 5 into a box named x",
          correct: true,
          reply: "Yes. That is the picture to keep: a box with a name, and = puts a value in it. It is also why x = x + 1 makes sense.",
          note: { label: "What = means in code", state: "solid", evidence: "Knew = stores a value" },
        },
        {
          id: "ask",
          text: "Asks whether x is 5",
          correct: false,
          reply:
            "That is a close cousin: mixing up storing a value with asking a question. What slipped is that asking is done with a different symbol, usually two equals signs, ==. A single = stores.",
          note: { label: "What = means in code", state: "shaky", evidence: "Mixed up storing a value with comparing" },
        },
      ],
    },
    explanations: [
      {
        id: "first",
        choice: "Show me an example",
        user: "Show me an example.",
        text: "x = 5 puts 5 in the box. Then x = x + 1 reads the box (5), adds 1 to get 6, and puts 6 back in the same box. Print x now and you see 6. Run the line again and you see 7.",
      },
      {
        id: "second",
        choice: "Walk me through it",
        user: "Walk me through it.",
        text: "Step 1: the computer works out the right-hand side first. Step 2: it takes the current value of x and adds 1. Step 3: it stores that result in x, replacing what was there. So it is an instruction to update x, not a claim that x equals itself plus one.",
      },
    ],
    preferenceNote: {
      first: { label: "How you like it explained", state: "tried", evidence: "Asked for a worked example" },
      second: { label: "How you like it explained", state: "tried", evidence: "Asked to be walked through it" },
    },
  },
];

export const chatUi = {
  noteTitle: "What Brownie noted",
  noteEmpty: "Nothing yet. Answer the question and see what Brownie writes down.",
  noteHelp: "This is only an example of a note. Nothing you press here is saved.",
  pickTopic: "Pick a situation",
  askNext: "How would you like it explained?",
  tryOwn: "Ask your own question",
  stateLabels: { solid: "Solid", shaky: "Shaky", tried: "Noted" } satisfies Record<NoteState, string>,
} as const;

// ── the learning map: states and evidence, never a probability ───────────────────────────────────

export const learningMap = {
  title: "WHAT BROWNIE HAS SEEN",
  label: "EXAMPLE",
  lead: "Every answer adds to a map of what Robin knows, what is shaky and what has not been tried. Each state comes with the evidence behind it.",
  caveat: "An example, not a real person. The map a signed-in learner sees comes from their own answers.",
  states: { solid: "Solid", shaky: "Shaky", unseen: "Not yet seen" },
  topics: [
    { id: "linear", name: "Linear equations", state: "solid", evidence: "Last 5 answers right, none needed a hint" },
    { id: "quadratic", name: "Quadratic equations", state: "shaky", evidence: "3 of 5 right; slips when a sign changes" },
    { id: "zeroes", name: "Zeroes of polynomials", state: "shaky", evidence: "2 of 4 right; mixes up roots and factors" },
    { id: "trigonometry", name: "Trigonometry", state: "unseen", evidence: "No answers yet" },
  ],
  aria: "Example learning map, not a real person's progress",
} as const;

// ── the videos: add a source here and its tab appears; a tab with no source is hidden ────────────

export type VideoDemo = {
  id: string;
  tab: string;
  title: string;
  summary: string;
  /** Path under /public or a public URL. Empty until the video exists. */
  src: string;
  poster: string;
  /** WebVTT captions, same rule as src. */
  captions: string;
  length: string;
  transcript: string;
};

export const videoDemos: readonly VideoDemo[] = [
  {
    id: "student",
    tab: "A student",
    title: "A student, stuck on a step",
    summary: "A learner asks, Brownie asks one question back, and finds the step that slipped.",
    src: "",
    poster: "",
    captions: "",
    length: "",
    transcript: "",
  },
  {
    id: "work",
    tab: "At work",
    title: "At work, stuck on a tool",
    summary: "A new starter is stuck on a task they were too shy to ask about, and gets unstuck.",
    src: "",
    poster: "",
    captions: "",
    length: "",
    transcript: "",
  },
  {
    id: "course",
    tab: "A company course",
    title: "A company course, built with Brownie",
    summary: "An IT onboarding lesson made with the video engine, with a check after each step.",
    src: "",
    poster: "",
    captions: "",
    length: "",
    transcript: "",
  },
];

export const videoUi = {
  heading: "See it work, three ways",
  note: "One short example each: a student, a person at work, and a company course.",
  tabs: "Choose an example video",
  captionsOn: "Captions are on by default.",
  transcript: "Read the transcript",
  disclosure: "Made with Brownie’s video engine. The voice is AI-generated.",
  soon: "Example videos are coming soon. Until then, try Brownie yourself.",
} as const;

// ── before you try it: plain answers ─────────────────────────────────────────────────────────────

export const trust = {
  title: "Before you try it",
  intro: "Short, honest answers.",
  items: [
    {
      id: "ai",
      q: "Is it a person or an AI, and can it be wrong?",
      a: "Brownie is an AI. It can make mistakes, and lessons it writes are not checked by a person, so the page says so. If something looks wrong, ask again or check with a teacher or a trusted source.",
    },
    {
      id: "signup",
      q: "Do I have to sign up?",
      a: "No. You can ask without an account. Signing in is for saving your progress.",
    },
    {
      id: "remember",
      q: "What does it remember?",
      a: "Asking without an account starts a temporary guest with no name or email. The page does not keep the text of your question, but a video made from it is stored on our server. The interactive lesson can keep a small note of your guesses on your own device, and you can clear it. What a signed-in account keeps is explained on the privacy page.",
      pending: true,
    },
    {
      id: "child",
      q: "Is it safe for a child?",
      a: "Details are on the privacy page. Brownie is built for learners in classes 6 to 12 and for adults, and it is not a replacement for a parent, a teacher or a counsellor.",
      pending: true,
    },
    {
      id: "cannot",
      q: "What can’t it do?",
      a: "It cannot replace a teacher. It does not diagnose learning difficulties. It does not check your marks or your school’s syllabus unless you sign in and set it up.",
    },
  ],
  pendingNote: "Wording to be confirmed.",
} as const;
