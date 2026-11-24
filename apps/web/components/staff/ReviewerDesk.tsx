"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError, decideDesk, deskErrors, deskItems, whoAmI, type DeskCard, type DeskDecision, type DeskOther } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  allYes,
  buildBody,
  emptyDraft,
  formatClock,
  keyAction,
  median,
  missingNotes,
  moveBlocked,
  nextUnanswered,
  placeServerErrors,
  problemsFor,
  tickSeconds,
  type Draft,
  type Problem,
} from "@/lib/reviewDesk";
import { desk } from "@/lib/reviewDeskCopy";

type Lang = "en" | "hi" | "ne";
type Result = { decision: DeskDecision; card: DeskCard };

const DOT: Record<string, string> = {
  approve: "bg-success",
  fix: "bg-warning",
  reject: "bg-danger",
  skip: "bg-muted",
};

/** The reviewer desk: a queue, and one question at a time with five checks. The API is the authority on every rule. */
export default function ReviewerDesk() {
  const [cards, setCards] = useState<DeskCard[]>([]);
  const [total, setTotal] = useState(0);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [idx, setIdx] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [seconds, setSeconds] = useState<Record<string, number>>({});
  const [results, setResults] = useState<Record<string, Result>>({});
  const [lang, setLang] = useState<Lang>("en");
  const [showAnswer, setShowAnswer] = useState(false);
  const [paused, setPaused] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [toast, setToast] = useState("");
  const [role, setRole] = useState("");
  const [focusId, setFocusId] = useState("");
  const [reviewing, setReviewing] = useState(false); // looking at one question from the summary
  const pausedRef = useRef(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const say = useCallback((text: string) => {
    setToast(text);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 2400);
  }, []);

  const load = useCallback(async (offset: number) => {
    try {
      const data = await deskItems(offset);
      setCards((rows) => (offset === 0 ? data.items : [...rows, ...data.items]));
      setTotal(data.total);
      setState("ready");
      return data.items.length;
    } catch {
      setState("error");
      return 0;
    }
  }, []);

  useEffect(() => {
    void load(0);
    whoAmI()
      .then((me: { role?: string }) => setRole(me.role ?? ""))
      .catch(() => setRole(""));
    return () => clearTimeout(toastTimer.current);
  }, [load]);

  const isDone = useCallback(
    (card: DeskCard) => Boolean(card.my_decision) || Boolean(results[card.id]),
    [results],
  );
  const card = cards[idx] as DeskCard | undefined;
  const decided = card ? Boolean(card.my_decision) || (results[card.id] ? results[card.id].decision !== "skip" : false) : false;
  const doneCount = cards.filter(isDone).length;
  const everyDone = cards.length > 0 && doneCount === cards.length;
  const allDone = everyDone && !reviewing;
  const draft = card ? drafts[card.id] ?? emptyDraft() : emptyDraft();
  const cardSeconds = card ? seconds[card.id] ?? 0 : 0;

  // start on the first question that still needs a decision
  const started = useRef(false);
  useEffect(() => {
    if (state !== "ready" || started.current || !cards.length) return;
    started.current = true;
    const first = cards.findIndex((c) => !c.my_decision);
    setIdx(first >= 0 ? first : 0);
  }, [state, cards]);

  // the timer: a second counts only while this question is open, not paused and the tab is visible
  const currentId = card?.id;
  useEffect(() => {
    if (!currentId || decided || allDone) return;
    const timer = setInterval(() => {
      setSeconds((all) => ({
        ...all,
        [currentId]: tickSeconds(all[currentId] ?? 0, { paused: pausedRef.current, hidden: document.hidden }),
      }));
    }, 1000);
    return () => clearInterval(timer);
  }, [currentId, decided, allDone]);

  useEffect(() => {
    if (!focusId) return;
    document.getElementById(focusId)?.focus();
    setFocusId("");
  }, [focusId, draft]);

  const patch = useCallback(
    (change: (d: Draft) => Draft) => {
      if (!card) return;
      setDrafts((all) => ({ ...all, [card.id]: change(all[card.id] ?? emptyDraft()) }));
      setProblems([]);
    },
    [card],
  );

  function setCheck(i: number, yes: boolean) {
    if (!card || decided) return;
    patch((d) => ({ ...d, checks: d.checks.map((c, j) => (j === i ? yes : c)) }));
    if (!yes) setFocusId(`fix-note-${i}`);
  }

  function answerNext(yes: boolean) {
    const n = nextUnanswered(draft);
    if (n >= 0) setCheck(n, yes);
  }

  function go(to: number) {
    if (moveBlocked(draft)) {
      patch((d) => ({ ...d, tried: true }));
      say(desk.toastNoMove);
      const first = missingNotes(draft)[0];
      setFocusId(`fix-note-${first}`);
      return;
    }
    setIdx(to);
    setLang("en");
    setShowAnswer(false);
    setProblems([]);
    setReviewing(true);
  }

  function next(after: number, updated: Record<string, Result>) {
    const open = (c: DeskCard, i: number) => !c.my_decision && !updated[c.id] && i !== after;
    const n = cards.findIndex((c, i) => i > after && open(c, i));
    const any = cards.findIndex((c, i) => open(c, i));
    const target = n >= 0 ? n : any;
    if (target >= 0) {
      setIdx(target);
      setLang("en");
      setShowAnswer(false);
    }
    window.scrollTo?.({ top: 0 });
  }

  async function decide(decision: DeskDecision) {
    if (!card || decided || busy) return;
    const found = problemsFor(decision, draft);
    if (found.length) {
      patch((d) => ({ ...d, tried: true }));
      setProblems(found);
      const note = found.find((p) => p.field === "fix_notes" && p.question !== undefined);
      if (decision === "approve") say(desk.toastNeedYes);
      else if (note?.question !== undefined) {
        say(desk.toastWriteFix(desk.checks[note.question]));
        setFocusId(`fix-note-${note.question}`);
      } else say(found[0].message);
      return;
    }
    setBusy(true);
    setProblems([]);
    try {
      const saved = await decideDesk(card.id, buildBody(card, decision, draft, cardSeconds));
      const updated = { ...results, [card.id]: { decision, card: saved } };
      setResults(updated);
      setReviewing(false);
      setCards((rows) => rows.map((r) => (r.id === saved.id ? saved : r)));
      say(
        { approve: desk.toastApproved, fix: desk.toastFix, reject: desk.toastReject, skip: desk.toastSkip }[decision],
      );
      if (decision !== "skip" && saved.others.length) say(desk.toastOthers(saved.others.length));
      next(idx, updated);
    } catch (error) {
      const server = deskErrors(error);
      if (server.length) setProblems(placeServerErrors(server));
      else
        setProblems([
          {
            field: "form",
            message: error instanceof ApiError && error.status === 409 ? desk.stale : desk.failed,
          },
        ]);
    } finally {
      setBusy(false);
    }
  }

  // keys: kept in a ref so the one listener always sees the latest state
  const keyHandler = useRef<(event: KeyboardEvent) => void>(() => {});
  keyHandler.current = (event) => {
    const target = event.target as HTMLElement | null;
    const tag = target?.tagName?.toUpperCase();
    if ((tag === "TEXTAREA" || tag === "INPUT") && event.key === "Escape") {
      target?.blur();
      return;
    }
    const action = keyAction(event.key, target, { ctrl: event.ctrlKey, meta: event.metaKey, alt: event.altKey });
    if (!action) return;
    event.preventDefault(); // so a key that moves focus to a note box does not also type its letter there
    if (action.kind === "help") return setHelpOpen(true);
    if (action.kind === "escape") return setHelpOpen(false);
    if (helpOpen || !card || allDone || decided) return;
    if (action.kind === "answer") answerNext(action.yes);
    else if (action.kind === "decide") void decide(action.decision);
    else if (action.kind === "toggleAnswer") setShowAnswer((v) => !v);
    else if (action.kind === "reason") patch((d) => ({ ...d, reason: action.code }));
  };
  useEffect(() => {
    const listener = (event: KeyboardEvent) => keyHandler.current(event);
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  function togglePause() {
    const now = !paused;
    pausedRef.current = now;
    setPaused(now);
    say(now ? desk.paused : desk.running);
  }

  async function nextBatch() {
    const before = cards.length;
    const got = await load(before);
    if (got > 0) {
      setIdx(before);
      started.current = true;
    }
  }

  const lastLook = everyDone && reviewing;
  const error = (field: string, question?: number) =>
    problems.filter((p) => p.field === field && p.question === question);
  const nextIndex = () => {
    const open = cards.findIndex((c, i) => i > idx && !isDone(c));
    return open >= 0 ? open : Math.min(idx + 1, cards.length - 1);
  };
  const generalProblems = problems.filter(
    (p) => p.field === "form" || (p.field === "fix_notes" && p.question === undefined) || p.field === "checks",
  );

  if (state === "loading") return <main className="stack" data-testid="desk-loading"><p>{desk.loading}</p></main>;
  if (state === "error")
    return (
      <main className="stack" data-testid="desk-error">
        <p role="alert">{desk.loadFailed}</p>
      </main>
    );

  return (
    <main className="mx-auto w-full max-w-6xl pb-44 sm:pb-32" data-testid="reviewer-desk">
      <header className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-line py-3">
        <h1 className="m-0 text-xl font-bold">{desk.title}</h1>
        <span className="flex-1" />
        <span className="text-sm text-muted">
          {desk.timeThis}{" "}
          <span className="font-mono tabular-nums text-ink" data-testid="desk-clock">
            {formatClock(cardSeconds)}
          </span>
        </span>
        <Button variant="outline" size="sm" onClick={togglePause} aria-pressed={paused} data-testid="desk-pause">
          {paused ? desk.resume : desk.pause}
        </Button>
        <Button variant="outline" size="sm" onClick={() => setHelpOpen(true)} aria-label={desk.keysLabel}>
          {desk.keys}
        </Button>
        {role === "admin" ? (
          <Link href="/staff/review/reviewers" className="text-sm">
            {desk.adminLink}
          </Link>
        ) : null}
      </header>

      {cards.length === 0 ? (
        <p className="mt-6" data-testid="desk-empty">
          {desk.empty}
        </p>
      ) : (
        <>
          <nav aria-label={desk.queueLabel} className="flex flex-wrap items-center gap-2 py-3" data-testid="desk-queue">
            {cards.map((c, i) => {
              const r = results[c.id];
              const decision = c.my_decision?.decision ?? r?.decision;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => go(i)}
                  aria-current={i === idx ? "true" : undefined}
                  className={cn(
                    "flex min-h-11 w-auto items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1 text-sm font-medium text-ink",
                    i === idx && "border-accent shadow-[0_0_0_2px_var(--c-accent-soft)]",
                  )}
                >
                  <span className={cn("size-2.5 rounded-full bg-line", decision && DOT[decision])} aria-hidden />
                  {desk.question(i + 1)}
                  {decision ? <span className="sr-only"> ({desk.decisionWords[decision] ?? decision})</span> : null}
                </button>
              );
            })}
            <span className="text-sm text-muted" data-testid="desk-progress">
              {desk.doneCount(doneCount, cards.length)}
            </span>
          </nav>

          <ol className="mb-4 flex list-none flex-wrap gap-x-6 gap-y-2 rounded-xl bg-accent-soft px-4 py-3 text-sm" data-testid="desk-howto">
            {desk.how.map(([bold, rest], i) => (
              <li key={bold} className="flex items-center gap-2">
                <span className="grid size-5 place-items-center rounded-full bg-accent text-xs font-semibold text-accent-fg" aria-hidden>
                  {i + 1}
                </span>
                <span>
                  <b>{bold}</b> {rest}
                </span>
              </li>
            ))}
          </ol>

          {allDone ? (
            <Summary cards={cards} results={results} seconds={seconds} more={cards.length < total} onMore={() => void nextBatch()} onOpen={go} />
          ) : card ? (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
              <StudentView card={card} lang={lang} setLang={setLang} showAnswer={showAnswer} setShowAnswer={setShowAnswer} />
              <section className="rounded-2xl border border-line bg-surface p-4" aria-labelledby="your-check">
                <h2 id="your-check" className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
                  {desk.yourCheck}
                </h2>
                <ComputerBox state={card.verification.state} />
                <p className="my-3 rounded-xl border border-line bg-surface-2 p-3 text-sm text-muted">{desk.cannot}</p>
                {decided ? (
                  <DecidedView card={results[card.id]?.card ?? card} />
                ) : (
                  <>
                    {desk.checks.map((text, i) => (
                      <CheckRow
                        key={i}
                        index={i}
                        text={text}
                        value={draft.checks[i]}
                        current={i === nextUnanswered(draft)}
                        note={draft.notes[i] ?? ""}
                        tried={draft.tried}
                        problems={error("fix_notes", i)}
                        onAnswer={(yes) => setCheck(i, yes)}
                        onNote={(value) => patch((d) => ({ ...d, notes: d.notes.map((n, j) => (j === i ? value : n)) }))}
                      />
                    ))}
                    {draft.checks.some((c) => c === false) || problems.some((p) => p.field === "severity" || p.field === "reason_code") ? (
                      <ReasonPicker
                        draft={draft}
                        reasonError={error("reason_code")}
                        severityError={error("severity")}
                        onReason={(code) => patch((d) => ({ ...d, reason: code }))}
                        onSeverity={(value) => patch((d) => ({ ...d, severity: value }))}
                      />
                    ) : null}
                    <div className="mt-4">
                      <label htmlFor="general-note" className="text-sm font-normal text-muted">
                        {desk.generalNote}
                      </label>
                      <textarea
                        id="general-note"
                        rows={3}
                        value={draft.note}
                        placeholder={desk.generalNotePlaceholder}
                        onChange={(e) => patch((d) => ({ ...d, note: e.target.value }))}
                        aria-invalid={error("note").length > 0}
                        aria-describedby={error("note").length ? "general-note-error" : undefined}
                      />
                      {error("note").map((p) => (
                        <p key={p.message} id="general-note-error" role="alert" className="mt-1 text-sm font-medium text-danger">
                          {p.message}
                        </p>
                      ))}
                    </div>
                  </>
                )}
                <OthersPanel card={results[card.id]?.card ?? card} visible={decided} />
              </section>
            </div>
          ) : null}
        </>
      )}

      {cards.length > 0 && !allDone && card ? (
        <ActionBar
          draft={draft}
          decided={decided}
          busy={busy}
          problems={generalProblems}
          onDecide={(d) => void decide(d)}
          lastLook={lastLook}
          onNext={() => (lastLook ? setReviewing(false) : go(nextIndex()))}
        />
      ) : null}

      <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-28 z-30 flex justify-center px-4">
        {toast ? (
          <span className="rounded-xl bg-ink px-4 py-2 text-sm text-surface" data-testid="desk-toast">
            {toast}
          </span>
        ) : null}
      </div>

      {helpOpen ? <Help onClose={() => setHelpOpen(false)} /> : null}
    </main>
  );
}

