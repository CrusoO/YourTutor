/**
 * English wording for the role agreements, the child's limited-mode start, the guardian's approval
 * screen and phone sign-in. The one place this wording lives (it is loaded only by those routes, so
 * the home page does not carry it).
 *
 * DRAFT, under legal review, not in force. The item ids match the server's catalog
 * (apps/api/app/auth/agreements.py), which also says which items are required; the wording here
 * never decides that. English only: Hindi and Nepali are never machine-translated, so these screens
 * stay English until a person translates them and a lawyer approves them.
 *
 * Rules for this file (same as legal-copy.ts):
 *  - Never invent a contact, a provider, a name or a legal claim. Whatever we do not have is PLACEHOLDER.
 *  - Never say the product does something the code does not do. We cannot yet check that a guardian is
 *    one, or that a person is 18: the text says so.
 */

import { DRAFT_BANNER, PLACEHOLDER } from "./legal-copy";

export { DRAFT_BANNER, PLACEHOLDER };

export type Role = "guardian" | "adult" | "teacher" | "child";

export type ItemCopy = { label: string; detail: string };

const SHARE_DETAIL =
  "Counts and progress only. If you tick this, a class joined with a teacher's code starts sharing at once, without asking again. If you leave it empty, you are asked for each class.";

export const items: Record<Role, Record<string, ItemCopy>> = {
  guardian: {
    confirm_guardian: {
      label: "I am this child's parent or legal guardian, and I am 18 or over.",
      detail: "We cannot check this yet. Please tick it only if it is true.",
    },
    tutoring: {
      label: "Brownie may teach my child and keep their progress.",
      detail: "Needed to use Brownie. It keeps each child's class, subject, answers and progress.",
    },
    ai_processing: {
      label: "Brownie may use AI to explain things to my child.",
      detail: `Needed to use Brownie. Parts of a lesson turn are processed by an AI model provider. Provider: ${PLACEHOLDER}.`,
    },
    teacher_share: {
      label: "My child's teacher may see my child's progress in a class my child joins.",
      detail: SHARE_DETAIL,
    },
    free_text: {
      label: "My child may type their own questions to Brownie.",
      detail: "Optional. Without it, your child picks from the choices Brownie offers.",
    },
    uploads: {
      label: "My child may upload a picture of their work.",
      detail: "Optional.",
    },
    research_pseudonymised: {
      label: "Learning data without names may be used for research.",
      detail: `Optional. Who does the research and how it is protected: ${PLACEHOLDER}.`,
    },
    progress_reports: {
      label: "Send me a weekly note about how my child is doing.",
      detail: "Optional. Sent to the email address on this account.",
    },
  },
  adult: {
    confirm_adult: {
      label: "I am 18 or over.",
      detail: "We cannot check this yet. Please tick it only if it is true.",
    },
    tutoring: {
      label: "Brownie may teach me and keep my progress.",
      detail: "Needed to use Brownie. It keeps your class, subject, answers and progress.",
    },
    ai_processing: {
      label: "Brownie may use AI to explain things to me.",
      detail: `Needed to use Brownie. Parts of a lesson turn are processed by an AI model provider. Provider: ${PLACEHOLDER}.`,
    },
    teacher_share: {
      label: "A teacher may see my progress in a class I join.",
      detail: SHARE_DETAIL.replace("asking again", "asking me again").replace("you are asked", "I am asked"),
    },
    free_text: {
      label: "I may type my own questions to Brownie.",
      detail: "Optional.",
    },
    uploads: {
      label: "I may upload a picture of my work.",
      detail: "Optional.",
    },
    research_pseudonymised: {
      label: "My learning data without my name may be used for research.",
      detail: `Optional. Who does the research and how it is protected: ${PLACEHOLDER}.`,
    },
    progress_reports: {
      label: "Send me a weekly note about how I am doing.",
      detail: "Optional. Sent to the email address on this account.",
    },
  },
  teacher: {
    terms_counts_only: {
      label: "I will use what I see about students as counts only.",
      detail: "The class views are for teaching the class, not for singling a student out.",
    },
    terms_no_sharing_codes: {
      label: "I will not share my class join codes outside my class.",
      detail: "A code lets a student ask to join. Give it only to the students of that class.",
    },
    terms_no_exporting_names: {
      label: "I will not export or copy students' names out of the app.",
      detail: "What a student chose as a label stays inside the app.",
    },
  },
  child: {
    ack_limited_mode: {
      label: "I understand that nothing about me is saved until my guardian says yes.",
      detail: "Until then it works like a guest: no saved progress and no school details.",
    },
    ack_guardian_contact: {
      label: "The phone number or email I give is my guardian's.",
      detail: "It is only used to send them one message asking if it is all right.",
    },
  },
};

export const roleTitle: Record<Role, string> = {
  guardian: "Agreement for a parent or guardian",
  adult: "Agreement for an adult learner",
  teacher: "Terms for teachers",
  child: "Before you start",
};

