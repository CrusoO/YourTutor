import type { ItemLabels as Labels } from "@/lib/api";

/** Small print under a practice question: where it came from and how its answer was checked.
 *  The server sends the wording (apps/api/app/content/labels.py) and only for an original,
 *  calculation-checked question, so this shows nothing for anything else. */
export default function ItemLabels({ labels }: { labels?: Labels | null }) {
  if (!labels) {
    return null;
  }
  return (
    <div className="muted item-labels" data-testid="item-labels">
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
    </div>
  );
}
