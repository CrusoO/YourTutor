import * as React from "react";
import { cn } from "@/lib/cn";

const field =
  "w-full rounded-xl border border-input-line bg-surface px-4 py-2.5 font-[inherit] text-base text-ink placeholder:text-muted";

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = "text", ...props }, ref) => (
    <input ref={ref} type={type} className={cn(field, "min-h-11", className)} {...props} />
  ),
);
Input.displayName = "Input";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(field, "min-h-11 resize-none", className)} {...props} />
));
Textarea.displayName = "Textarea";

export { Input, Textarea };