export const roleIntro: Record<Role, string> = {
  guardian:
    "Each box below is its own choice. The first group is what Brownie needs to work. The second group is up to you, and you can change any of it later in Settings.",
  adult:
    "Each box below is its own choice. The first group is what Brownie needs to work. The second group is up to you, and you can change any of it later in Settings.",
  teacher:
    "Please read and tick each line. These are the terms for handling student data. You can withdraw them later in Settings, and then the class views close.",
  child: "A few things to know. A grown-up you trust has to say yes before Brownie keeps anything about you.",
};

export const ui = {
  banner: DRAFT_BANNER,
  groupNeeded: "Needed to use Brownie",
  groupTeacher: "Terms",
  groupOptional: "Your choice",
  required: "required",
  optional: "optional",
  agree: "Agree and continue",
  agreeNeeds: "Tick the required boxes to continue.",
  saving: "Saving…",
  failed: "That did not save. Please try again.",
  versionChanged: "The agreement was updated. Please read it again.",
  signInFirst: "Please sign in first.",
  signInLink: "Sign in",
  noTracking: "Brownie does not track children, monitor their behaviour or target adverts at them.",
  chooseRole: "Which one are you?",
  roleGuardian: "I am a parent or guardian",
  roleAdult: "I am an adult learner (18 or over)",
  adultAgeTitle: "Your age",
  adultAgeHint:
    "Say you are 18 or over, or give your birth year. Only that answer is kept: not your day or month of birth.",
  adultDeclared: "I am 18 or over",
  adultBirthYear: "Birth year (optional)",
  adultBoard: "Board",
  adultGrade: "Class",
  adultStart: "Start learning",
  adultNotAdult: "Brownie can only open an adult profile for someone aged 18 or over. A parent or guardian can set up a profile for you.",
  adultNeedsYear: "Please tick the box, or give your birth year.",
  chooseOne: "Choose one",
};

export const settings = {
  title: "Settings: your agreements",
  intro:
    "Everything you agreed to is listed here. Untick a box to withdraw it. It takes effect at once. You can tick an optional box again whenever you like.",
  none: "You have not agreed to anything yet.",
  withdrawRequired:
    "This one is needed to use Brownie. Withdrawing it closes the consent for your learners and Brownie stops working for them until you agree again. Continue?",
  agreeAgain: "Agree again",
  back: "Back",
  version: "Agreement version",
};

export const child = {
  linkText: "Under 18? Start your own profile with a nickname",
  title: "Start with a nickname",
  intro:
    "You do not need to give your real name. Brownie works like a guest until a parent or guardian says yes.",
  nickname: "Nickname (not your real name)",
  nicknameHint: "Do not use your real name, a phone number or an email.",
  board: "Board",
  grade: "Class",
  contact: "Your parent or guardian's phone number or email",
  contactHint:
    "We send them one message with a link. They do not need an account first. Nothing about you is kept until they say yes.",
  start: "Ask my guardian",
  sent: "We sent your guardian a message.",
  pendingTitle: "Waiting for your guardian",
  pendingBody:
    "You can use Brownie like a guest while you wait. Nothing about you is saved, there is no personalised difficulty and no school is recorded.",
  approvedTitle: "Your guardian said yes",
  approvedBody: "Your profile is unlocked. Your progress is now saved.",
  expired: "The message to your guardian expired.",
  resend: "Send it again",
  ok: "OK",
  whileWaiting: "Start as a guest while I wait",
  checkAgain: "Check again",
  resent: "Sent again.",
  failed: "That did not work. Please check the details and try again.",
  noticeDown: "We could not reach your guardian. Please check the phone number or email.",
  tooMany: "Too many tries for that contact. Please wait a while.",
  off: "This is not switched on yet.",
  schoolTitle: "School name (optional)",
  schoolBody: "A school name can be added after your guardian has said yes, by you or by them.",
};

export const approve = {
  title: "A child asked for your OK",
  intro:
    "A child has asked to use Brownie with you as their guardian. Nothing about them is kept until you decide here. You do not need an account first.",
  nickname: "Nickname",
  correct: "Check the class and board. You can correct them.",
  grade: "Class",
  board: "Board",
  approve: "Say yes and agree",
  decline: "No, delete this request",
  declined: "Done. Nothing was kept about the child.",
  approved: "Thank you. Your child's profile is unlocked.",
  username: "Open your guardian page",
  invalid: "This link is not valid any more. Ask the child to send a new one.",
  noToken: "This page needs the link that was sent to you.",
  contactCaveat:
    "If you do not know this child, choose No. We cannot check who typed your contact.",
  school: "You can add the school name later in Settings, if you want to.",
};

export const login = {
  phoneLabel: "Phone number",
  phoneHint: "With the country code, for example +<code> <number>.",
  emailLabel: "Email",
  usePhone: "Use my phone number",
  useEmail: "Use my email instead",
  sendCode: "Send me a code",
  codeLabel: "Code we sent",
  verify: "Sign in",
  wrong: "That code did not work. Ask for a new one.",
  smsDown: "We could not send a text message. Try email instead, or start as a guest.",
  invalidPhone: "That phone number does not look right.",
  signupHint: "New here? The first sign-in makes your account, then you choose what to agree to.",
  usernameHint: "A child can use the short username a guardian made instead of the family code.",
};

export const loginDetails = {
  button: "Make a username and PIN",
  result: "Give these to your child. The PIN is shown only now.",
  username: "Username",
  pin: "PIN",
};
