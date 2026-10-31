"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@/components/ui/icons";
import { applyComfort, readComfort, saveComfort } from "@/lib/comfort";
import { cn } from "@/lib/cn";
import { useChatApi } from "./ChatProvider";

const NAV = [
  { name: "home", label: "homeNavHome", href: "/" },
  { name: "book", label: "homeNavLessons", href: "/video-jobs" },
  { name: "pencil", label: "homeNavPractice", href: "#practice" },
  { name: "chart", label: "homeNavProgress", href: "#progress" },
] as const;

/** Flip between the two palettes and remember the choice (the same setting as Settings > Comfort). */
function toggleTheme() {
  const root = document.documentElement;
  const explicit = root.getAttribute("data-theme");
  const dark = explicit ? explicit === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  const next = { ...readComfort(), theme: dark ? ("light" as const) : ("dark" as const) };
  applyComfort(next);
  saveComfort(next);
}

export function IconSidebar() {
  const { identity, copy, dispatch, signOut } = useChatApi();
  const pathname = usePathname();
  const initial = identity?.name?.[0]?.toUpperCase() ?? "G";

  return (
    <aside
      className="hidden w-14 shrink-0 flex-col items-center gap-1 border-0 border-r border-line bg-transparent py-4 lg:flex"
      aria-label={copy.appName}
      data-testid="sidebar"
    >
      <Link
        href="/"
        aria-label={copy.homeNavNew}
        className="mb-5 grid size-7 place-items-center rounded-full bg-accent text-accent-fg shadow-[0_0_18px_color-mix(in_srgb,var(--c-accent)_45%,transparent)] transition-opacity hover:opacity-85"
      >
        <Icon name="sparkle" size={13} />
      </Link>

      <nav className="flex flex-1 flex-col items-center gap-1.5" aria-label={copy.homeMainNav}>
        {NAV.map(({ name, label, href }) => {
          const active = pathname === href;
          return (
            <Link
              key={name}
              href={href}
              aria-label={copy[label]}
              title={copy[label]}
              aria-current={active ? "page" : undefined}
              className={cn(
                "grid size-8 place-items-center rounded-[10px] transition-colors",
                active ? "bg-accent-soft text-accent-ink" : "text-muted hover:bg-surface-2 hover:text-ink",
              )}
            >
              <Icon name={name} size={16} />
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col items-center gap-3">
        <button
          type="button"
          onClick={toggleTheme}
          className="grid size-8 cursor-pointer place-items-center rounded-[10px] border-0 bg-transparent text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          aria-label={copy.homeThemeToggle}
          title={copy.homeThemeToggle}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </svg>
        </button>
        {identity ? (
          <>
            <button
              type="button"
              onClick={signOut}
              className="grid size-8 cursor-pointer place-items-center rounded-[10px] border-0 bg-transparent text-muted transition-colors hover:bg-surface-2 hover:text-ink"
              aria-label={copy.chatSignOut}
              title={copy.chatSignOut}
              data-testid="sign-out"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 4H5v16h4M16 8l4 4-4 4M20 12H9" />
              </svg>
            </button>
            <span className="grid size-7 place-items-center rounded-full bg-surface-2 text-[0.6875rem] font-medium text-ink" title={identity.name ?? undefined} data-testid="who">
              {initial}
            </span>
          </>
        ) : (
          <button
            type="button"
            onClick={() => dispatch({ type: "identity", view: "choices" })}
            className="grid size-8 cursor-pointer place-items-center rounded-full border-0 bg-accent text-accent-fg transition-opacity hover:opacity-90"
            aria-label={copy.chatSignIn}
            title={copy.chatSignIn}
            data-testid="nav-sign-in"
          >
            <Icon name="user" size={15} />
          </button>
        )}
      </div>
    </aside>
  );
}
