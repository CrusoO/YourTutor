import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icons";
import { TRUST_LABELS, type TrustVariant } from "./trust";

export type TrustChipProps = {
  variant: TrustVariant;
  /**
   * Whether the item is factory-stamped as code-verified. REQUIRED for the chip to render at all:
   * undefined renders nothing; "checked-by-code" and "hints-from-verified-steps" render only when `true`;
   * "not-verified" renders only when `false`. A chip must never claim a check that did not happen.
   */
  verified?: boolean;
  className?: string;
};

/** True when the chip may show for this variant and flag. Exported so callers and tests share one rule. */
export function trustChipVisible(variant: TrustVariant, verified: boolean | undefined): boolean {
  if (verified === undefined) return false;
  return variant === "not-verified" ? verified === false : verified === true;
}

/**
 * A small label saying how much to trust a question or its hints. The wording comes only from `trust.ts`.
 * Icon plus words, never colour alone.
 */
export function TrustChip({ variant, verified, className }: TrustChipProps) {
  if (!trustChipVisible(variant, verified)) return null;
  const ok = variant !== "not-verified";
  return (
    <span
      data-variant={variant}
      className={cn(
        "inline-flex min-h-6 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
        ok ? "bg-success-soft text-success" : "bg-neutral-soft text-neutral",
        className,
      )}
    >
      <Icon name={ok ? "check" : "alert"} size={14} />
      {TRUST_LABELS[variant]}
    </span>
  );
}
