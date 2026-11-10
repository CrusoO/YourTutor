/**
 * English copy for /privacy, /terms and /grievance.
 *
 * DRAFT, under legal review, not in force. The data inventory below was written from the code on
 * 2026-11-11 (apps/api/app/db/models.py, auth/, llm/, video_jobs/, groups/, retention.py,
 * config/jurisdictions/, and the keys the web app stores). When the code changes, change the
 * inventory in the same pull request. English only: Hindi and Nepali are never machine-translated,
 * so these pages stay English until a person translates and a lawyer approves them.
 *
 * Rules for this file:
 *  - Never invent a contact. Every contact detail, name, date or place we do not have is PLACEHOLDER.
 *  - Never say the product does something the code does not do. Where a good notice would promise
 *    more than the code delivers, the text says "no automatic deletion yet" (or similar) and the gap
 *    is listed in the pull request.
 */

export const PLACEHOLDER = "[owner to supply]";

export const DRAFT_BANNER = "Draft: under legal review. Not yet in force.";
export const DRAFT_NOTE =
  "This page describes what the product does today, written from the code. It has not been approved by a lawyer and does not create promises yet. Where the product does not yet do what a good notice would promise, this page says so.";

export const legalLinks = [
  { id: "privacy", href: "/privacy", label: "Privacy" },
  { id: "terms", href: "/terms", label: "Terms" },
  { id: "grievance", href: "/grievance", label: "Grievance" },
] as const;

export const legalNavLabel = "Privacy, terms and grievance";

// ── the data inventory ───────────────────────────────────────────────────────────────────────────

export type DataItem = {
  id: string;
  title: string;
  /** What is kept. */
  what: string;
  /** Why. */
  why: string;
  /** Where it lives. */
  where: string;
  /** Who can see it. */
  who: string;
  /** How long it is kept: the real current rule, or "no automatic deletion yet". */
  kept: string;
  /** Does it go to anyone outside us. */
  thirdParty: string;
};

const NONE_OUTSIDE = "No. It stays with us.";
const NO_AUTO = "No automatic deletion yet.";

