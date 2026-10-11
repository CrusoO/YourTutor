"use client";

import { useEffect, useState } from "react";

/** A CSS media query as React state. Only use it for UI that appears after the page has loaded in the browser
 * (a panel, a sheet); layout that is rendered on the server uses CSS classes instead, so markup always matches. */
export function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() => (typeof window !== "undefined" ? window.matchMedia(query).matches : false));
  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    update();
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);
  return matches;
}
