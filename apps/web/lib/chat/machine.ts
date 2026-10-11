/**
 * The conversation as a pure state machine (UI-1). No I/O, no React, no clock: given a state, an event and
 * the registry's options it returns the next state. The screen only renders it.
 *
 * Phases: welcome (greeting, role unknown) -> context (setup chips) -> identity (sign in, just try it,
 * save progress, create account) -> home (role cards). Nothing the visitor types is ever stored here:
 * the composer is a topic finder outside this module, and messages hold choices, never free text.
 */

export type Role = "guest" | "student" | "teacher" | "parent";
export type Phase = "welcome" | "context" | "identity" | "home";
export type SetupStep = "grade" | "state" | "board" | "medium" | "subject";

/** What the registry offers, in the shape of GET /context/options (plus optional lists). */
export type ContextLike = {
  grades?: number[];
  states?: { id: string; titles?: Record<string, string> }[];
  curricula: {
    id: string;
    titles?: Record<string, string>;
    states?: string[];
    grades: {
      grade: number;
      subjects: { id: string; books: { id: string; medium: string | null }[] }[];
    }[];
  }[];
};

export type Setup = {
  grade?: number;
  state?: string;
  board?: string;
  medium?: string;
  subject?: string;
};

export type IdentityView =
  | "choices"
  | "sign_in"
  | "save_progress"
  | "parent"
  | "teacher"
  | "create_account";

export type MsgKey =
  | "ask_grade"
  | "ask_state"
  | "ask_board"
  | "ask_medium"
  | "ask_subject"
  | "user_choice"
  | "identity_intro"
  | "signed_in"
  | "guest_started"
  | "restart";

export type Msg = {
  id: number;
  from: "tutor" | "user" | "system";
  key: MsgKey;
  /** Choices only (step and value), never typed text. */
  data?: { step?: SetupStep; value?: string | number; name?: string };
};

export type ChatState = {
  phase: Phase;
  role: Role | null;
  setup: Setup;
  identity: IdentityView;
  /** Which activity the visitor asked for on the welcome cards; the first activity opens this one. */
  intent: "lesson" | "practice" | null;
  messages: Msg[];
  nextId: number;
};

export type Option = { value: string; label?: string; available: boolean };

export type ChatEvent =
  | { type: "start_setup"; intent: "lesson" | "practice" | null }
  | { type: "pick"; step: SetupStep; value: string }
  | { type: "identity"; view: IdentityView }
  | { type: "signed_in"; role: Role; name?: string }
  | { type: "guest_started" }
  | { type: "restart" };

export const initialState = (): ChatState => ({
  phase: "welcome",
  role: null,
  setup: {},
  identity: "choices",
  intent: null,
  messages: [],
  nextId: 1,
});

const ORDER: SetupStep[] = ["grade", "state", "board", "medium", "subject"];

const unique = <T,>(values: T[]): T[] => [...new Set(values)];

function boardsFor(ctx: ContextLike, setup: Setup) {
  return ctx.curricula.filter((c) => {
    if (setup.state && c.states && !c.states.includes(setup.state)) return false;
    return true;
  });
}

function booksFor(ctx: ContextLike, setup: Setup) {
  const boards = setup.board ? ctx.curricula.filter((c) => c.id === setup.board) : boardsFor(ctx, setup);
  return boards.flatMap((c) =>
    c.grades
      .filter((g) => setup.grade === undefined || g.grade === setup.grade)
      .flatMap((g) => g.subjects.flatMap((s) => s.books.map((b) => ({ ...b, subject: s.id, board: c.id })))),
  );
}

/** The options for one step. `available: false` means no live content yet ("coming soon"). */
export function stepOptions(ctx: ContextLike, setup: Setup, step: SetupStep): Option[] {
  if (step === "grade") {
    const withContent = new Set(ctx.curricula.flatMap((c) => c.grades.map((g) => g.grade)));
    const all = unique([...(ctx.grades ?? []), ...withContent]).sort((a, b) => a - b);
    return all.map((g) => ({ value: String(g), available: withContent.has(g) }));
  }
  if (step === "state") {
    return (ctx.states ?? []).map((s) => ({
      value: s.id,
      available: ctx.curricula.some((c) => !c.states || c.states.includes(s.id)),
    }));
  }
  if (step === "board") {
    return boardsFor(ctx, setup).map((c) => ({
      value: c.id,
      available: setup.grade === undefined || c.grades.some((g) => g.grade === setup.grade),
    }));
  }
  if (step === "medium") {
    const media = unique(booksFor(ctx, setup).flatMap((b) => (b.medium ? [b.medium] : [])));
    return media.map((m) => ({ value: m, available: true }));
  }
  const subjects = unique(booksFor(ctx, setup).map((b) => b.subject));
  return subjects.map((s) => ({ value: s, available: true }));
}

/** Does this step need asking? A step with no options (no states in the registry) or only one is skipped. */
function needed(ctx: ContextLike, setup: Setup, step: SetupStep): boolean {
  const options = stepOptions(ctx, setup, step);
  if (step === "grade" || step === "board" || step === "subject") return options.length > 0;
  return options.length > 1; // state and medium only when there is a real choice
}

