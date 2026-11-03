export const landingContent = {
  metadata: {
    title: "Ask Brownie | Finds out what you know first",
    description: "Brownie finds out what you already know first, then teaches in the way that helps it click.",
  },
  brand: "Brownie",
  hero: {
    topLabel: "BROWNIE",
    topNote: "ONE TO ONE, FOR EVERYONE",
    languageLabel: "Landing page language",
    languageOptions: [
      { id: "en", label: "English" },
      { id: "hi", label: "हिन्दी" },
      { id: "ne", label: "नेपाली" },
    ],
    ask: "Ask",
    name: "Brownie",
    audienceLead: "Brownie is for",
    audiences: ["Students", "Teachers", "Professionals", "Everyone"],
    tagline: "Finds out what you know first. Then teaches.",
    description:
      "Don't understand something? You don't have to pretend you do. Ask Brownie. Take your time, ask again, and learn until it clicks. It never laughs or makes you feel uncomfortable. It adapts its explanations to what you already know and what helps.",
    tryBrownie: "Ask Brownie",
    readStory: "Read Robin's story ↓",
    signIn: "Sign in",
    explore: "Try Brownie first. Discover what's possible.",
    exploreNote: "Explore at your own pace. Sign in when you're ready to go further.",
    homepage: "Go to the Brownie homepage",
  },
  auth: {
    title: "Sign in to Brownie",
    familyCode: "Family code",
    pin: "PIN",
    signIn: "Sign in",
    loginError: "That code or PIN did not match. Try again.",
    tryAsGuest: "Try without an account",
    homepage: "Back to the Brownie homepage",
  },
  chapterOne: {
    chapter: "Chapter One",
    label: "THE NOD",
    hook: "The most dangerous word in any room is “yes.”",
    headline: "Robin nodded. But they didn’t understand.",
    paragraphs: [
      "Someone had just explained something new, maybe a teacher on fractions, maybe a manager on a tool, and asked, “Does everyone understand?” Almost everyone nodded. Robin did too.",
      "Robin had a question. Actually, several. But everyone else seemed to get it, and Robin didn’t want to be the one holding things up. So they stayed quiet.",
      "The next step built on something Robin hadn’t understood yet. Then the next. Catching up got harder every day.",
      "Eventually, Robin started believing something untrue: “Maybe I’m just not good at this.”",
      "But Robin wasn’t bad at it. They had missed one part, and nobody noticed they needed help.",
      "Now imagine someone had stopped and asked: “It’s okay if you don’t understand. Tell me which part is confusing. We’ll figure it out together.”",
    ],
    invitation: "If you’ve ever said “yes” when you meant “I don’t understand,” you know how Robin feels.",
    stats: "One room · Thirty people · One person afraid to ask · A question that never got asked",
  },
  chapterTwo: {
    chapter: "Chapter Two",
    label: "THE QUESTION",
    headlineStart: "What if learning started by understanding the learner",
    headlineEmphasis: "not just the subject?",
    paragraphs: [
      "With Brownie, Robin doesn’t have to pretend. It doesn’t expect you to know everything already, and it never minds the same question twice.",
      "Before teaching, it asks a few small questions, like:",
    ],
    questions: [
      "Have you learned about fractions before?",
      "Is the meaning confusing, or is it adding them?",
      "Would you like pictures, everyday examples, or step by step?",
    ],
    invitation: "Not sure what’s confusing? That’s okay. Brownie helps you find where it stopped making sense.",
    demoChat: {
      label: "A SAMPLE CHAT · SCRIPTED",
      disclosure: "A scripted preview. Brownie is not responding live here.",
      studentQuestion: "Why can't I just add 1/2 + 1/3 and get 2/5?",
      brownieOpening: "That’s a reasonable guess. The bottom numbers tell us the size of the pieces. Halves and thirds are different-sized pieces, so let’s rename them as sixths before adding.",
      studentLabel: "You",
      tutorLabel: "Brownie",
      followUpPrompt: "What would help next?",
      pictureChoice: "Show me with pieces",
      pictureUser: "Show me with pieces.",
      pictureExplanation: "Imagine one whole split into 6 equal pieces. One half is 3 of those pieces; one third is 2. Now the pieces are the same size, so 3/6 + 2/6 = 5/6.",
      stepsChoice: "Why can’t we add the bottoms?",
      stepsUser: "Why can’t we add the bottoms?",
      stepsExplanation: "The denominator names the size of each piece. Adding 2 + 3 would mix different-sized pieces. Split each half into 3 pieces and each third into 2, making sixths without changing the amounts: 1/2 = 3/6 and 1/3 = 2/6. Now count same-sized pieces: 3/6 + 2/6 = 5/6.",
      piecesAria: "Six equal pieces: three from one half, two from one third",
      halfLegend: "3/6 (one half)",
      thirdLegend: "2/6 (one third)",
      restart: "Restart example",
    },
    afterPanel: [
      "Not clear yet? Ask again and Brownie tries another way. It moves ahead when you’re ready, not when the textbook does. Not understanding doesn’t mean you can’t learn it. You just need it taught differently.",
    ],
    questionAria: "A scripted sample conversation about adding fractions",
  },
  chapterThree: {
    chapter: "Chapter Three",
    label: "THE CLICK",
    headlineStart: "Now Robin can see",
    headlineEnd: "what they know.",
    body: "Every session updates a map of what Robin has mastered and what needs another try. Nothing is guessed. Robin always knows what to do next, and so does Brownie.",
    chartTitle: "TOPIC MASTERY",
    chartLabel: "EXAMPLE",
    topics: [
      { id: "linear", name: "Linear equations", percent: 88 },
      { id: "quadratic", name: "Quadratic equations", percent: 72 },
      { id: "zeroes", name: "Zeroes of polynomials", percent: 54 },
      { id: "trigonometry", name: "Trigonometry", percent: 31 },
    ],
    chartAria: "Example topic mastery, not a real person's progress",
  },
  demo: {
    headlineStart: "Watch it understand",
    headlineEnd: "a real learner.",
    note: "A live session, start to finish: a learner asks, Brownie listens, then teaches.",
    dropTitle: "Drop your demo video",
    dropAccent: "here",
    dropHint: "Choose a video to preview in this browser only. It is not uploaded.",
    choose: "Choose video",
    replace: "Replace video",
    invalidFile: "Choose a video file to preview.",
    fileAria: "Select a local demo video",
    dropAria: "Choose a local video or drop it here to preview",
    playerAria: "Ask Brownie demo video",
  },
  feedback: {
    headlineStart: "How can Brownie",
    headlineEmphasis: "know you better?",
    intro: "Tell us how you like to learn, and what would make it easier. Your answer shapes Brownie for every learner after you.",
    categoryLabel: "WHAT WOULD HELP MOST?",
    categories: [
      { id: "language", label: "A language" },
      { id: "simpler", label: "A topic explained simpler" },
      { id: "feature", label: "A new feature" },
      { id: "something-else", label: "Something else" },
    ],
    messageLabel: "IN YOUR OWN WORDS",
    placeholder: "What’s hard about learning right now? What would make it click?",
    localNote: "This preview does not send or save feedback.",
    submit: "Tell Brownie",
    thanks: "Thanks for helping shape Brownie. Your feedback stays in this browser preview and hasn’t been sent.",
  },
  footer: {
    brand: "BROWNIE",
    line: "FINDS OUT WHAT YOU KNOW FIRST. THEN TEACHES.",
  },
  accessibility: {
    main: "Ask Brownie landing page",
    chapters: "The Brownie approach",
  },
} as const;

