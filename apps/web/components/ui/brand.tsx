import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/cn";

/** The product's mark and wordmark. The name lives in lib/brand.ts and the colours in app/tokens.css. */
export function Brand({ className, showName = true }: { className?: string; showName?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-ink", className)}>
      <svg aria-hidden="true" width="26" height="26" viewBox="0 0 26 26" focusable="false">
        <rect width="26" height="26" rx="7" fill="var(--c-accent)" />
        <path
          d="M6 17h5v-4h4V9h5"
          fill="none"
          stroke="var(--c-accent-fg)"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {showName ? (
        <span className="font-display text-lg font-medium leading-none">{BRAND.name}</span>
      ) : (
        <span className="sr-only">{BRAND.name}</span>
      )}
    </span>
  );
}