export const inventory: readonly DataItem[] = [
  {
    id: "guest",
    title: "A guest (no account)",
    what: "A guest has no name, email or school. We keep the class, subject and language chosen, the device time zone, a random identifier, and the practice that guest does.",
    why: "So a question can be answered and a lesson can be picked without asking who you are.",
    where: "Our database. The sign-in token for a guest stays in that browser tab.",
    who: "The guest. Staff who run the service can reach the database.",
    kept: "A command that deletes guests idle for 90 days exists (the limit comes from the region profile). It is not run automatically by the code, so today it happens only when someone runs it.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "account",
    title: "A guardian, teacher or adult account",
    what: "An email address, a role (guardian, teacher or admin), a language, and for staff an optional school or site code.",
    why: "To sign in with an emailed code, and to link a guardian to the learners they look after.",
    where: "Our database.",
    who: "The account holder. For a learner linked to a school, that school's teacher sees the learner's progress. Staff who run the service can reach the database.",
    kept: "Until the guardian deletes the family from the guardian page. No automatic deletion yet.",
    thirdParty: "The email service that sends the sign-in code can see the address (see the sign-in code row).",
  },
  {
    id: "learner",
    title: "A learner profile",
    what: "A display name, class (grade), curriculum and book, home and exam language, an optional exam date, the current chapter, a time zone, a family code, and a hashed PIN with a count of wrong attempts. For learners added by a guardian or school, the display name is whatever the adult typed.",
    why: "To pick the right lessons, to let a learner sign in with a family code and PIN, and to show a guardian how the learner is doing.",
    where: "Our database. The sign-in token and learner id are stored in the browser.",
    who: "The learner, the guardian, the learner's teacher if one is linked, and staff who run the service.",
    kept: "Until the guardian deletes the family. No automatic deletion yet.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "consent",
    title: "Consent records",
    what: "For each learner: the version of the consent text, the list of things agreed to (tutoring, sharing with a teacher, AI processing, free text, uploads, pseudonymised research), when it was granted, when it was withdrawn, and an optional reference to a paper form.",
    why: "To show what was agreed, and to switch features off when consent is missing or withdrawn.",
    where: "Our database.",
    who: "The guardian, and staff who run the service.",
    kept: "Until the family is deleted. A withdrawn consent is marked, not erased.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "code",
    title: "Sign-in codes (email one-time codes)",
    what: "The email address, a hashed code, the IP address that asked, the time, the number of attempts, and when it was used.",
    why: "To check that the person signing in controls the email address, and to slow down guessing.",
    where: "Our database. The code itself is emailed through an SMTP mail service we configure.",
    who: "Staff who run the service.",
    kept: `Codes expire after a short time but the rows are not deleted. ${NO_AUTO}`,
    thirdParty: "Yes. The mail service that delivers the email sees the address and the code. Provider: " + PLACEHOLDER + ".",
  },
  {
    id: "rate",
    title: "Rate-limit counters",
    what: "A label (for example an IP address or an email) and a time, for each request that is counted.",
    why: "To stop one person from sending too many requests.",
    where: "Our database.",
    who: "Staff who run the service.",
    kept: NO_AUTO,
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "tokens",
    title: "Sign-in sessions",
    what: "A hashed token, the role, which account it belongs to, when it was made and when it expires.",
    why: "So you stay signed in between pages.",
    where: "Our database holds the hash. The browser holds the token itself (local storage, or tab storage for a guest). One research link sets a cookie, described below.",
    who: "You, and staff who run the service.",
    kept: `Each token has an expiry time. Expired rows are not deleted. ${NO_AUTO}`,
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "practice",
    title: "Practice and progress",
    what: "Practice sessions (start, end, active time), each answer event (which question, right or wrong, hint level, how long it took), how well each skill is known, the practice schedule for revision, a record of ideas the learner mixed up, lesson results on a learning card, and an internal learner profile used to pick what comes next.",
    why: "To choose the next question, to show progress, and to find the idea that slipped.",
    where: "Our database. The learning card is also kept on the learner's own device.",
    who: "The learner and the guardian. A teacher sees it only if a teacher is linked and sharing with the teacher was agreed. Staff who run the service can reach the database.",
    kept: "Until the family is deleted (or, for a guest, the guest is deleted). No automatic deletion yet for signed-in accounts.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "safety",
    title: "Distress flags",
    what: "If a learner's own words match a distress pattern, we keep the kind of signal, where it came from, the time, and whether an adult has acknowledged it. We do not keep the words in that record.",
    why: "To pause tutoring and show support information until a guardian looks.",
    where: "Our database.",
    who: "The guardian, and staff who run the service.",
    kept: "Until the family is deleted. No automatic deletion yet.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "teacher",
    title: "Classes and teacher alerts",
    what: "A class name and the list of learners in it. If sharing with the teacher was agreed, an alert when a learner is stuck on a skill.",
    why: "So a teacher can see where a class is stuck.",
    where: "Our database.",
    who: "The teacher who owns the class, and staff who run the service.",
    kept: "Until the learner or family is deleted. No automatic deletion yet.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "report",
    title: "Weekly guardian reports",
    what: "A log that a weekly report was sent for a learner and week.",
    why: "So the same report is not sent twice.",
    where: "Our database. The report itself goes by email.",
    who: "The guardian, and staff who run the service.",
    kept: "Until the family is deleted. No automatic deletion yet.",
    thirdParty: "Yes. The mail service that delivers the email. Provider: " + PLACEHOLDER + ".",
  },
  {
    id: "ai",
    title: "Questions and chat sent to the AI",
    what: "When you ask Brownie something, the text of your question and the earlier turns of that chat (up to 20 messages) are sent to the AI service with the lesson source, the class band and the language. We do not send your name or email. If you type your name into a question, it goes too.",
    why: "To write the explanation.",
    where: "The conversation lives in your browser. The server does not keep a chat history; the browser sends it again with each message.",
    who: "The AI service while it answers. Not stored by us as chat text.",
    kept: "We do not store the text of your question. See the next row for the metadata and reply text we keep. How long the AI service itself keeps what it receives is set by its terms, which we have not yet confirmed for our account.",
    thirdParty: "Yes. Anthropic, the only AI provider in production. The terms for retention and training on our account are " + PLACEHOLDER + " to confirm.",
  },
  {
    id: "llmlog",
    title: "Record of each AI call",
    what: "For each call: the time, the purpose, the model, the class band, the language, the outcome, the number of tries, how long it took and how many tokens were used. A share of replies, set by a setting that defaults to 100%, also has the AI's reply text saved for human review. The reply can repeat words from the question.",
    why: "To pay attention to cost and quality, and to review replies.",
    where: "Our database.",
    who: "Staff who run the service and review replies.",
    kept: `Deleted with the learner's sessions when a family or guest is deleted. ${NO_AUTO} The plan is 90 days for the metadata; that job does not exist yet.`,
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "video",
    title: "Videos made on request",
    what: "A job record (which learner, status, steps, error code, file locations) and the finished video and its source list. A typed topic is held in the job only until the video program starts, then removed; a job cancelled before it starts has it removed too.",
    why: "To make and show a video.",
    where: "Our server: the database for the job and the server's disk for the files.",
    who: "The learner who asked, and staff who run the service.",
    kept: `${NO_AUTO} A queued job holds the typed topic until it starts. The finished video files are not deleted automatically.`,
    thirdParty: "The video program is our own software that runs on our server. Whether it calls any outside service (for example for speech) is " + PLACEHOLDER + " to confirm.",
  },
  {
    id: "group",
    title: "Group lessons",
    what: "A teacher or manager types a short topic (up to 300 characters) and a lesson is made and shared by a link. Each participant who chooses to send results adds right or wrong per question under a scrambled code that cannot be traced to a person or matched across groups. No name, account or address is kept.",
    why: "So a group can see where it is stuck.",
    where: "Our database.",
    who: "The person who made the group lesson, and staff who run the service.",
    kept: NO_AUTO,
    thirdParty: "The topic is used to write the lesson. The lesson is written by the same lesson writer as other lessons, which can use the AI service (see the AI row).",
  },
  {
    id: "research",
    title: "Research checkpoints (only if a school or study uses them)",
    what: "A pseudonymous code, the study group, test scores per skill, one-time links, and for paper tests the entered answers. This is used only with consent that covers research.",
    why: "To measure whether learning improved.",
    where: "Our database. A link sets a cookie that is HTTP-only and expires with the session time.",
    who: "Research staff, and staff who run the service.",
    kept: "Deleting a family does not remove these rows: the link to the learner is cut but the scores and household code remain. No automatic deletion yet.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "browser",
    title: "On your own device",
    what: "Keys in your browser storage: the sign-in token and learner id; a staff sign-in token; your language; display comfort settings (theme, text size, spacing, motion); read-aloud choice; the days you practised (up to 21); the learning card from the sample lessons; set-up choices and a dismissed tip in the chat; the landing page language; and, for offline use, a downloaded lesson pack and answers waiting to send. No advertising or analytics cookies or scripts were found in the code.",
    why: "So the app remembers you and works without a connection.",
    where: "Your browser (local storage, session storage, and for offline use the browser's app storage).",
    who: "Anyone who uses that browser.",
    kept: "Until you clear it. Clearing site data in your browser removes it.",
    thirdParty: NONE_OUTSIDE,
  },
  {
    id: "logs",
    title: "Server logs and metrics",
    what: "Operational logs of requests and errors. Optional traces are off unless switched on, and carry only names such as a rule or skill id, no personal fields.",
    why: "To keep the service working.",
    where: "Our servers and hosting provider. What the hosting provider keeps is " + PLACEHOLDER + " to confirm.",
    who: "Staff who run the service.",
    kept: "Not set by the code. " + PLACEHOLDER + " to confirm.",
    thirdParty: "Hosting provider: " + PLACEHOLDER + ".",
  },
];

