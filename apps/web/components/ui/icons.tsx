import * as React from "react";

/** A small set of line icons drawn for this product. Icons are decorative: a visible text label always
 * sits next to them (UI standard: never an icon without a label), so they are hidden from screen readers. */
const PATHS = {
  book: "M5 4h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Zm0 13a3 3 0 0 1 3-3h10",
  play: "M8 5v14l11-7L8 5Z",
  pencil: "M4 20l1-4L16.5 4.5a2 2 0 0 1 3 3L8 19l-4 1Z",
  refresh: "M20 11a8 8 0 0 0-14-4M4 4v4h4M4 13a8 8 0 0 0 14 4m2 3v-4h-4",
  calendar: "M5 6h14v14H5V6Zm0 4h14M9 3v4m6-4v4",
  users: "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-6 9a6 6 0 0 1 12 0M17 11a2.5 2.5 0 1 0 0-5M16 14a5 5 0 0 1 5 5",
  alert: "M12 4 3 20h18L12 4Zm0 6v5m0 3h.01",
  inbox: "M4 13l2-8h12l2 8v6H4v-6Zm0 0h5l1 2h4l1-2h5",
  chart: "M4 20V8m6 12V4m6 16v-9m5 9H3",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3Z",
  plus: "M12 5v14M5 12h14",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm9 3-4.5-4.5",
  send: "M4 12 20 4l-4 16-4-6-8-2Z",
  mic: "M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm-6-3a6 6 0 0 0 12 0m-6 6v3",
  arrowUp: "M12 19V5m-7 7 7-7 7 7",
  menu: "M4 7h16M4 12h16M4 17h16",
  close: "M6 6l12 12M18 6 6 18",
  chat: "M4 5h16v11H9l-5 4V5Z",
  home: "M4 11 12 4l8 7v9h-5v-6H9v6H4v-9Z",
  star: "m12 3 2.7 5.8 6.3.8-4.6 4.4 1.2 6.3L12 17.2 6.4 20.3l1.2-6.3L3 9.6l6.3-.8L12 3Z",
  lock: "M6 11h12v9H6v-9Zm3 0V8a3 3 0 0 1 6 0v3",
  grid: "M4 4h7v7H4V4Zm9 0h7v7h-7V4ZM4 13h7v7H4v-7Zm9 0h7v7h-7v-7Z",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-8 9a8 8 0 0 1 16 0",
  back: "M15 5 8 12l7 7",
  sparkle: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z",
  check: "M5 12.5l4.5 4.5L19 7.5",
  settings: "M4 7h10m4 0h2M4 17h2m4 0h10M16 4v6M8 14v6",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 20,
  className,
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
