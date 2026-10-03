import localeRegistry from "../../../packages/shared/generated/locales.json";

type RegistryLocale = (typeof localeRegistry.locales)[number]["code"];
export type Locale = RegistryLocale;
const FALLBACK: Record<string, readonly string[]> = Object.fromEntries(
  localeRegistry.locales.map((row) => [row.code, row.fallback_chain as readonly string[]]),
);

const en = {
  appName: "YourTutor",
  loginTitle: "Student login",
  familyCode: "Family code",
  pin: "PIN",
  signIn: "Sign in",
  loginError: "That code or PIN did not match. Try again.",
  todayTitle: "Today",
  goal: "Today's goal",
  remaining: "Active minutes left",
  startPractice: "Start practice",
  startDiagnostic: "Start diagnostic",
  startCheckpoint: "Start checkpoint",
  resume: "Resume",
  minutes: "min",
  predict: "What do you think?",
  yes: "Yes",
  no: "No",
  continue: "Continue",
  nextStep: "Show next step",
  submit: "Check",
  hint: "Hint",
  reveal: "Show the solution",
  dontKnow: "I don't know",
  explainBack: "Explain it in your own words",
  explainContinue: "Continue",
  idleNudge: "Still there? Tap to keep going.",
  done: "Done for now",
  backToday: "Back to Today",
  similar: "Try a similar one",
  feedbackCorrect: "That's right.",
  feedbackWrong: "Not yet. Try again.",
  answerPlaceholder: "Type your answer",
  language: "Language",
};

export type Messages = typeof en;

const ne: Messages = {
  ...en,
  loginTitle: "विद्यार्थी लगइन",
  familyCode: "परिवार कोड",
  pin: "पिन",
  signIn: "लगइन",
  todayTitle: "आज",
  goal: "आजको लक्ष्य",
  remaining: "बाँकी सक्रिय मिनेट",
  startPractice: "अभ्यास सुरु",
  startDiagnostic: "डायग्नोस्टिक सुरु",
  startCheckpoint: "चेकपोइन्ट सुरु",
  resume: "जारी राख्नुहोस्",
  minutes: "मिनेट",
  continue: "अगाडि",
  hint: "संकेत",
  reveal: "हल देखाउनुहोस्",
  dontKnow: "मलाई थाहा छैन",
  idleNudge: "अझै हुनुहुन्छ? जारी राख्न थिच्नुहोस्।",
  done: "आजलाई सकियो",
  backToday: "आजमा फर्कनुहोस्",
  language: "भाषा",
};

const as: Messages = {
  ...en,
  loginTitle: "শিক্ষাৰ্থী লগইন",
  familyCode: "পৰিয়াল ক'ড",
  pin: "পিন",
  signIn: "লগইন",
  todayTitle: "আজি",
  goal: "আজিৰ লক্ষ্য",
  remaining: "বাকী সক্রিয় মিনিট",
  startPractice: "অভ্যাস আৰম্ভ",
  startDiagnostic: "ডায়েগনষ্টিক আৰম্ভ",
  startCheckpoint: "চেকপইণ্ট আৰম্ভ",
  resume: "আকৌ আৰম্ভ",
  minutes: "মিনিট",
  continue: "আগলৈ",
  hint: "ইংগিত",
  reveal: "সমাধান দেখুৱাওক",
  dontKnow: "মই নাজানো",
  idleNudge: "এতিয়াও আছে নেকি? আগলৈ যাবলৈ টিপক।",
  done: "আজিৰ বাবে শেষ",
  backToday: "আজিলৈ উভতি যাওক",
  language: "ভাষা",
};

const TABLE: Record<Locale, Messages> = { en, ne, as };

export function t(locale: Locale | string | null | undefined): Messages {
  const code = locale && FALLBACK[locale] !== undefined ? locale : localeRegistry.default;
  if (code in TABLE) {
    return TABLE[code as Locale];
  }
  for (const step of FALLBACK[code] ?? []) {
    if (step in TABLE) {
      return TABLE[step as Locale];
    }
  }
  return en;
}