/**
 * Who Robin is in Chapter One. English only for now: Hindi and Nepali keep the original paragraph until a
 * human translator provides these (never machine-translated), so this sits outside landingContent.
 */
export const robinScenes = {
  prompt: "Who is Robin to you?",
  groupLabel: "Choose a setting for Robin's story",
  scenes: [
    {
      id: "class",
      label: "In a class",
      text: "A teacher had just explained fractions and asked, “Does everyone understand?” Almost everyone nodded. Robin did too.",
    },
    {
      id: "work",
      label: "At work",
      text: "A manager had just walked the team through a new tool and asked, “Does everyone understand?” Almost everyone nodded. Robin did too.",
    },
    {
      id: "alone",
      label: "On my own",
      text: "Robin was learning alone from a video course. The narrator asked, “Got it?” Nobody was there to answer, so Robin nodded at the screen and let the next lesson start.",
    },
  ],
} as const;

export type LandingLanguage = "en" | "hi" | "ne";

type Widen<T> = T extends string
  ? string
  : T extends number
    ? number
    : T extends readonly (infer Item)[]
      ? ReadonlyArray<Widen<Item>>
      : T extends object
        ? { [K in keyof T]: K extends "id" ? T[K] : Widen<T[K]> }
        : T;

export type LandingCopy = Widen<typeof landingContent>;