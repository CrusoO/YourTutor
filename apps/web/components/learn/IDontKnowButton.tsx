import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icons";
import { langProps } from "./lang";

export type IDontKnowButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  /** The words, for example "I don't know, give me a hint". */
  label: string;
  /** Loading: the hint is being prepared. The button stays in place, busy and not pressable. */
  loading?: boolean;
  lang?: string;
};

/**
 * The prominent secondary action. Asking for help is a normal move, so it is full width, 48 px tall and outlined in
 * the accent colour (not a quiet link). Wire `onClick` to the hint flow. States: default, disabled, loading.
 */
export function IDontKnowButton({ label, loading, disabled, lang, className, ...rest }: IDontKnowButtonProps) {
  return (
    <button
      type="button"
      {...langProps(lang)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      data-state={loading ? "loading" : disabled ? "disabled" : "default"}
      className={cn(
        "inline-flex min-h-12 w-full cursor-pointer font-[family-name:var(--ff-body)]! normal-case! tracking-normal! items-center justify-center gap-2 rounded-xl border-2 border-accent bg-surface px-4 py-3 text-base font-semibold text-accent-ink",
        "hover:bg-accent-soft focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[color:var(--c-focus)]",
        "disabled:cursor-not-allowed disabled:opacity-60",
        loading && "motion-safe:animate-pulse",
        className,
      )}
      {...rest}
    >
      <Icon name="sparkle" size={18} />
      {label}
    </button>
  );
}