function ComputerBox({ state }: { state: "verified" | "unchecked" | "mismatch" }) {
  const tone = { verified: "border-success bg-success-soft text-success", unchecked: "border-warning bg-warning-soft text-warning", mismatch: "border-danger bg-danger-soft text-danger" }[state];
  const head = { verified: desk.computerOk, unchecked: desk.computerUnchecked, mismatch: desk.computerMismatch }[state];
  const more = { verified: desk.computerOkMore, unchecked: desk.computerUncheckedMore, mismatch: desk.computerMismatchMore }[state];
  return (
    <div className={cn("rounded-xl border p-3 text-sm font-medium", tone)} data-testid="desk-computer" data-state={state}>
      {head}
      <small className="mt-0.5 block font-normal text-ink">{more}</small>
    </div>
  );
}

function StudentView({
  card,
  lang,
  setLang,
  showAnswer,
  setShowAnswer,
}: {
  card: DeskCard;
  lang: Lang;
  setLang: (l: Lang) => void;
  showAnswer: boolean;
  setShowAnswer: (v: boolean) => void;
}) {
  const choices = useMemo(() => {
    const right = { id: card.answer, text: card.answer_text ?? card.answer, right: true };
    const wrong = card.wrong_options.map((o) => ({ id: o.answer, text: o.text, right: false }));
    return [right, ...wrong].sort((a, b) => a.id.localeCompare(b.id));
  }, [card]);
  const hindi = card.hindi.stem;
  return (
    <section className="rounded-2xl border border-line bg-surface p-4" aria-labelledby="student-view" data-testid="desk-student">
      <h2 id="student-view" className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
        {desk.studentView}
      </h2>
      <Tabs value={lang} onValueChange={(v) => setLang(v as Lang)}>
        <TabsList aria-label={desk.studentView}>
          {(["en", "hi", "ne"] as const).map((k) => (
            <TabsTrigger key={k} value={k}>
              {desk.tabs[k]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      {lang === "en" ? (
        <div className="mt-3">
          <p className="mb-2 flex flex-wrap gap-x-3 text-xs text-muted">
            <span className="font-mono">{card.id}</span>
            {card.skill_ids.length ? <span className="font-mono">{card.skill_ids.join(", ")}</span> : null}
            <span>{card.type}</span>
          </p>
          <p className="my-0 mb-3 text-lg" data-testid="desk-stem">
            {card.stem}
          </p>
          <ul className="m-0 mb-3 grid list-none gap-2 p-0">
            {choices.map((c) => (
              <li
                key={c.id}
                className={cn(
                  "flex items-center gap-3 rounded-xl border border-line px-3 py-2",
                  showAnswer && c.right && "border-success bg-success-soft",
                )}
                data-right={showAnswer && c.right ? "true" : undefined}
              >
                <span className="grid size-6 flex-none place-items-center rounded-full border border-line font-mono text-xs text-muted">{c.id}</span>
                <span>{c.text}</span>
                {showAnswer && c.right ? <span className="ml-auto rounded-full bg-surface px-2 py-0.5 text-xs font-semibold text-success">{desk.rightAnswer}</span> : null}
              </li>
            ))}
          </ul>
          <label className="mb-3 flex flex-row items-center gap-3 text-sm font-normal text-muted">
            <input
              type="checkbox"
              role="switch"
              className="size-5 min-h-0 w-5"
              checked={showAnswer}
              onChange={(e) => setShowAnswer(e.target.checked)}
            />
            <span>
              {desk.showAnswer} <kbd className="font-mono">(E)</kbd>
            </span>
          </label>
          {card.hints.length ? (
            <details className="border-t border-line py-2">
              <summary className="cursor-pointer text-sm font-medium">{desk.hints(card.hints.length)}</summary>
              <ol className="mt-2 pl-5">
                {card.hints.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ol>
            </details>
          ) : null}
          {card.solution_steps.length ? (
            <details className="border-t border-line py-2">
              <summary className="cursor-pointer text-sm font-medium">{desk.steps}</summary>
              <ol className="mt-2 pl-5">
                {card.solution_steps.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ol>
            </details>
          ) : null}
          {card.wrong_options.length ? (
            <details open className="border-t border-line py-2">
              <summary className="cursor-pointer text-sm font-medium">{desk.wrongChoices}</summary>
              <ul className="mt-2 list-none space-y-1 p-0 text-sm">
                {card.wrong_options.map((o) => (
                  <li key={o.answer}>
                    <span className="font-mono text-muted">({o.answer})</span>{" "}
                    <b>{o.misconceptions.join(", ") || desk.noMistakeNamed}</b>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : lang === "hi" && hindi ? (
        <p className="mt-3 text-lg" lang="hi" data-testid="desk-hindi">
          {hindi}
        </p>
      ) : (
        <div className="mt-3 rounded-xl border border-dashed border-line bg-surface-2 p-4 text-sm text-muted" data-testid="desk-no-translation">
          <b>{desk.noTranslation(desk.languageNames[lang === "hi" ? "hi" : "ne"])}</b>
          <br />
          {desk.noTranslationHelp(desk.languageNames[lang === "hi" ? "hi" : "ne"])}
        </div>
      )}
    </section>
  );
}

function CheckRow({
  index,
  text,
  value,
  current,
  note,
  tried,
  problems,
  onAnswer,
  onNote,
}: {
  index: number;
  text: string;
  value: boolean | null;
  current: boolean;
  note: string;
  tried: boolean;
  problems: Problem[];
  onAnswer: (yes: boolean) => void;
  onNote: (value: string) => void;
}) {
  const short = note.replace(/\s/g, "").length < 8;
  const bad = (tried && short) || problems.length > 0;
  return (
    <div data-testid={`check-${index}`}>
      <div className={cn("grid grid-cols-1 items-center gap-2 rounded-xl border border-transparent p-2 sm:grid-cols-[1fr_auto]", current && "border-accent bg-accent-soft")}>
        <span id={`check-text-${index}`} className="text-sm">
          {text}
        </span>
        <span className="flex gap-2" role="group" aria-labelledby={`check-text-${index}`}>
          <button
            type="button"
            aria-pressed={value === true}
            onClick={() => onAnswer(true)}
            className={cn("min-h-11 w-auto min-w-20 rounded-lg border border-line bg-surface px-3 text-sm text-ink", value === true && "border-success bg-success-soft font-semibold text-success")}
          >
            {desk.yes} <span className="font-mono text-xs opacity-70">Y</span>
          </button>
          <button
            type="button"
            aria-pressed={value === false}
            onClick={() => onAnswer(false)}
            className={cn("min-h-11 w-auto min-w-20 rounded-lg border border-line bg-surface px-3 text-sm text-ink", value === false && "border-warning bg-warning-soft font-semibold text-warning")}
          >
            {desk.needsFix} <span className="font-mono text-xs opacity-70">N</span>
          </button>
        </span>
      </div>
      {value === false ? (
        <div
          className={cn("mb-3 ml-3 mt-1 rounded-r-xl border-l-4 border-warning bg-warning-soft p-2", bad && "border-danger bg-danger-soft")}
          data-testid={`fix-note-box-${index}`}
          data-state={bad ? "bad" : "ok"}
        >
          <label htmlFor={`fix-note-${index}`} className="mb-1 text-sm">
            {desk.fixLabel}
          </label>
          <textarea
            id={`fix-note-${index}`}
            rows={2}
            value={note}
            placeholder={desk.placeholders[index]}
            onChange={(e) => onNote(e.target.value)}
            aria-required="true"
            aria-invalid={bad}
            aria-describedby={`fix-hint-${index}`}
            className={cn(bad && "border-danger")}
          />
          <p id={`fix-hint-${index}`} role={bad ? "alert" : undefined} className={cn("mt-1 text-sm", bad ? "font-medium text-danger" : "text-ink")}>
            {problems.length ? problems[0].message : bad ? desk.fixHintBad : desk.fixHint}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function ReasonPicker({
  draft,
  reasonError,
  severityError,
  onReason,
  onSeverity,
}: {
  draft: Draft;
  reasonError: Problem[];
  severityError: Problem[];
  onReason: (code: string) => void;
  onSeverity: (v: "blocker" | "must_fix" | "nice_to_fix") => void;
}) {
  return (
    <div className="mt-3" data-testid="desk-reasons">
      <p className="text-sm text-muted">{desk.reasonIntro}</p>
      <div role="group" aria-label={desk.reasonGroup} className="my-2 flex flex-wrap gap-2">
        {desk.reasons.map(([code, label]) => (
          <button
            key={code}
            type="button"
            aria-pressed={draft.reason === code}
            onClick={() => onReason(code)}
            className={cn("flex min-h-11 w-auto items-center gap-2 rounded-full border border-line bg-surface px-3 text-sm text-ink", draft.reason === code && "border-accent bg-accent-soft text-accent-ink")}
          >
            <kbd className="font-mono text-xs text-muted">{code}</kbd>
            {label}
          </button>
        ))}
      </div>
      {reasonError.map((p) => (
        <p key={p.message} role="alert" className="text-sm font-medium text-danger">
          {p.message}
        </p>
      ))}
      <div role="group" aria-label={desk.severityGroup} className="my-2">
        <p className="mb-1 text-sm font-semibold">{desk.severityGroup}</p>
        <div className="flex flex-wrap gap-2">
          {desk.severities.map(([key, label, help]) => (
            <button
              key={key}
              type="button"
              aria-pressed={draft.severity === key}
              onClick={() => onSeverity(key)}
              className={cn("min-h-11 w-auto rounded-xl border border-line bg-surface px-3 py-1 text-left text-sm text-ink", draft.severity === key && "border-accent bg-accent-soft text-accent-ink")}
            >
              <b>{label}</b>
              <span className="block text-xs font-normal opacity-80">{help}</span>
            </button>
          ))}
        </div>
      </div>
      {severityError.map((p) => (
        <p key={p.message} role="alert" className="text-sm font-medium text-danger">
          {p.message}
        </p>
      ))}
    </div>
  );
}

function ActionBar({
  draft,
  decided,
  busy,
  problems,
  lastLook,
  onDecide,
  onNext,
}: {
  draft: Draft;
  decided: boolean;
  busy: boolean;
  problems: Problem[];
  lastLook: boolean;
  onDecide: (d: DeskDecision) => void;
  onNext: () => void;
}) {
  const done = nextUnanswered(draft) === -1;
  const canApprove = done && allYes(draft);
  const missing = missingNotes(draft).length > 0;
  const status = decided
    ? desk.statusDecided
    : missing
      ? desk.statusMissingNote
      : canApprove
        ? desk.statusCanApprove
        : done
          ? desk.statusFixOrReject
          : desk.statusAnswerFirst;
  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))] pt-3" data-testid="desk-actions">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2">
        {decided ? (
          <Button variant="outline" onClick={onNext}>
            {lastLook ? desk.backToSummary : desk.nextQuestion}
          </Button>
        ) : (
          <>
            <Button
              onClick={() => onDecide("approve")}
              disabled={!canApprove || busy}
              className="bg-success text-surface"
              data-testid="act-approve"
            >
              {desk.approve} <kbd className="font-mono text-xs opacity-80">A</kbd>
            </Button>
            <Button variant="outline" onClick={() => onDecide("fix")} disabled={busy} className="border-warning text-warning" data-testid="act-fix">
              {desk.fix} <kbd className="font-mono text-xs opacity-80">F</kbd>
            </Button>
            <Button variant="outline" onClick={() => onDecide("reject")} disabled={busy} className="border-danger text-danger" data-testid="act-reject">
              {desk.reject} <kbd className="font-mono text-xs opacity-80">R</kbd>
            </Button>
            <Button variant="outline" onClick={() => onDecide("skip")} disabled={busy} data-testid="act-skip">
              {desk.skip} <kbd className="font-mono text-xs opacity-80">S</kbd>
            </Button>
          </>
        )}
        <span className="min-w-0 flex-1 basis-48 text-sm text-muted" data-testid="desk-status">
          {busy ? desk.saving : status}
        </span>
      </div>
      {problems.length ? (
        <ul role="alert" className="mx-auto mt-2 max-w-6xl list-none p-0 text-sm font-medium text-danger" data-testid="desk-problems">
          {problems.map((p) => (
            <li key={p.message}>{p.message}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function DecidedView({ card }: { card: DeskCard }) {
  const mine = card.my_decision;
  if (!mine) return <p data-testid="desk-decided">{desk.decidedLine(desk.decisionWords.skip)}</p>;
  return (
    <div data-testid="desk-decided">
      <h3 className="mb-1 text-base font-semibold">{desk.decidedTitle}</h3>
      <p className="my-1">{desk.decidedLine(desk.decisionWords[mine.decision] ?? mine.decision)}</p>
      <DecisionDetail row={{ reviewer: "", decision: mine.decision, note: mine.note, severity: mine.severity, reason_code: mine.reason_code, checks: mine.checks, fix_notes: mine.fix_notes }} />
    </div>
  );
}

function DecisionDetail({ row }: { row: DeskOther }) {
  const reason = desk.reasons.find(([code]) => code === row.reason_code)?.[1];
  const severity = desk.severities.find(([key]) => key === row.severity)?.[1];
  return (
    <ul className="m-0 list-none space-y-1 p-0 text-sm">
      {severity || reason ? (
        <li>
          {[severity, reason].filter(Boolean).join(" · ")}
        </li>
      ) : null}
      {(row.fix_notes ?? []).map((n) => (
        <li key={n.question_index}>
          <b>{desk.checks[n.question_index] ?? `Question ${n.question_index + 1}`}</b> {n.text}
        </li>
      ))}
      {row.note ? <li>{row.note}</li> : null}
    </ul>
  );
}

/** Other reviewers, only after you decided: the API sends nothing before that, and this panel never asks for it. */
function OthersPanel({ card, visible }: { card: DeskCard; visible: boolean }) {
  if (!visible) {
    return (
      <p className="mt-4 text-sm text-muted" data-testid="desk-blind">
        {desk.hiddenUntil}
      </p>
    );
  }
  return (
    <div className="mt-4 border-t border-line pt-3" data-testid="desk-others">
      <h3 className="mb-1 text-base font-semibold">{desk.othersTitle}</h3>
      {card.approvals !== null ? (
        <p className="my-1 text-sm text-muted" data-testid="desk-approvals">
          {desk.othersCount(card.approvals, card.approvals_needed)}
          {card.blocked ? ` · ${desk.blockedNow}` : ""}
        </p>
      ) : null}
      {card.others.length === 0 ? (
        <p className="text-sm text-muted">{desk.othersNone}</p>
      ) : (
        <ul className="m-0 list-none space-y-3 p-0">
          {card.others.map((o) => (
            <li key={o.reviewer} className="rounded-xl bg-surface-2 p-3 text-sm">
              <b>{o.reviewer}</b> {desk.decisionWords[o.decision] ?? o.decision}
              <DecisionDetail row={o} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Summary({
  cards,
  results,
  seconds,
  more,
  onMore,
  onOpen,
}: {
  cards: DeskCard[];
  results: Record<string, Result>;
  seconds: Record<string, number>;
  more: boolean;
  onMore: () => void;
  onOpen: (index: number) => void;
}) {
  const decisionOf = (c: DeskCard) => results[c.id]?.decision ?? c.my_decision?.decision ?? "";
  const count = (d: string) => cards.filter((c) => decisionOf(c) === d).length;
  const times = cards.filter((c) => results[c.id]).map((c) => seconds[c.id] ?? 0);
  return (
    <section className="rounded-2xl border border-line bg-surface p-4" data-testid="desk-summary" aria-labelledby="all-done">
      <h2 id="all-done" className="mb-3 text-xl font-bold">
        {desk.allDone}
      </h2>
      <div className="flex flex-wrap gap-3">
        {(
          [
            ["approve", desk.statApproved],
            ["fix", desk.statFix],
            ["reject", desk.statReject],
            ["skip", desk.statSkip],
          ] as const
        ).map(([key, label]) => (
          <div key={key} className="rounded-xl bg-surface-2 px-4 py-2" data-testid={`stat-${key}`}>
            <b className="block text-2xl">{count(key)}</b>
            <span className="text-sm text-muted">{label}</span>
          </div>
        ))}
        <div className="rounded-xl bg-surface-2 px-4 py-2">
          <b className="block font-mono text-2xl">{formatClock(median(times))}</b>
          <span className="text-sm text-muted">{desk.statTime}</span>
        </div>
      </div>
      <p className="my-3 text-sm text-muted">{desk.summaryNote}</p>
      <ul className="m-0 list-none space-y-2 p-0">
        {cards.map((c, i) => (
          <li key={c.id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className={cn("size-2.5 rounded-full bg-line", DOT[decisionOf(c)])} aria-hidden />
            <span>{desk.question(i + 1)}</span>
            <span className="text-muted">{desk.decisionWords[decisionOf(c)] ?? ""}</span>
            <button type="button" className="ml-auto min-h-11 w-auto px-3 text-sm" onClick={() => onOpen(i)}>
              {desk.summaryOpen}
            </button>
          </li>
        ))}
      </ul>
      {count("skip") ? <p className="text-sm text-muted">{desk.skippedAgain}</p> : null}
      {more ? (
        <div className="mt-3">
          <Button onClick={onMore}>{desk.more}</Button>
        </div>
      ) : null}
    </section>
  );
}

function Help({ onClose }: { onClose: () => void }) {
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/55 p-4">
      <div role="dialog" aria-modal="true" aria-label={desk.keysLabel} className="w-full max-w-lg rounded-2xl border border-line bg-surface p-5">
        <h3 className="mb-2 text-lg font-semibold">{desk.helpTitle}</h3>
        <table className="w-full border-collapse text-sm">
          <tbody>
            {desk.helpRows.map(([key, what]) => (
              <tr key={key} className="border-b border-line">
                <td className="whitespace-nowrap py-1.5 pr-4 font-mono text-accent-ink">{key}</td>
                <td className="py-1.5">{what}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="my-3 text-sm text-muted">{desk.helpNote}</p>
        <Button ref={ref} onClick={onClose}>
          {desk.close}
        </Button>
      </div>
    </div>
  );
}
