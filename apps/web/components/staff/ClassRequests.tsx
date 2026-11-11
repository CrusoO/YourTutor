"use client";

import { useEffect, useState } from "react";
import { classRequests, decideClassRequest, type ClassRequest } from "@/lib/api";
import { useCopy } from "@/lib/locale";

/** Guardian: a child asked to join a class. Yes shares progress with that teacher; no removes it. */
export default function ClassRequests() {
  const copy = useCopy() as unknown as Record<string, string>;
  const [rows, setRows] = useState<ClassRequest[]>([]);

  useEffect(() => {
    classRequests()
      .then((data) => setRows(data.requests))
      .catch(() => setRows([]));
  }, []);

  async function decide(row: ClassRequest, verb: "accept" | "decline") {
    await decideClassRequest(row.class_id, row.student_id, verb);
    setRows((all) => all.filter((r) => !(r.class_id === row.class_id && r.student_id === row.student_id)));
  }

  if (rows.length === 0) return null;
  return (
    <section className="stack" data-testid="guardian-class-requests" aria-labelledby="class-req-h">
      <h2 id="class-req-h">{copy.guardianRequestsTitle}</h2>
      {rows.map((row) => (
        <div key={`${row.class_id}:${row.student_id}`} className="card stack">
          <p>
            {copy.guardianRequestText
              .replaceAll("{student}", row.student_name)
              .replace("{class}", row.class_name)
              .replace("{teacher}", row.teacher)}
          </p>
          <button type="button" onClick={() => void decide(row, "accept")}>
            {copy.guardianRequestYes}
          </button>
          <button type="button" className="secondary" onClick={() => void decide(row, "decline")}>
            {copy.guardianRequestNo}
          </button>
        </div>
      ))}
    </section>
  );
}
