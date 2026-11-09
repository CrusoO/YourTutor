"use client";

import type { Helpline } from "@/lib/api";

/** Support lines under a distress message. Names and numbers only, so it needs no translation; the message
    above it (authored, reviewed per language) says what they are for. Renders nothing without a list. */
export function Helplines({ list }: { list: Helpline[] | undefined }) {
  if (!list?.length) return null;
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0" data-testid="helplines">
      {list.map((h) => (
        <li key={h.id} className="rounded-2xl border border-line bg-surface px-4 py-3 text-[0.9375rem] text-ink">
          <a className="font-semibold underline" href={`tel:${h.number.replace(/[^\d+]/g, "")}`}>
            {h.name} {h.number}
          </a>
          {h.hours ? <span className="text-muted"> · {h.hours}</span> : null}
        </li>
      ))}
    </ul>
  );
}
