import type { MouseEvent } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icons";
import { langProps } from "./lang";

export type TabItem = { id: string; label: string; href: string; icon: IconName };

export type BottomTabBarProps = {
  /** Four tabs: Home, Practice, Progress, Lessons (labels and hrefs come from the caller). */
  items: readonly TabItem[];
  /** The current pathname; the tab whose href equals it (or is a parent of it) is current. */
  currentPath: string;
  /** Name of the landmark, for example "Main". */
  label: string;
  /** Optional hook for client-side navigation; call event.preventDefault() and push yourself. Default: a normal link. */
  onNavigate?: (href: string, event: MouseEvent<HTMLAnchorElement>) => void;
  /** "fixed" pins it to the screen edge (bottom on phones, left rail from 768 px); "static" lays it out in flow (previews). */
  position?: "fixed" | "static";
  lang?: string;
  className?: string;
};

/** True when `path` is `href` or below it (`/practice/3` is on the `/practice` tab; `/` matches only `/`). */
export function isCurrentTab(path: string, href: string): boolean {
  if (href === "/") return path === "/";
  return path === href || path.startsWith(href.endsWith("/") ? href : `${href}/`);
}

/**
 * Four-tab navigation: a bottom bar on phones that becomes a left rail from 768 px. No router import: it takes
 * hrefs and the current path as props. The current tab carries aria-current="page", a filled pill and bold text.
 * Targets are 56 px tall, labels 12 px or more.
 */
export function BottomTabBar({ items, currentPath, label, onNavigate, position = "fixed", lang, className }: BottomTabBarProps) {
  return (
    <nav
      aria-label={label}
      {...langProps(lang)}
      className={cn(
        "z-30 border-t border-input-line bg-surface text-ink md:border-r md:border-t-0",
        position === "fixed" && "fixed inset-x-0 bottom-0 pb-[env(safe-area-inset-bottom)] md:inset-y-0 md:right-auto md:bottom-auto md:w-24 md:pb-0",
        position === "static" && "w-full md:w-24",
        className,
      )}
    >
      <ul className="m-0 flex list-none p-0 md:flex-col md:gap-1 md:p-2">
        {items.map((it) => {
          const current = isCurrentTab(currentPath, it.href);
          return (
            <li key={it.id} className="min-w-0 flex-1 md:flex-none">
              <a
                href={it.href}
                aria-current={current ? "page" : undefined}
                data-current={current ? "true" : "false"}
                onClick={onNavigate ? (e) => onNavigate(it.href, e) : undefined}
                className={cn(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 px-1 py-1.5 text-xs no-underline",
                  "focus-visible:outline focus-visible:outline-[3px] focus-visible:-outline-offset-2 focus-visible:outline-[color:var(--c-focus)] md:rounded-xl",
                  current ? "font-bold text-accent-ink" : "font-medium text-muted",
                )}
              >
                <span className={cn("flex h-7 w-12 items-center justify-center rounded-full", current ? "bg-accent-soft" : "")}>
                  <Icon name={it.icon} size={20} />
                </span>
                <span className="max-w-full truncate">{it.label}</span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
