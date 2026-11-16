import { Fragment, type ReactNode } from "react";

/**
 * Renders a plain-text equation with superscripts and subscripts: `x^2` and `x^(n+1)` raise, `a_1` and `a_(n)` lower.
 * No library and no HTML parsing; anything else is shown as typed. Pass a ReactNode instead when a screen already
 * has its own rendering (the lesson widgets draw their own).
 */
export function MathText({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  const re = /([\^_])(\([^)]*\)|[-+]?[A-Za-z0-9.]+)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(<Fragment key={key++}>{text.slice(last, m.index)}</Fragment>);
    const inner = m[2].startsWith("(") ? m[2].slice(1, -1) : m[2];
    parts.push(m[1] === "^" ? <sup key={key++}>{inner}</sup> : <sub key={key++}>{inner}</sub>);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  return <>{parts}</>;
}
