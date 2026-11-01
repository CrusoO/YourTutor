"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { type LandingLanguage } from "./content";
import { landingTranslations } from "./landing-translations";

const STORAGE_KEY = "brownie_landing_language";

type LandingState = {
  language: LandingLanguage;
  setLanguage: (language: LandingLanguage) => void;
};

const LandingLanguageContext = createContext<LandingState | null>(null);

function isLandingLanguage(value: string | null): value is LandingLanguage {
  return value !== null && Object.hasOwn(landingTranslations, value);
}

export function LandingLanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<LandingLanguage>("en");

  useEffect(() => {
    try {
      const requested = new URLSearchParams(window.location.search).get("lang");
      if (isLandingLanguage(requested)) {
        setLanguageState(requested);
        window.localStorage.setItem(STORAGE_KEY, requested);
        return;
      }
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (isLandingLanguage(saved)) setLanguageState(saved);
    } catch {
      return;
    }
  }, []);

  const value = useMemo<LandingState>(() => ({
    language,
    setLanguage(next) {
      setLanguageState(next);
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
        const url = new URL(window.location.href);
        if (url.searchParams.has("lang")) {
          url.searchParams.set("lang", next);
          window.history.replaceState(window.history.state, "", url);
        }
      } catch {
        return;
      }
    },
  }), [language]);

  return (
    <LandingLanguageContext.Provider value={value}>
      {children}
    </LandingLanguageContext.Provider>
  );
}

export function useLandingLanguage() {
  const context = useContext(LandingLanguageContext);
  if (!context) throw new Error("useLandingLanguage must be used within LandingLanguageProvider");
  return {
    ...context,
    copy: landingTranslations[context.language],
  };
}
