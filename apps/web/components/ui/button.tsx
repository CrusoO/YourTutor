import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

/** `w-auto` and the explicit height undo the legacy stylesheet's full-width button rule. */
const buttonVariants = cva(
  "inline-flex w-auto cursor-pointer items-center justify-center gap-2 rounded-xl border border-transparent text-base font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-accent text-accent-fg hover:opacity-90 active:opacity-80",
        secondary: "bg-surface-2 text-ink hover:bg-accent-soft active:opacity-80",
        outline: "border-input-line bg-surface text-ink hover:bg-surface-2 active:opacity-80",
        ghost: "bg-transparent text-ink hover:bg-surface-2 active:opacity-80",
      },
      size: {
        default: "min-h-12 min-w-12 px-5 py-2",
        sm: "min-h-12 min-w-12 px-3 py-1.5 text-sm",
        icon: "size-12 p-0",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, type, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        {...(asChild ? {} : { type: type ?? "button" })}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
