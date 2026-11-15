"use client";

import { useEffect, useState } from "react";
import { applyAudience, AUDIENCE_THEMES, DEFAULT_AUDIENCE, resolveAudience, storedAudience, type Audience, type AudienceTheme } from "./audience";
import { loadUi } from "./ui";

/**
 * The audience of this device: a stored choice, else the grade band of the signed-in student, else school. It sets
 * the data-audience, data-density, data-mascot and data-motion attributes on <html> and follows a sign-in or a
 * stored change. There is no visible switch yet. The first render is always school so server and browser agree.
 */
export function useAudience(): { audience: Audience; theme: AudienceTheme } {
  const [audience, setAudience] = useState<Audience>(DEFAULT_AUDIENCE);
  useEffect(() => {
    const read = () => {
      const next = resolveAudience({ stored: storedAudience(), bandId: loadUi()?.band_id });
      setAudience(next);
      applyAudience(next);
    };
    read();
    window.addEventListener("storage", read);
    window.addEventListener("yt:ui", read);
    return () => {
      window.removeEventListener("storage", read);
      window.removeEventListener("yt:ui", read);
    };
  }, []);
  return { audience, theme: AUDIENCE_THEMES[audience] };
}
