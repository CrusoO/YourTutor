"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { getPack, postSync } from "@/lib/api";

import type { Pack } from "@/lib/offline/pack";
import { OfflinePlayer } from "@/lib/offline/player";
import { type KeyValueStore, openStore } from "@/lib/offline/store";
import { syncPlayer, type SyncReply } from "@/lib/offline/sync";
import type { Action, CatalogItem } from "@/lib/offline/types";
import { useStudent } from "@/lib/useStudent";
import { useCopy } from "@/lib/locale";

/**
 * Practice without a network. The pack is downloaded once; every step after that runs in the
 * browser with the same policy as the server, and the queued events are sent when the network
 * is back. This screen is deliberately plain: it covers the whole loop (lesson prompt, items,
 * hints, the help picker, the reveal, explain-back, breaks) with a generic layout.
 */
export default function OfflinePage() {
  const copy = useCopy();
  const student = useStudent();
  const [store, setStore] = useState<KeyValueStore | null>(null);
  const [pack, setPack] = useState<Pack | null>(null);
  const [player, setPlayer] = useState<OfflinePlayer | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [pending, setPending] = useState(0);
  const [online, setOnline] = useState(true);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const shownAt = useRef(0);

  useEffect(() => {
    let live = true;
    openStore().then(async (kv) => {
      if (!live) return;
      setStore(kv);
      setPack((await OfflinePlayer.loadPack(kv)) ?? null);
      const resumed = await OfflinePlayer.resume(kv);
      if (resumed && live) {
        setPlayer(resumed);
        setAction(resumed.action);
        setPending(resumed.pending.length);
      }
    });
    setOnline(navigator.onLine);
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      live = false;
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);

  const sync = useCallback(async () => {
    if (!player) return;
    const outcome = await syncPlayer(player, (body) => postSync(body) as Promise<SyncReply>);
    setPending(player.pending.length);
    setMessage(outcome.ok ? copy.offlineSynced : copy.loadError);
  }, [player, copy]);

  useEffect(() => {
    if (online && player && player.pending.length > 0) void sync();
  }, [online, player, sync]);

  async function download() {
    if (!store) return;
    const fresh = (await getPack()) as Pack;
    await OfflinePlayer.savePack(store, fresh);
    setPack(fresh);
    setMessage(copy.offlineDownloaded);
  }

  async function begin() {
    if (!store || !pack) return;
    const fresh = await OfflinePlayer.start(store, pack);
    setPlayer(fresh);
    setAction(fresh.action);
    setPending(0);
    shownAt.current = Date.now();
  }

  async function send(type: string, payload: Record<string, unknown> = {}, itemId?: string | null) {
    if (!player) return;
    const next = await player.send(type, payload, itemId ?? null);
    setAction(next);
    setPending(player.pending.length);
    setAnswer("");
    shownAt.current = Date.now();
    if (online && next.type === "end_session") void sync();
  }

  const item: CatalogItem | undefined =
    pack && action?.item_id ? pack.catalog.find((row) => row.id === action.item_id) : undefined;

  function submitAnswer(response: string) {
    void send("answer", { response, latency_ms: Date.now() - shownAt.current }, action?.item_id);
  }

  function answerBox() {
    if (!item) return null;
    return (
      <div className="stack">
        <p className="stem">{item.stem}</p>
        {item.type === "mcq" ? (
          <div className="stack">
            {item.options.map((option) => (
              <button
                key={option.id}
                type="button"
                className="secondary"
                onClick={() => submitAnswer(option.id)}
              >
                {option.en ?? option.id}
              </button>
            ))}
          </div>
        ) : (
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              if (answer.trim()) submitAnswer(answer.trim());
            }}
          >
            <input
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer"
              aria-label="Type your answer"
              inputMode="decimal"
            />
            <button type="submit">{copy.submit}</button>
          </form>
        )}
        <button type="button" className="secondary" onClick={() => void send("request_help")}>
          {copy.helpButton}
        </button>
      </div>
    );
  }

  function step() {
    if (!action) return null;
    const type = action.type;
    if (type === "predict") {
      return (
        <div className="stack">
          <p>{action.text}</p>
          <button type="button" onClick={() => void send("predict_response", { response: "ok" })}>
            {copy.continue}
          </button>
        </div>
      );
    }
    if (["show_item", "similar_item", "warmup_item", "check_your_work"].includes(type)) {
      return answerBox();
    }
    if (type === "hint") {
      return (
        <div className="stack">
          <p className="banner">{action.text}</p>
          {answerBox()}
        </div>
      );
    }
    if (type === "ask_stuck_point") {
      const choices = (action.extras.choices as string[]) ?? [];
      return (
        <div className="stack">
          <h2>{copy.stuckTitle}</h2>
          {choices.map((choice) => (
            <button
              key={choice}
              type="button"
              className="secondary"
              onClick={() => void send("stuck_choice", { choice })}
            >
              {choice.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      );
    }
    if (type === "ask_stuck_step") {
      const count = Number(action.extras.step_count ?? 0);
      return (
        <div className="stack">
          {Array.from({ length: count }, (_, index) => (
            <button
              key={index}
              type="button"
              className="secondary"
              onClick={() => void send("stuck_step", { index })}
            >
              {`Step ${index + 1}`}
            </button>
          ))}
        </div>
      );
    }
    if (type === "explain_back_prompt") {
      return (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void send("explain_back", { text: answer });
          }}
        >
          <p>{copy.explainBack}</p>
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <button type="submit">{copy.continue}</button>
        </form>
      );
    }
    if (type === "break_or_switch") {
      return (
        <div className="stack">
          <h2>{copy.breakTitle}</h2>
          {["break", "switch", "continue"].map((choice) => (
            <button
              key={choice}
              type="button"
              className="secondary"
              onClick={() => void send("break_choice", { choice })}
            >
              {choice}
            </button>
          ))}
        </div>
      );
    }
    if (type === "end_session") {
      return (
        <div className="stack">
          <h2>{copy.done}</h2>
          <p className="muted">{pending > 0 ? copy.offlineWaiting : copy.offlineSynced}</p>
        </div>
      );
    }
    // worked example, reveal, explain-back result, content gap, nudge: read and continue
    return (
      <div className="stack">
        {action.text ? <p>{action.text}</p> : null}
        <button type="button" onClick={() => void send("continue")}>
          {copy.continue}
        </button>
      </div>
    );
  }

  if (!student) return <p>…</p>;
  return (
    <main className="stack" data-testid="offline-page">
      <h1>{copy.offlineTitle}</h1>
      <p className="muted">{copy.offlineIntro}</p>
      <p data-testid="offline-status" className="muted">
        {online ? copy.offlineIsOnline : copy.offlineIsOffline}
        {" · "}
        {pack ? `${pack.catalog.length} ${copy.offlineCount}` : copy.offlineNothing}
        {pending > 0 ? ` · ${pending} ${copy.offlineWaiting}` : ""}
      </p>
      {store && !store.durable ? <p className="banner">{copy.offlineNotSaved}</p> : null}
      {!player || action?.type === "end_session" ? (
        <div className="stack">
          <button type="button" disabled={!online} onClick={() => void download()}>
            {copy.offlineDownload}
          </button>
          <button type="button" disabled={!pack} onClick={() => void begin()}>
            {copy.offlineStart}
          </button>
        </div>
      ) : null}
      {player && action ? (
        <section
          className="card stack"
          data-testid="offline-step"
          data-action={action.type}
          data-item-id={action.item_id ?? ""}
        >
          {step()}
        </section>
      ) : null}
      {player && pending > 0 ? (
        <button type="button" className="secondary" disabled={!online} onClick={() => void sync()}>
          {copy.offlineSync}
        </button>
      ) : null}
      {message ? <p data-testid="offline-message">{message}</p> : null}
      <Link href="/subjects">{copy.offlineBack}</Link>
    </main>
  );
}