/** The next question to ask, or null when setup is complete. */
export function nextStep(ctx: ContextLike, setup: Setup): SetupStep | null {
  for (const step of ORDER) {
    if (setup[step] !== undefined) continue;
    if (needed(ctx, setup, step)) return step;
    // A skipped step with exactly one option is filled in silently so later steps can narrow by it.
    const only = stepOptions(ctx, setup, step);
    if ((step === "state" || step === "medium") && only.length === 1) {
      return nextStep(ctx, { ...setup, [step]: only[0]!.value });
    }
  }
  return null;
}

/** The setup with silently-skipped single-option steps filled in. */
export function resolveSetup(ctx: ContextLike, setup: Setup): Setup {
  let current = { ...setup };
  for (const step of ORDER) {
    if (current[step] !== undefined) continue;
    const options = stepOptions(ctx, current, step);
    if ((step === "state" || step === "medium") && options.length === 1) {
      current = { ...current, [step]: options[0]!.value };
    }
  }
  return current;
}

const ASK: Record<SetupStep, MsgKey> = {
  grade: "ask_grade",
  state: "ask_state",
  board: "ask_board",
  medium: "ask_medium",
  subject: "ask_subject",
};

function push(state: ChatState, msg: Omit<Msg, "id">): ChatState {
  return {
    ...state,
    messages: [...state.messages, { ...msg, id: state.nextId }],
    nextId: state.nextId + 1,
  };
}

/** After a choice: ask the next question, or move on to identity when setup is complete. */
function advance(state: ChatState, ctx: ContextLike): ChatState {
  const step = nextStep(ctx, state.setup);
  if (step) return push({ ...state, phase: "context" }, { from: "tutor", key: ASK[step] });
  return push(
    { ...state, phase: "identity", identity: "choices", setup: resolveSetup(ctx, state.setup) },
    { from: "tutor", key: "identity_intro" },
  );
}

export function reduce(state: ChatState, event: ChatEvent, ctx: ContextLike): ChatState {
  switch (event.type) {
    case "start_setup": {
      if (state.phase !== "welcome" && state.phase !== "home") return state;
      const fresh = { ...initialState(), intent: event.intent, nextId: state.nextId, messages: state.messages };
      return advance(fresh, ctx);
    }
    case "pick": {
      if (state.phase !== "context" && state.phase !== "identity") return state;
      // Only the question being asked, or an earlier answer being changed.
      const asking = nextStep(ctx, state.setup);
      if (asking !== event.step && state.setup[event.step] === undefined) return state;
      // Choosing a step clears every later one, so changing an answer never leaves stale choices.
      const later = ORDER.slice(ORDER.indexOf(event.step) + 1);
      const base = Object.fromEntries(
        Object.entries(state.setup).filter(([k]) => k !== event.step && !later.includes(k as SetupStep)),
      ) as Setup;
      const option = stepOptions(ctx, base, event.step).find((o) => o.value === event.value);
      if (!option || !option.available) return state; // "coming soon" cannot start
      const value = event.step === "grade" ? Number(event.value) : event.value;
      const setup = resolveSetup(ctx, { ...base, [event.step]: value } as Setup);
      const chosen = push(
        { ...state, setup, phase: "context", identity: "choices" },
        { from: "user", key: "user_choice", data: { step: event.step, value } },
      );
      return advance(chosen, ctx);
    }
    case "identity": {
      if (state.phase !== "identity" && state.phase !== "welcome" && state.phase !== "home") return state;
      const next: ChatState = { ...state, phase: state.phase === "home" ? "home" : "identity", identity: event.view };
      // Opening sign-in straight from the welcome screen still needs a message to hang the card on.
      const hasIntro = state.messages.some((m) => m.key === "identity_intro");
      return state.phase === "welcome" && !hasIntro ? push(next, { from: "tutor", key: "identity_intro" }) : next;
    }
    case "signed_in": {
      return push(
        { ...state, phase: "home", role: event.role, identity: "choices" },
        { from: "tutor", key: "signed_in", data: { name: event.name } },
      );
    }
    case "guest_started": {
      return push({ ...state, phase: "home", role: "guest", identity: "choices" }, { from: "system", key: "guest_started" });
    }
    case "restart": {
      return push({ ...initialState(), nextId: state.nextId, messages: [] }, { from: "system", key: "restart" });
    }
  }
}

/** The number of taps from a fresh welcome screen to the identity step, for the "five taps" check. */
export function tapsToIdentity(ctx: ContextLike, picks: Record<SetupStep, string | undefined>): number {
  let state = reduce(initialState(), { type: "start_setup", intent: "lesson" }, ctx);
  let taps = 1;
  while (state.phase === "context") {
    const step = nextStep(ctx, state.setup);
    if (!step) break;
    const value = picks[step] ?? stepOptions(ctx, state.setup, step).find((o) => o.available)?.value;
    if (value === undefined) break;
    state = reduce(state, { type: "pick", step, value }, ctx);
    taps += 1;
  }
  return taps;
}
