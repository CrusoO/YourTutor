"use client";

import { useCallback, useEffect, useState } from "react";
import {
  classCodeStatus,
  disableClassCode,
  joinRequests,
  makeClassCode,
  type CodeStatus,
} from "@/lib/api";
import { useCopy } from "@/lib/locale";

const EXPIRY = [null, 7, 30, 90] as const;

/** Teacher: make, replace or turn off the join code, and see who is waiting (labels only). */
export default function ClassCodePanel({ classId }: { classId: string }) {
  const copy = useCopy() as unknown as Record<string, string>;
  const [status, setStatus] = useState<CodeStatus | null>(null);
  const [labels, setLabels] = useState<string[]>([]);
  const [days, setDays] = useState<number | null>(30);
  const [shown, setShown] = useState("");

  const load = useCallback(async () => {
    const [s, r] = await Promise.all([classCodeStatus(classId), joinRequests(classId)]);
    setStatus(s);
    setLabels(r.requests.map((row) => row.label));
  }, [classId]);

  useEffect(() => {
    setShown("");
    void load();
  }, [load]);

  async function make() {
    const out = await makeClassCode(classId, days);
    setShown(out.code);
    await load();
  }

  async function off() {
    await disableClassCode(classId);
    setShown("");
    await load();
  }

  const state = !status
    ? ""
    : status.enabled
      ? copy.classCodeOn
      : status.expired
        ? copy.classCodeExpired
        : copy.classCodeIsOff;

  return (
    <section className="stack" data-testid="teacher-classcode" aria-labelledby="classcode-h">
      <h2 id="classcode-h">{copy.classCodeTitle}</h2>
      <p className="muted">{copy.classCodeHint}</p>
      <p data-testid="classcode-state">{state}</p>
      {shown ? (
        <div className="card stack" role="status">
          <strong data-testid="classcode-value" style={{ fontSize: "1.6rem", letterSpacing: "0.1em" }}>
            {shown}
          </strong>
          <span className="muted">{copy.classCodeShownOnce}</span>
        </div>
      ) : null}
      <label>
        {copy.classCodeExpiry}
        <select
          value={days === null ? "" : String(days)}
          onChange={(e) => setDays(e.target.value ? Number(e.target.value) : null)}
        >
          {EXPIRY.map((n) => (
            <option key={String(n)} value={n === null ? "" : String(n)}>
              {n === null ? copy.classCodeNoEnd : copy.classCodeDays.replace("{n}", String(n))}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={() => void make()}>
        {copy.classCodeMake}
      </button>
      <p className="muted">{copy.classCodeRotateNote}</p>
      {status?.enabled ? (
        <button type="button" className="secondary" onClick={() => void off()}>
          {copy.classCodeOff}
        </button>
      ) : null}
      <h3>{copy.classCodePending.replace("{n}", String(status?.pending_count ?? 0))}</h3>
      {labels.length === 0 ? (
        <p className="muted">{copy.classCodeNoneWaiting}</p>
      ) : (
        <>
          <ul data-testid="classcode-requests">
            {labels.map((label, index) => (
              <li key={index}>{label}</li>
            ))}
          </ul>
          <p className="muted">{copy.classCodeLabelsHint}</p>
        </>
      )}
    </section>
  );
}
