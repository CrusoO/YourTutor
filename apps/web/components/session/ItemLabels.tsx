import type { ItemLabels as Labels } from "@/lib/api";
import { sessionEn } from "@/lib/session/copy";

/** "Checked" (solid ink border, tick) or "Not checked" (dashed border, dashed circle). The word and the border
 *  style carry the meaning, so it reads in grey-scale and for colour-blind learners. Anything that is not exactly
 *  "checked" shows Not checked: a missing field from an older server never claims a check. */
export function CheckStamp({ check }: { check?: "checked" | "not_checked" | null }) {
  const checked = check === "checked";
  return (
    <>
      <span
        className={`check-stamp ${checked ? "is-checked" : "is-unchecked"}`}
        data-testid="check-stamp"
        data-state={checked ? "checked" : "not_checked"}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          {checked ? (
            <path d="M3 8.5l3.2 3L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
          ) : (
            <circle cx="8" cy="8" r="6" strokeDasharray="2.6 2.4" />
          )}
        </svg>
        {checked ? sessionEn.checkedStamp : sessionEn.notCheckedStamp}
      </span>
      {checked ? null : (
        <small className="muted check-hint" data-testid="check-hint">
          {sessionEn.notCheckedStampHint}
        </small>
      )}
    </>
  );
}

/** Small print under a practice question: how its answer was checked (always), and where it came from. The server
 *  sends the rights wording (apps/api/app/content/labels.py) only for an original, calculation-checked question. */
export default function ItemLabels({
  labels,
  check,
}: {
  labels?: Labels | null;
  check?: "checked" | "not_checked" | null;
}) {
  return (
    <div className="muted item-labels" data-testid="item-labels">
      <CheckStamp check={check} />
      {labels ? (
        <>
          <small>{labels.question}</small>
          {labels.pattern ? (
            <small data-testid="item-pattern" style={{ display: "block" }}>
              {labels.pattern}
            </small>
          ) : null}
          <small data-testid="item-badge" style={{ display: "block" }}>
            {labels.badge}
            {labels.reviewed ? ` · ${labels.reviewed}` : ""}
          </small>
        </>
      ) : null}
    </div>
  );
}
