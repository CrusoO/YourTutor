"use client";

import { cn } from "@/lib/cn";
import { LIVE_LOCALES, nativeName, setLocale, useCopy, useLocale, type LocaleRow } from "@/lib/locale";
import localeRegistry from "../../../../packages/shared/generated/locales.json";

/**
 * The language switch (UI-5): English and हिन्दी, each in its own script. It changes the language in place, never
 * leaves the screen the student is on, and the choice is remembered on this device. Languages that are not live yet
 * are listed as "coming soon" when `showSoon` is set (Settings) and can never be selected.
 */
export function LanguageSwitch({ className, showSoon = false }: { className?: string; showSoon?: boolean }) {
  const active = useLocale();
  const copy = useCopy();
  const soon = (localeRegistry.locales as LocaleRow[]).filter((row) => row.status === "coming_soon");
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div role="group" aria-label={copy.language} data-testid="language-switch" className="inline-flex w-fit rounded-full border border-line bg-surface p-0.5">
        {LIVE_LOCALES.map((code) => (
          <button
            key={code}
            type="button"
            lang={code}
            aria-pressed={active === code}
            onClick={() => setLocale(code)}
            data-testid={`language-${code}`}
            className={cn(
              "inline-flex min-h-11 min-w-12 cursor-pointer items-center justify-center rounded-full border-0 px-3 text-sm font-medium",
              active === code ? "bg-accent text-accent-fg" : "bg-transparent text-ink hover:bg-surface-2",
            )}
          >
            {nativeName(code)}
          </button>
        ))}
      </div>
      {showSoon && soon.length ? (
        <p className="m-0 text-sm text-muted" data-testid="language-soon">
          {soon.map((row) => row.name).join(", ")}: {copy.comingSoon}
        </p>
      ) : null}
    </div>
  );
}
