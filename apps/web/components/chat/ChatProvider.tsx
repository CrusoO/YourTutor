"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  answerOnboarding,
  getChapterSkills,
  getChapters,
  getContextOptions,
  getFinderRules,
  guestStart,
  hasStudentToken,
  locale,
  setStaffToken,
  setToken,
  startSession,
  studentId,
  today,
  clearStudent,
  type ContextOptions,
} from "@/lib/api";
import { useCopy } from "@/lib/locale";
import { loadSetup, saveSetup } from "@/lib/chat/device";
import { markActive } from "@/lib/chat/today";
import { findTopics, prepare, type FinderRules, type Topic } from "@/lib/chat/finder";
import { currentIdentity, type Identity } from "@/lib/chat/identity";
import {
  initialState,
  reduce,
  resolveSetup,
  type ChatEvent,
  type ChatState,
  type ContextLike,
  type Role,
  type Setup,
} from "@/lib/chat/machine";
import { type Messages } from "@/lib/messages";

export type Lesson = { id: number; prompt: string };

export type Mode =
  | "learn"
  | "practise"
  | "revise"
  | "notes"
  | "class"
  | "alerts"
  | "content"
  | "progress"
  | "privacy";

export const MODES_BY_ROLE: Record<Role | "visitor", Mode[]> = {
  visitor: ["learn", "practise"],
  guest: ["learn", "practise"],
  student: ["learn", "practise", "revise", "notes"],
  teacher: ["class", "alerts", "content"],
  parent: ["progress", "privacy"],
};

/** A reply the finder or a mode produced. Memory only: never stored, never sent, gone on refresh. */
export type Reply = {
  id: number;
  kind: "matches" | "none" | "blocked" | "distress" | "pick_class" | "off" | "too_long" | "notice";
  topics?: Topic[];
  piiRemoved?: boolean;
  /** Which mode the matches belong to, so tapping a chip does the right thing. */
  mode?: Mode;
};

/** `src` is where the frame was opened and never changes while it is open; `path` follows the screen inside. */
export type Workspace = { path: string; src: string; title?: string };

export type ChatApi = {
  copy: Messages;
  hour: number | null;
  chat: ChatState;
  ctx: ContextLike | null;
  contextError: boolean;
  identity: Identity | null;
  identityReady: boolean;
  role: Role | "visitor";
  mode: Mode;
  setMode: (mode: Mode) => void;
  replies: Reply[];
  dispatch: (event: ChatEvent) => void;
  submitText: (text: string) => Promise<void>;
  pickTopic: (topic: Topic, mode: Mode) => Promise<void>;
  justTry: () => Promise<void>;
  tryOneQuestion: () => Promise<void>;
  startMode: (mode: Mode) => Promise<void>;
  signedIn: (role: Role, name?: string) => void;
  signOut: () => void;
  newChat: () => void;
  workspace: Workspace | null;
  /** The question a signed-out visitor just asked: shown as an in-depth explanation with a video. In memory only. */
  lesson: Lesson | null;
  closeLesson: () => void;
  openWorkspace: (path: string, title?: string) => void;
  closeWorkspace: () => void;
  busy: boolean;
  error: string;
};

const Ctx = createContext<ChatApi | null>(null);

export function useChatApi(): ChatApi {
  const api = useContext(Ctx);
  if (!api) throw new Error("ChatProvider is missing");
  return api;
}