// ── /privacy ─────────────────────────────────────────────────────────────────────────────────────

export const privacy = {
  title: "Privacy",
  pageTitle: "Brownie · Privacy",
  intro:
    "Brownie is a tutor that asks first and then teaches. This page says, in plain words, what we keep about you, why, who can see it, how long we keep it, and who else gets it.",
  sections: {
    short: {
      heading: "The short version",
      points: [
        "You can ask without an account. A guest has no name or email.",
        "We do not sell your data and we found no advertising or analytics code in the product.",
        "Your questions go to an AI service (Anthropic) so it can write an answer. We do not send your name or email.",
        "Some things are not deleted automatically yet. The list below says which.",
        "This is a draft and a lawyer has not approved it.",
      ],
    },
    who: {
      heading: "Who is responsible",
      body: [
        `The organisation responsible for your data (the data fiduciary under India's Digital Personal Data Protection Act, 2023): ${PLACEHOLDER}.`,
        `Where a school uses Brownie for its learners, the school decides why the data is used and Brownie works on the school's instructions. Which of these applies to you depends on how you came to Brownie: ${PLACEHOLDER} to confirm.`,
      ],
    },
    inventoryHeading: "What we keep, and why",
    inventoryIntro:
      "This list was written from the program's code, not from a wish list. Each item says what it is, why, where it lives, who can see it, how long it is kept, and whether anyone outside gets it. Where it says there is no automatic deletion yet, that is the truth today.",
    children: {
      heading: "Children and guardians (under 18)",
      body: [
        "Brownie is for learners in classes 6 to 12 and for adults. Many learners are under 18.",
        "The law in India (the Digital Personal Data Protection Act, 2023) says an organisation needs the verifiable consent of a parent or guardian before it handles a child's personal data. It also says an organisation must not track a child's behaviour, monitor it, or show a child targeted advertising, with some exceptions for education that a lawyer needs to confirm for us.",
        "What the product does today, so that you know where it stands:",
      ],
      today: [
        "A guardian signs in with an emailed code and records consent for a learner, with a version and a date. A guardian can withdraw it.",
        "There is no age check yet and no check that the adult who signs in is the learner's parent or guardian. Verifiable parental consent is therefore not in place for learners who join on their own.",
        "There is no advertising and we found no third-party tracking in the code.",
        "Brownie does record what a learner answers and how well each skill is known, to choose the next question. That is a form of tracking of learning behaviour. Whether and how this is allowed for children, directly or through a school, is a question for our lawyer. Until then do not treat this page as saying it is allowed.",
        "A guest is treated like a minor in the product and has no name, email or school.",
        "Voice, uploads and free text are controlled by consent scopes. We have not confirmed in this draft which of them are switched on in production.",
      ],
      note: "If you are under 18, please ask a parent or guardian to read this page with you.",
    },
    rights: {
      heading: "Your rights",
      body: [
        "Under the Act you can ask to see what we hold, correct it, and have it erased, and you can complain to us first and then to the Data Protection Board. A guardian can use these rights for a child.",
        "What works today: a signed-in guardian can download a short export of the account, its learners and their consents, and can delete the family, which removes the learners' practice, progress and AI-call records. A guest cannot download or delete from the app.",
        "What does not work yet: the export does not include practice sessions, answers, progress or learning cards. Deleting does not yet remove sign-in code records for the email, research checkpoint results, or video files. See the list above. Until these are fixed, write to us and we will do it by hand: see the Grievance page.",
      ],
    },
    changes: {
      heading: "Changes and dates",
      body: [`Effective date: ${PLACEHOLDER}. Version: draft.`, "We will change this page before it comes into force and say what changed."],
    },
    contact: {
      heading: "Questions and complaints",
      body: ["Use the grievance page. It says what to send and who answers."],
    },
  },
  fieldLabels: {
    what: "What",
    why: "Why",
    where: "Where it lives",
    who: "Who can see it",
    kept: "How long we keep it",
    thirdParty: "Does it go to anyone outside us",
  },
} as const;

