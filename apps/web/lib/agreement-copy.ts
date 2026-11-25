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

export type Role = "guardian" | "adult" | "teacher" | "child" | "reviewer";

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
    learning_profile: {
      label: "Brownie may keep simple counts of the methods my child uses and the mistakes they make.",
      detail: "Optional. Read the exact wording below before you decide.",
    },
    math_check: {
      label: "My child may send a confirmed maths expression to Brownie's server to be checked.",
      detail: "Optional. Read the exact wording below before you decide.",
    },
    photo_check: {
      label: "My child may send a photo of a maths question to Brownie's server to be read.",
      detail: "Optional. Read the exact wording below before you decide.",
    },
    ai_help_typed: {
      label: "My child may send a typed school question to an AI service when they ask for AI help.",
      detail: "Optional. Read the exact wording below before you decide.",
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
    learning_profile: {
      label: "Brownie may keep simple counts of the methods I use and the mistakes I make.",
      detail: "Optional. Read the exact wording below before you decide.",
    },
    math_check: {
      label: "I may send a confirmed maths expression to Brownie's server to be checked.",
      detail: "Optional. Read the exact wording below before you decide.",
    },
    photo_check: {
      label: "I may send a photo of a maths question to Brownie's server to be read.",
      detail: "Optional. Read the exact wording below before you decide.",
    },
    ai_help_typed: {
      label: "I may send a typed school question to an AI service when I ask for AI help.",
      detail: "Optional. Read the exact wording below before you decide.",
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
  reviewer: {
    accept_reviewer_terms: {
      label: "I have read these terms and I agree to them.",
      detail: "",
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
  reviewer: "Reviewer terms",
  child: "Before you start",
};

export const roleIntro: Record<Role, string> = {
  guardian:
    "Each box below is its own choice. The first group is what Brownie needs to work. The second group is up to you, and you can change any of it later in Settings.",
  adult:
    "Each box below is its own choice. The first group is what Brownie needs to work. The second group is up to you, and you can change any of it later in Settings.",
  teacher:
    "Please read and tick each line. These are the terms for handling student data. You can withdraw them later in Settings, and then the class views close.",
  reviewer: "Please read these terms. You must accept them to start reviewing.",
  child: "A few things to know. A grown-up you trust has to say yes before Brownie keeps anything about you.",
};

/**
 * The reviewer terms shown on the agreement page. DRAFT: the owner or a lawyer will edit this text.
 * To change it, edit it here and bump REVIEWER_VERSION in apps/api/app/auth/agreements.py: every
 * reviewer is then asked to accept again. [contact] is replaced by the API's REVIEWER_TERMS_CONTACT.
 */
export const reviewerTerms = [
  "Thank you for helping check Brownie's questions. Please read these terms. You must accept them to start reviewing.",
  "1. You are an adult (18 or over). You review as an independent person. You are not an employee of Brownie.",
  "2. Your job: read each question, check it is correct and clear, and say so honestly. Use your own judgement. Please do not talk to other reviewers about a question before you have decided.",
  "3. Keep it confidential: do not share, copy or publish the questions, answers or anything else you see here. Do not paste text from textbooks or exam papers into your notes.",
  "4. Your comments and decisions can be used by Brownie to improve its content. You do not own the content you review.",
  "5. Pay: you are paid the rate agreed with you for each question you review, by UPI, once a month, after a quality check. Some questions with deliberate mistakes are mixed in to measure quality; they are not a test of you. If you disagree with a payment, tell us within 7 days. You are responsible for your own taxes, and we may ask for your PAN.",
  "6. Your details: we keep your name, email, phone or UPI details, PAN if given, and a record of your decisions and time spent. We use them to run the review and pay you. We do not sell or share them. Ask [contact] to see, correct or delete your details.",
  "7. Safety: you will never be presented to students as a doctor, nurse or teacher unless you agree. Student reviewers are shown only as student reviewers, if at all.",
  "8. Either side can stop at any time. We may pause your access if the work does not meet the standard.",
  "By accepting, you confirm you have read and agree to these terms.",
];

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

/**
 * The scopes whose exact approved wording comes from the server (config/consent_texts) and whose
 * switch is shown in Settings. Each needs a withdrawal line here: the plain list of what is deleted
 * when it is switched off (it mirrors the server's deletion map; a test checks every id has one).
 */
export const CONSENT_TEXT_SCOPES = ["learning_profile", "math_check", "photo_check", "ai_help_typed"] as const;
export type ConsentTextScope = (typeof CONSENT_TEXT_SCOPES)[number];

export const scopeUi = {
  guardianHeading: "What you are agreeing to",
  childHeading: "What your child is told",
  showChild: "See what your child is told",
  hideChild: "Hide what your child is told",
  textVersion: "Wording version",
  textMissing: "The wording for this choice is not available right now, so it cannot be switched on.",
  switchOn: "Switch on",
  switchOff: "Switch off",
  confirmTitle: "Switch this off?",
  confirmDelete: "Switching this off will delete:",
  confirmKeep: "Keep it on",
  confirmGo: "Switch off and delete",
  status: { on: "On", off: "Off" },
  childNoticeTitle: "A note for you",
  childNoticeOk: "OK, I understand",
  childNoticeCancel: "Cancel",
};

export const withdrawal: Record<ConsentTextScope, string> = {
  learning_profile:
    "All the method and mistake counts kept for your child are deleted now. Brownie stops keeping them, and later reads find nothing.",
  math_check:
    "Nothing is stored for this choice, so there is nothing to delete. Checking a maths expression on our server stops at once.",
  photo_check:
    "Nothing is stored for this choice, so there is nothing to delete. Sending a photo to our server stops at once; reading a photo on the device still works.",
  ai_help_typed:
    "AI call records linked to your child are deleted. The Ask AI button stops sending typed questions, and your child sees the answers Brownie already has on the device.",
};
