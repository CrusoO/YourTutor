/**
 * English copy for the sign-in chooser and its forms. Hindi and Nepali fall back to this English until a person
 * translates and the owner approves them (never machine-translated), the same way the rest of the app does.
 */
export const signin = {
  title: "Sign in to Brownie",
  who: "Who is signing in?",
  whoHint: "Pick the one that fits you. It only takes you to the right place.",
  back: "Choose a different way to sign in",
  roles: {
    student: { name: "Student", hint: "In school, with a family code or username and a PIN" },
    guardian: { name: "Parent or guardian", hint: "See how your child is doing. We send you a one-time code" },
    teacher: { name: "Teacher", hint: "See your classes. We send you a one-time code" },
    adult: { name: "Adult learner", hint: "College student, working professional or anyone else" },
  },
  student: {
    title: "Student sign-in",
    intro: "Type the code and PIN your guardian or teacher gave you.",
    codeLabel: "Family code",
    codeHint: "Letters and numbers. A short username from your guardian works too.",
    pinLabel: "PIN",
    submit: "Sign in",
    working: "Signing in...",
    waiting: "Getting ready...",
    haveCode: "My guardian gave me a code / Join a class",
    newHere: "I am new: start",
  },
  errors: {
    mismatch: "That code or PIN did not match. Check it and try again.",
    locked: "Too many wrong tries, so this login is paused for a while. Ask your guardian or teacher for help, or try again later.",
    slowDown: "Too many tries just now. Please wait a minute, then try again.",
    other: "We could not sign you in just now. Please try again in a moment.",
    afterRejected: "Your code and PIN were right, but your sign-in was not accepted on the next step. Please press Sign in once more.",
    afterFailed: "You are signed in, but we could not load your page just now. Please try again in a moment.",
  },
  teacherNote: "Teacher accounts are made by your school or an admin. If you cannot sign in, ask them to add you.",
  guardianNote: "New here? Your first sign-in makes your account, then you choose what to agree to.",
  adultNote: "New here? Your first sign-in makes your account. Then you say you are 18 or over and choose your class.",
  staffTitles: {
    guardian: "Parent or guardian sign-in",
    teacher: "Teacher sign-in",
    adult: "Adult learner sign-in",
    any: "Guardian and teacher sign-in",
  },
  guest: "Try without an account",
  guestHint: "Have a look first. Nothing personal is asked.",
  home: "Back to the Brownie homepage",
  draft: "Draft status",
} as const;

export type SigninRole = "student" | "guardian" | "teacher" | "adult";