// ── /terms ───────────────────────────────────────────────────────────────────────────────────────

export const terms = {
  title: "Terms of use",
  pageTitle: "Brownie · Terms",
  intro: "These are the rules for using Brownie, in plain words. They are a draft and do not apply yet.",
  sections: [
    {
      id: "what",
      heading: "What Brownie is",
      body: [
        "Brownie is an AI tutor. It asks a question first, then explains. It is a help for learning. It is not a school, a teacher or an exam board.",
        `The service is run by ${PLACEHOLDER}.`,
      ],
    },
    {
      id: "wrong",
      heading: "Answers can be wrong",
      body: [
        "An AI can make mistakes. Where it is possible, we check a maths answer by calculation. Not everything can be checked that way, and a check can miss a mistake.",
        "If something looks wrong, ask your teacher, a parent or a book. Do not rely on Brownie alone for an exam, a school task or any decision that matters.",
      ],
    },
    {
      id: "teacher",
      heading: "Not a substitute for a teacher",
      body: ["Brownie does not replace a teacher, a parent, a doctor, or a counsellor. It does not diagnose learning difficulties and it does not mark your school work."],
    },
    {
      id: "emergency",
      heading: "Not an emergency service",
      body: [
        "Brownie cannot call anyone for you and nobody watches the chat live. If you or someone near you is in danger, contact your local emergency number or a trusted adult now.",
        `Helpline numbers for support lines: ${PLACEHOLDER}. We do not list any number here until the owner has confirmed it with the provider.`,
      ],
    },
    {
      id: "age",
      heading: "Age and guardians",
      body: [
        "If you are under 18, a parent or guardian should agree before you use Brownie with an account. Brownie asks the guardian to record consent. Today the product cannot check who the adult is, so please only do this with a real parent or guardian.",
        "A guardian can look at the learner's progress, withdraw consent and ask for the learner's data to be deleted.",
      ],
    },
    {
      id: "use",
      heading: "Using Brownie properly",
      body: ["Please do not:"],
      list: [
        "give someone else's details, or pretend to be someone else;",
        "try to break, overload or get into parts of the service you were not given;",
        "use Brownie to cheat in a live exam, or to make content that harms or bullies someone;",
        "type private details such as phone numbers, addresses or passwords into a question;",
        "copy the service's content in bulk or sell it.",
      ],
    },
    {
      id: "stop",
      heading: "Stopping and changes",
      body: ["You can stop using Brownie at any time. We may change or stop the service, or an account that breaks these rules. We will change these terms before they come into force and say what changed."],
    },
    {
      id: "limit",
      heading: "Limits on what we are responsible for",
      body: [
        `For counsel: ${PLACEHOLDER}. This section is deliberately short. A lawyer will write the limit of liability, the governing law and where disputes are heard.`,
        "Nothing here takes away rights that the law gives you.",
      ],
    },
    {
      id: "contact",
      heading: "Contact",
      body: ["Use the grievance page."],
    },
  ],
} as const;

