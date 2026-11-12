/** Small inline icons for the role cards. Decorative: the card text names the role. */
const base = { width: 26, height: 26, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true, focusable: false } as const;

export function StudentIcon() {
  return (
    <svg {...base}>
      <path d="M2 9l10-5 10 5-10 5z" />
      <path d="M6 11.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.5" />
    </svg>
  );
}
export function GuardianIcon() {
  return (
    <svg {...base}>
      <circle cx="8" cy="7" r="3" />
      <circle cx="17" cy="9" r="2.2" />
      <path d="M2.5 20v-2.5A4.5 4.5 0 0 1 7 13h2a4.5 4.5 0 0 1 4.5 4.5V20" />
      <path d="M15 14.2a3.6 3.6 0 0 1 5.5 3.1V20" />
    </svg>
  );
}
export function TeacherIcon() {
  return (
    <svg {...base}>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8M12 16v4" />
      <path d="M7 9h6M7 12h4" />
    </svg>
  );
}
export function AdultIcon() {
  return (
    <svg {...base}>
      <path d="M12 3a6 6 0 0 0-3.5 10.9V17h7v-3.1A6 6 0 0 0 12 3z" />
      <path d="M9.5 20.5h5" />
    </svg>
  );
}
export function Chevron() {
  return (
    <svg {...base} width={20} height={20}>
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}
