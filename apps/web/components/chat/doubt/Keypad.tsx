"use client";

import type { RefObject } from "react";
import { DOUBT_COPY as T } from "./copy";

/** A key: what the student sees, what it types, and the spoken name. `caret` moves the cursor back inside the insert. */
type Key = { show: string; insert: string; label: string; caret?: number };

const KEYS: Key[] = [
  ...["7", "8", "9", "4", "5", "6", "1", "2", "3", "0"].map((d) => ({ show: d, insert: d, label: d })),
  { show: ".", insert: ".", label: "decimal point" },
  { show: "x", insert: "x", label: "x" },
  { show: "y", insert: "y", label: "y" },
  { show: "+", insert: " + ", label: "plus" },
  { show: "-", insert: " - ", label: "minus" },
  { show: "×", insert: " × ", label: "times" },
  { show: "÷", insert: " ÷ ", label: "divided by" },
  { show: "^", insert: "^", label: "power" },
  { show: "(", insert: "(", label: "open bracket" },
  { show: ")", insert: ")", label: "close bracket" },
  { show: "=", insert: " = ", label: "equals" },
  { show: "a/b", insert: "()/()", label: "fraction", caret: 4 },
  { show: "√", insert: "√()", label: "square root", caret: 1 },
];

export type KeypadProps = {
  /** The composer's text box: the keys edit it at the cursor. */
  box: RefObject<HTMLTextAreaElement | null>;
  /** Called after each edit so the box can resize. */
  onChange: () => void;
};

/** A soft keypad that only fills the composer text. 44 px keys, real buttons, nothing stored or sent. */
export default function Keypad({ box, onChange }: KeypadProps) {
  /** Replace the selection (or the character before the cursor, for `cut`) and put the cursor `back` from the end. */
  function edit(text: string, back = 0, cut = false) {
    const el = box.current;
    if (!el) return;
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? start;
    const from = cut && start === end ? Math.max(0, start - 1) : start;
    el.value = el.value.slice(0, from) + text + el.value.slice(end);
    const at = from + text.length - back;
    el.setSelectionRange(at, at);
    onChange();
    el.focus();
  }
  const onInsert = (t: string, back?: number) => edit(t, back);
  const onBackspace = () => edit("", 0, true);
  const onClear = () => {
    if (box.current) box.current.value = "";
    edit("");
  };
  const key =
    "inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-center rounded-xl border-2 border-input-line bg-surface px-2 text-base font-semibold text-ink hover:bg-surface-2 focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[color:var(--c-focus)]";
  return (
    <div role="group" aria-label={T.keypadLabel} className="grid grid-cols-6 gap-2 py-2" style={{ lineHeight: 1.5 }} data-testid="doubt-keypad">
      {KEYS.map((k) => (
        <button key={k.label} type="button" aria-label={k.label} className={key} onClick={() => onInsert(k.insert, k.caret)} data-testid={`key-${k.label}`}>
          {k.show}
        </button>
      ))}
      <button type="button" aria-label="backspace" className={key} onClick={onBackspace} data-testid="key-backspace">
        ⌫
      </button>
      <button type="button" aria-label="clear" className={`${key} text-sm`} onClick={onClear} data-testid="key-clear">
        Clear
      </button>
    </div>
  );
}