// ── /grievance ───────────────────────────────────────────────────────────────────────────────────

export const grievance = {
  title: "Grievance and data requests",
  pageTitle: "Brownie · Grievance",
  intro:
    "If you are unhappy about how your data is handled, or you want to see, correct or erase it, tell us here. A guardian can write for a child.",
  contact: {
    heading: "Who to write to",
    fields: [
      { id: "officer", label: "Grievance officer (name)", value: PLACEHOLDER },
      { id: "email", label: "Email", value: PLACEHOLDER },
      { id: "address", label: "Postal address", value: PLACEHOLDER },
      { id: "phone", label: "Phone", value: PLACEHOLDER },
      { id: "hours", label: "Hours", value: PLACEHOLDER },
    ],
    note: "These are placeholders on purpose. We do not publish a contact until the owner has supplied and checked it.",
  },
  send: {
    heading: "What to send",
    list: [
      "Who you are. If you write for a child, say you are the parent or guardian and which learner.",
      "The email address or family code on the account, so we can find it. Do not send a password or a PIN.",
      "What you want: to see your data, correct it, erase it, withdraw consent, or make a complaint.",
      "What went wrong, and when, in a few lines.",
    ],
  },
  process: {
    heading: "What happens next",
    steps: [
      "We write back to say we have your message.",
      `We check who you are, so that your data does not go to someone else. For a child we ask for the guardian's email on the account.`,
      "We do what you asked, or tell you why we cannot, in plain words.",
      "If you are not satisfied, you can complain to the Data Protection Board of India, after you have written to us first.",
    ],
    time: {
      label: "Expected time to reply",
      value: PLACEHOLDER,
    },
  },
  today: {
    heading: "Doing it by hand for now",
    body: [
      "Some requests cannot be done from the app yet (a full export of practice records, a guest's data, or sign-in code and research records). We do them by hand. Tell us what you need and we will say honestly what we can and cannot do.",
    ],
  },
} as const;
