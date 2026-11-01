export const landingContent = {
  metadata: {
    title: "Ask Brownie | Understands you first",
    description: "Brownie understands you first, then teaches in the way that makes it click.",
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
    tagline: "Understands you first. Then teaches.",
    description:
      "Don't understand something? You don't have to pretend you do. Ask Brownie. Take your time, ask again, and learn until it clicks. It never laughs or makes you feel uncomfortable. It adapts its explanations to the way you understand.",
    tryBrownie: "Try asking Brownie",
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
  hook: {
    firstLine: "Everyone is taught one way.",
    secondLine: "You learn your way.",
    body: "Brownie first finds out what makes sense to you, then explains the next step in a way that clicks.",
    seeHow: "See how Brownie asks",
    watchDemo: "Watch the demo",
  },
  chapterOne: {
    chapter: "Chapter One",
    label: "THE NOD",
    hook: "The most dangerous word in a classroom is “yes.”",
    headline: "Robin nodded. But he didn’t understand.",
    paragraphs: [
      "The teacher had just explained fractions and asked, “Does everyone understand?” Almost everyone nodded. Robin did too.",
      "He had a question. Actually, several. But everyone else seemed to get it, and he didn’t want to be the one holding up the lesson. So he stayed quiet.",
      "The next lesson built on something Robin hadn’t understood yet. Then the next. Catching up got harder every day.",
      "Eventually, Robin started believing something untrue: “Maybe I’m just not good at maths.”",
      "But Robin wasn’t bad at maths. He had missed one part, and nobody noticed he needed help.",
      "Now imagine someone had stopped and asked him: “It’s okay if you don’t understand. Tell me which part is confusing. We’ll figure it out together.”",
    ],
    invitation: "If you’ve ever said “yes” when you meant “I don’t understand,” you know how Robin feels.",
    stats: "One classroom · Thirty students · One student afraid to ask · A question that never got asked",
  },
  chapterTwo: {
    chapter: "Chapter Two",
    label: "THE QUESTION",
    headlineStart: "What if learning started by understanding the student",
    headlineEmphasis: "not just the subject?",
    paragraphs: [
      "Remember Robin? He was afraid to admit he didn’t understand. With Brownie, he doesn’t have to pretend.",
      "Brownie doesn’t assume everyone learns at the same pace or expect you to know everything already. It never makes you feel bad for asking the same question twice.",
      "Before teaching you, Brownie asks a few small questions, like:",
    ],
    questions: [
      "Have you learned about fractions before?",
      "Is the meaning confusing, or is it adding them?",
      "Would you like pictures, everyday examples, or step by step?",
    ],
    invitation: "Not sure what’s confusing? That’s okay. Brownie helps you find where things stopped making sense. Let’s try it.",
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
      "Not clear yet? Ask again. Brownie will try another way, without making you feel you did something wrong. It doesn’t move ahead because the textbook does. It moves ahead when you’re ready.",
      "Not understanding doesn’t mean you can’t learn it. You don’t need to try harder. You just need someone to teach you differently.",
    ],
    questionAria: "A scripted sample conversation about adding fractions",
  },
  chapterThree: {
    chapter: "Chapter Three",
    label: "THE CLICK",
    headlineStart: "Now he can see",
    headlineEnd: "what he knows.",
    body: "Every session updates a map of what Robin has mastered and what needs another try. Nothing is guessed. He always knows what to do next, and so does Brownie.",
    chartTitle: "TOPIC MASTERY",
    chartLabel: "EXAMPLE",
    topics: [
      { id: "linear", name: "Linear equations", percent: 88 },
      { id: "quadratic", name: "Quadratic equations", percent: 72 },
      { id: "zeroes", name: "Zeroes of polynomials", percent: 54 },
      { id: "trigonometry", name: "Trigonometry", percent: 31 },
    ],
    chartAria: "Example topic mastery, not a real student's progress",
  },
  demo: {
    headlineStart: "Watch it understand",
    headlineEnd: "a real student.",
    note: "A live session, start to finish: a student asks, Brownie listens, then teaches.",
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
    intro: "Tell us how you like to learn, and what would make it easier. Your answer shapes Brownie for every student after you.",
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
    line: "UNDERSTANDS YOU FIRST. THEN TEACHES.",
  },
  accessibility: {
    main: "Ask Brownie landing page",
    chapters: "The Brownie approach",
  },
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