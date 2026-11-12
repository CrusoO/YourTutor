
import { useCopy } from "@/lib/locale";

export type Offer = "first_run" | "warmup_reoffer" | null | undefined;
export type Choice = "warmup" | "start_beginning" | "not_now";

/** The first-run choice, or the one-time warm-up re-offer. A card, never a gate. */
export default function FirstRun({ offer, onChoose, busy = null }: { offer: Offer; onChoose: (c: Choice) => void; busy?: Choice | null }) {
  const copy = useCopy();
  if (!offer) return null;
  const reoffer = offer === "warmup_reoffer";
  return (
    <section className="card first-run" data-testid="first-run" aria-labelledby="first-run-title">
      <h2 id="first-run-title">{reoffer ? copy.reofferTitle : copy.firstRunTitle}</h2>
      <p className="muted">{reoffer ? copy.reofferHint : copy.firstRunHint}</p>
      <button type="button" className="reading" onClick={() => onChoose("warmup")} disabled={busy !== null} aria-busy={busy === "warmup"}>
        {busy === "warmup" ? copy.starting : copy.warmupButton}
      </button>
      {reoffer ? (
        <button type="button" className="secondary" onClick={() => onChoose("not_now")} disabled={busy !== null}>
          {copy.notNow}
        </button>
      ) : (
        <button type="button" className="secondary" onClick={() => onChoose("start_beginning")} disabled={busy !== null} aria-busy={busy === "start_beginning"}>
          {busy === "start_beginning" ? copy.starting : copy.beginningButton}
        </button>
      )}
    </section>
  );
}
