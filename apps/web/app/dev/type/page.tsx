"use client";

import { notFound } from "next/navigation";
import { devToolsEnabled } from "@/lib/dev";

/**
 * Dev only: a specimen of the display and label type, used by e2e/identity.spec.ts to check that Hindi (Devanagari)
 * lines never clip a matra or overlap, in both themes. It renders in whatever language the device has chosen.
 */
export default function TypeSpecimen() {
  if (!devToolsEnabled()) notFound();
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8" data-testid="type-specimen">
      <h1 className="display m-0 text-[2rem] text-ink @xl:text-[3.25rem]" data-testid="specimen-headline" lang="hi">
        विद्यार्थियों के लिए द्विघात समीकरण
      </h1>
      <p className="display m-0 text-[1.75rem] text-ink" data-testid="specimen-mixed" lang="hi">
        Class 12 गणित: Integrals
      </p>
      <p className="label m-0 text-ink" data-testid="specimen-label" lang="hi">
        अभ्यास शुरू करें
      </p>
      <button type="button" className="glow-btn w-auto" data-testid="specimen-glow" lang="hi">
        एक सवाल आज़माएँ
      </button>
      <p className="m-0 text-base text-ink" data-testid="specimen-body" lang="hi">
        द्विघात समीकरण ax + b = 0 के हल निकालने के लिए पहले उसे मानक रूप में लिखिए। Class 12 के Integrals में भी यही क्रम काम आता है।
      </p>
    </main>
  );
}