function toContext(options: ContextOptions): ContextLike {
  return { grades: options.grades, curricula: options.curricula };
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const copy = useCopy();
  const [hour, setHour] = useState<number | null>(null);
  const [ctx, setCtx] = useState<ContextLike | null>(null);
  const [contextError, setContextError] = useState(false);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [identityReady, setIdentityReady] = useState(false);
  const [modeChoice, setModeState] = useState<Mode>("learn");
  const [replies, setReplies] = useState<Reply[]>([]);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const lessonSeq = useRef(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const topics = useRef<Topic[] | null>(null);
  const rules = useRef<FinderRules | null>(null);
  const replySeq = useRef(1);
  const ctxRef = useRef<ContextLike | null>(null);

  const emptyCtx: ContextLike = useMemo(() => ({ curricula: [] }), []);
  const [chat, dispatchRaw] = useReducer(
    (state: ChatState, action: { event: ChatEvent; ctx: ContextLike }) => reduce(state, action.event, action.ctx),
    undefined,
    initialState,
  );

  useEffect(() => {
    ctxRef.current = ctx;
  }, [ctx]);

  const dispatch = useCallback(
    (event: ChatEvent) => {
      if (event.type === "start_setup" && !ctx) return; // the registry has not arrived yet
      setReplies([]);
      dispatchRaw({ event, ctx: ctx ?? emptyCtx });
    },
    [ctx, emptyCtx],
  );

  useEffect(() => {
    setHour(new Date().getHours());
    getContextOptions()
      .then((options) => setCtx(toContext(options)))
      .catch(() => setContextError(true));
    currentIdentity()
      .then((who) => {
        if (who) {
          setIdentity(who);
          dispatchRaw({ event: who.role === "guest" ? { type: "guest_started" } : { type: "signed_in", role: who.role, name: who.name }, ctx: emptyCtx });
        }
      })
      .finally(() => setIdentityReady(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const role: Role | "visitor" = identity?.role ?? "visitor";
  // The composer mode follows the role: a teacher never sits in a student's "Learn" mode.
  const mode: Mode = MODES_BY_ROLE[role].includes(modeChoice) ? modeChoice : MODES_BY_ROLE[role][0]!;

  const setMode = useCallback((next: Mode) => {
    setModeState(next);
    setReplies([]);
  }, []);

  /** The panel is part of the address (?w=/path) so deep links, refresh and the back button all work. */
  const openWorkspace = useCallback((path: string, title?: string) => {
    if (path.startsWith("/session/")) markActive();
    setWorkspace({ path, src: path, title });
    try {
      window.history.pushState({ w: path }, "", `/?w=${encodeURIComponent(path)}`);
    } catch {
      /* history can be blocked; the panel still opens */
    }
  }, []);
  const closeWorkspace = useCallback(() => {
    setWorkspace(null);
    try {
      window.history.pushState({}, "", "/");
    } catch {
      /* history can be blocked */
    }
  }, []);
  /** The embedded screen moved to another page: follow it without adding a history entry. */
  const followWorkspace = useCallback((path: string) => {
    setWorkspace((current) => (current ? { ...current, path } : { path, src: path }));
    try {
      window.history.replaceState({ w: path }, "", `/?w=${encodeURIComponent(path)}`);
    } catch {
      /* history can be blocked */
    }
  }, []);

  useEffect(() => {
    const fromUrl = () => {
      const w = new URLSearchParams(window.location.search).get("w");
      setWorkspace((current) => (w && w.startsWith("/") ? (current?.path === w ? current : { path: w, src: w }) : null));
    };
    fromUrl();
    window.addEventListener("popstate", fromUrl);
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data as { type?: string; path?: string; summary?: { skill?: string; status?: string; next?: string } } | null;
      if (data?.type === "yt:nav" && typeof data.path === "string" && data.path.startsWith("/")) followWorkspace(data.path);
      if (data?.type === "yt:done") {
        markActive();
        const { skill, status, next } = data.summary ?? {};
        dispatchRaw({ event: { type: "summary", skill, status, next }, ctx: ctxRef.current ?? { curricula: [] } });
      }
    };
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("popstate", fromUrl);
      window.removeEventListener("message", onMessage);
    };
  }, [followWorkspace]);

  const loadTopics = useCallback(async (): Promise<Topic[]> => {
    if (topics.current) return topics.current;
    const sid = studentId();
    if (!sid || !hasStudentToken()) return [];
    const { chapters } = await getChapters(sid);
    const out: Topic[] = [];
    for (const chapter of chapters.filter((c) => c.live)) {
      out.push({ id: chapter.id, title: chapter.title, chapterId: chapter.id, kind: "chapter" });
      try {
        const body = await getChapterSkills(sid, chapter.id);
        for (const skill of body.skills) {
          out.push({ id: skill.id, title: skill.title, chapterId: chapter.id, kind: "skill" });
        }
      } catch {
        /* a chapter whose skills fail to load is simply not searchable */
      }
    }
    topics.current = out;
    return out;
  }, []);

  const addReply = useCallback((reply: Omit<Reply, "id">) => {
    setReplies([{ ...reply, id: replySeq.current++ }]);
  }, []);

  const startPractice = useCallback(
    async (chapterId?: string, title?: string) => {
      const sid = studentId();
      const session = await startSession("practice", sid, chapterId);
      openWorkspace(`/session/${session.id}`, title);
    },
    [openWorkspace],
  );

  const pickTopic = useCallback(
    async (topic: Topic, forMode: Mode) => {
      setBusy(true);
      setError("");
      try {
        if (forMode === "learn") openWorkspace(`/chapters/${encodeURIComponent(topic.chapterId)}`, topic.title);
        else await startPractice(topic.chapterId);
        setReplies([]);
      } catch {
        setError(copy.chatCouldNotLoad);
      } finally {
        setBusy(false);
      }
    },
    [copy, openWorkspace, startPractice],
  );

  const startMode = useCallback(
    async (target: Mode) => {
      setBusy(true);
      setError("");
      try {
        if (target === "revise") await startPractice(); // a warm-up of due cards opens the session
        else if (target === "class" || target === "alerts") openWorkspace("/teacher");
        else if (target === "progress" || target === "privacy") openWorkspace("/guardian");
      } catch {
        setError(copy.chatCouldNotLoad);
      } finally {
        setBusy(false);
      }
    },
    [copy, openWorkspace, startPractice],
  );

  const beginGuest = useCallback(
    async (setup: Setup, remember: boolean) => {
      if (!setup.board || setup.grade === undefined || !setup.subject) throw new Error("setup incomplete");
      if (remember) saveSetup(setup);
      await guestStart({
        curriculum_id: setup.board,
        grade: setup.grade,
        subject: setup.subject,
        home_language: locale(),
        device_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      setIdentity({ role: "guest" });
      dispatch({ type: "guest_started" });
      topics.current = null;
    },
    [dispatch],
  );

  /** The class used when nobody has picked one: the one saved on this device, else the first class on offer. */
  const defaultSetup = useCallback((): Setup | null => {
    const saved = loadSetup();
    if (saved?.board && saved.grade !== undefined && saved.subject) return saved;
    // Class 10 CBSE maths first: it is the class the video engine has lessons for.
    const hasClass10 = (c: ContextLike["curricula"][number]) => c.grades.some((g) => g.grade === 10 && g.subjects.length);
    const curriculum = ctx?.curricula.find((c) => c.id === "cbse" && hasClass10(c)) ?? ctx?.curricula.find((c) => c.grades.some((g) => g.subjects.length));
    const grade = curriculum?.grades.find((g) => g.grade === 10 && g.subjects.length) ?? curriculum?.grades.find((g) => g.subjects.length);
    const subject = grade?.subjects[0];
    return curriculum && grade && subject ? resolveSetup(ctx!, { board: curriculum.id, grade: grade.grade, subject: subject.id }) : null;
  }, [ctx]);

  /** The composer: a deterministic topic finder. The typed text stays in this function and is dropped. */
  const submitText = useCallback(
    async (text: string) => {
      setError("");
      if (mode === "notes" || mode === "content") return;
      if (mode !== "learn" && mode !== "practise") {
        await startMode(mode);
        return;
      }
      if (role === "visitor") {
        // Nobody is signed in: no questions first. A guest starts quietly on the default class and the prompt is answered below.
        setBusy(true);
        try {
          const setup = defaultSetup();
          if (!setup) throw new Error("no class on offer");
          await beginGuest(setup, false);
        } catch {
          setError(copy.chatCouldNotLoad);
          return;
        } finally {
          setBusy(false);
        }
      }
      if ((role === "visitor" || role === "guest") && mode === "learn") {
        const question = text.trim();
        if (!question) return;
        setReplies([]);
        setWorkspace(null);
        setLesson({ id: lessonSeq.current++, prompt: question });
        return;
      }
      try {
        if (!rules.current) rules.current = await getFinderRules(locale());
      } catch {
        addReply({ kind: "off" });
        return;
      }
      const prepared = prepare(text, rules.current);
      if (prepared.kind === "empty") return;
      if (prepared.kind === "too_long") return addReply({ kind: "too_long" });
      if (prepared.kind === "distress") return addReply({ kind: "distress" });
      if (prepared.kind === "blocked") return addReply({ kind: "blocked" });
      const list = await loadTopics();
      const found = findTopics(prepared.text, list);
      if (found.kind === "none") return addReply({ kind: "none", topics: list.filter((x) => x.kind === "chapter").slice(0, 3), piiRemoved: prepared.piiRemoved });
      // Not signed in (a visitor or a guest): teach straight away from the best match instead of asking to choose.
      if (found.topics[0]) {
        await pickTopic(found.topics[0], mode);
        return;
      }
      addReply({ kind: "matches", topics: found.topics, piiRemoved: prepared.piiRemoved, mode });
    },
    [addReply, beginGuest, copy, defaultSetup, loadTopics, mode, pickTopic, role, startMode],
  );

  const signedIn = useCallback(
    (next: Role, name?: string) => {
      setIdentity({ role: next, name });
      setModeState(MODES_BY_ROLE[next][0]!);
      topics.current = null;
      dispatch({ type: "signed_in", role: next, name });
    },
    [dispatch],
  );

  /** Register a guest silently and land on the home screen. No chapter navigation: the guest uses the
   * Composer to ask anything. If live chapters exist they are reachable via the workspace. */
  const startAsGuest = useCallback(
    async (setup: Setup, remember: boolean) => {
      setBusy(true);
      setError("");
      try {
        await beginGuest(setup, remember);
        const me = await today();
        if (me.offer === "first_run") await answerOnboarding("start_beginning");
      } catch {
        setError(copy.chatCouldNotLoad);
      } finally {
        setBusy(false);
      }
    },
    [beginGuest, copy],
  );

  /** "Just try it" — works without setup questions. Falls back to the default class so any visitor
   * (student, professional, curious adult) can start without picking a curriculum first. */
  const justTry = useCallback(async () => {
    const setup =
      chat.setup.board && chat.setup.grade !== undefined && chat.setup.subject
        ? chat.setup
        : defaultSetup();
    if (!setup) {
      setError(copy.chatCouldNotLoad);
      return;
    }
    await startAsGuest(setup, false);
  }, [chat.setup, copy, defaultSetup, setError, startAsGuest]);

  /**
   * "Try one question": no questions asked first. Uses the saved class or the first available one.
   */
  const tryOneQuestion = useCallback(async () => {
    const setup = defaultSetup();
    if (!setup) { setError(copy.chatCouldNotLoad); return; }
    return startAsGuest(setup, false);
  }, [copy, defaultSetup, setError, startAsGuest]);

  const closeLesson = useCallback(() => setLesson(null), []);

  const signOut = useCallback(() => {
    setLesson(null);
    setToken("");
    setStaffToken("");
    clearStudent();
    topics.current = null;
    setIdentity(null);
    setWorkspace(null);
    setReplies([]);
    dispatchRaw({ event: { type: "restart" }, ctx: ctx ?? emptyCtx });
  }, [ctx, emptyCtx]);

  const newChat = useCallback(() => {
    setLesson(null);
    setWorkspace(null);
    setReplies([]);
    if (identity) {
      dispatchRaw({ event: identity.role === "guest" ? { type: "guest_started" } : { type: "signed_in", role: identity.role, name: identity.name }, ctx: ctx ?? emptyCtx });
    } else {
      dispatchRaw({ event: { type: "restart" }, ctx: ctx ?? emptyCtx });
    }
  }, [ctx, emptyCtx, identity]);

  const api: ChatApi = {
    copy,
    hour,
    chat,
    ctx,
    contextError,
    identity,
    identityReady,
    role,
    mode,
    setMode,
    replies,
    dispatch,
    submitText,
    pickTopic,
    justTry,
    tryOneQuestion,
    startMode,
    signedIn,
    signOut,
    newChat,
    workspace,
    lesson,
    closeLesson,
    openWorkspace,
    closeWorkspace,
    busy,
    error,
  };
  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}
