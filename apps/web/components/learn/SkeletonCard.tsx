import { cn } from "@/lib/cn";

/** A placeholder card while content loads. `label` is the spoken status (for example "Loading"). Pulses only if motion is allowed. */
export function SkeletonCard({ label, lines = 3, className }: { label: string; lines?: number; className?: string }) {
  return (
    <div
      role="status"
      aria-busy="true"
      className={cn("flex flex-col gap-3 rounded-[var(--radius-card)] border border-input-line bg-surface p-5", className)}
    >
      <span className="sr-only">{label}</span>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          aria-hidden="true"
          className={cn("h-4 rounded-md bg-surface-2 motion-safe:animate-pulse", i === lines - 1 ? "w-1/2" : "w-full")}
        />
      ))}
    </div>
  );
}
