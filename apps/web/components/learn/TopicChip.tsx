import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icons";
import { langProps } from "./lang";

export type TopicChipProps = {
  children: ReactNode;
  /** With onClick the chip is a button (44 px tall); without it, a plain label. */
  onClick?: () => void;
  selected?: boolean;
  disabled?: boolean;
  lang?: string;
  className?: string;
};

/** A topic name as a pill. Selected shows a check mark as well as the fill. States: default, selected, disabled. */
export function TopicChip({ children, onClick, selected = false, disabled, lang, className }: TopicChipProps) {
  const tone = selected ? "border-accent bg-accent-soft text-ink" : "border-input-line bg-surface text-ink";
  const base = cn("inline-flex items-center gap-1.5 font-[family-name:var(--ff-body)]! normal-case! tracking-normal! rounded-full border-2 px-3 text-sm font-semibold", tone, className);
  if (!onClick) {
    return (
      <span {...langProps(lang)} data-state={selected ? "selected" : "default"} className={cn(base, "min-h-8 py-1")}>
        {selected ? <Icon name="check" size={14} /> : null}
        {children}
      </span>
    );
  }
  return (
    <button
      type="button"
      {...langProps(lang)}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selected}
      data-state={disabled ? "disabled" : selected ? "selected" : "default"}
      className={cn(
        base,
        "min-h-11 cursor-pointer py-2 focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[color:var(--c-focus)] disabled:cursor-not-allowed disabled:opacity-60",
      )}
    >
      {selected ? <Icon name="check" size={14} /> : null}
      {children}
    </button>
  );
}
