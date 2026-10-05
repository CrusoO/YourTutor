"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { devToolsEnabled } from "@/lib/dev";

export default function DevLessonsPage() {
  if (!devToolsEnabled()) notFound();
  return (
    <main className="stack">
      <h1>Lessons</h1>
      <p>No lessons yet. The lesson player (S1a) lists every lesson here.</p>
      <p>
        <Link href="/dev">Back to scenarios</Link>
      </p>
    </main>
  );
}
