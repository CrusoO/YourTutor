/**
 * The practice-session look. It is a string rendered as a <style> inside the session route (not a .css file), so it is
 * not part of the shared stylesheet budget that the homepage is measured against. Tokens only (--s-*).
 */
export const SESSION_CSS = `/* ---- Practice session look (visual refresh). Everything below uses the semantic --s-* tokens, so dark mode and the
   college / work themes follow. Scoped to main.sess so no other screen changes. Motion is CSS only and off for
   reduced motion (device setting or Comfort). ---- */
.sess {
  gap: 16px;
}
.sess h1 {
  font-size: 1.5rem;
  line-height: 1.25;
  margin: 0;
}
.prog {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 28px;
  font-size: 0.875rem;
  color: var(--s-text-subtle);
}
.prog-label {
  font-weight: 700;
  color: var(--s-text-action);
}
.prog-dots {
  display: flex;
  gap: 6px;
  flex: 1;
  align-items: center;
}
.prog-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--s-action-primary);
}
.prog-dot.now {
  background: transparent;
  box-shadow: inset 0 0 0 2px var(--s-action-primary);
}
.prog-count {
  white-space: nowrap;
}
.q-card {
  background: var(--s-surface-card);
  border: 1px solid var(--s-border-subtle);
  border-radius: 20px;
  padding: 20px 20px 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.q-card .stem {
  font-size: 1.375rem;
  line-height: 1.4;
  font-weight: 600;
  margin: 0 0 12px;
}
.check-stamp {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0 8px;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  background: transparent;
}
.check-stamp.is-checked {
  border: 2px solid var(--s-text-default);
  color: var(--s-text-default);
}
.check-stamp.is-unchecked {
  border: 2px dashed var(--s-text-subtle);
  color: var(--s-text-subtle);
}
.check-stamp svg {
  flex: none;
}
.check-hint {
  display: block;
  margin: 0 0 8px;
}
.ans-label {
  margin: 8px 0 0;
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--s-text-subtle);
}
.ans-value {
  margin: 0 0 8px;
  font-size: 2rem;
  font-weight: 700;
  color: var(--s-text-action);
}
.sess button,
.sess input {
  min-height: var(--s-control-min);
  border-radius: 14px;
}
.sess input.math {
  min-height: 56px;
  font-size: 1.5rem;
  padding: 10px 16px;
  border: 2px solid var(--s-border-control);
  background: var(--s-surface-card);
}
.sess form > button[type="submit"],
.sess > button:not(.secondary):not(.ghost),
.sess [data-testid="confidence"] > button:not(.secondary):not(.ghost) {
  min-height: 52px;
  font-size: 1.0625rem;
  box-shadow: 0 3px 0 rgba(0, 0, 0, 0.18);
}
.sess button.secondary {
  min-height: 52px;
  border: 2px solid var(--s-border-control);
  background: var(--s-surface-card);
  color: var(--s-text-default);
}
.sess button.ghost {
  min-height: var(--s-control-min);
}
.sess button:focus-visible,
.sess input:focus-visible,
.sess summary:focus-visible {
  outline: 3px solid var(--s-focus-ring);
  outline-offset: 2px;
}
.hint-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-weight: 700;
  color: var(--s-status-warning-fg);
}
.fbk {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px;
  border-radius: 18px;
  border: 2px solid currentColor;
}
.fbk p {
  margin: 0;
}
.fbk-icon {
  flex: none;
  margin-top: 2px;
}
.fbk-title {
  font-size: 1.125rem;
  font-weight: 800;
}
.fbk-body {
  color: var(--s-text-default);
  margin-top: 4px;
}
.fbk.ok {
  background: var(--s-status-success-bg);
  color: var(--s-status-success-fg);
}
.fbk.try {
  background: var(--s-status-warning-bg);
  color: var(--s-status-warning-fg);
}
.sess .banner {
  border-radius: 14px;
  line-height: 1.45;
}
.sign-hint {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sign-card {
  background: var(--s-surface-card);
  border: 1px solid var(--s-border-subtle);
  border-left: 5px solid var(--s-action-primary);
  border-radius: 16px;
  padding: 16px;
}
.sign-title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  color: var(--s-text-action);
}
.sign-rule p {
  margin: 0 0 6px;
}
.sign-rule-extra {
  font-weight: 700;
}
.sign-steps {
  margin: 8px 0 0;
  padding-left: 1.4rem;
}
.sign-steps li {
  margin: 6px 0;
  font-size: 1.0625rem;
}
.more-steps {
  border: 1px solid var(--s-border-subtle);
  border-radius: 14px;
  padding: 4px 14px;
}
.more-steps summary {
  min-height: var(--s-control-min);
  display: flex;
  align-items: center;
  cursor: pointer;
  font-weight: 600;
  color: var(--s-text-action);
}
.mnl {
  margin: 8px 0;
}
.mnl-svg {
  display: block;
  width: 100%;
  max-width: 440px;
  height: auto;
  margin: 0 auto;
  min-height: 110px;
}
.mnl-axis,
.mnl-tick {
  stroke: var(--s-text-subtle);
  stroke-width: 2;
  stroke-linecap: round;
}
.mnl-zero {
  stroke: var(--s-text-default);
  stroke-width: 3;
}
.mnl-label,
.mnl-tag {
  fill: var(--s-text-default);
  font-size: 15px;
  font-family: inherit;
}
.mnl-label-zero {
  font-weight: 800;
}
.mnl-tag {
  fill: var(--s-text-subtle);
  font-size: 13px;
}
.mnl-tag-land {
  fill: var(--s-status-success-fg);
  font-weight: 700;
}
.mnl-move line,
.mnl-drop {
  stroke: var(--s-action-primary);
  stroke-width: 3;
  stroke-linecap: round;
}
.mnl-drop {
  stroke-dasharray: 3 4;
  stroke-width: 2;
}
.mnl-move polygon {
  fill: var(--s-action-primary);
}
.mnl-start {
  fill: var(--s-surface-card);
  stroke: var(--s-action-primary);
  stroke-width: 4;
}
.mnl-land {
  fill: var(--s-status-success-fg);
  stroke: var(--s-surface-card);
  stroke-width: 2;
}
.mnl-caption {
  margin-top: 4px;
  font-size: 0.8125rem;
  color: var(--s-text-subtle);
  text-align: center;
}
@media (prefers-reduced-motion: no-preference) {
  html:not([data-motion="reduce"]) .sess > * {
    animation: sess-in 220ms var(--ease, ease-out) both;
  }
}
@keyframes sess-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.q-card .read-aloud {
  margin: 0 0 8px;
}
.q-card .read-aloud button {
  width: auto;
  min-height: var(--s-control-min);
  padding: 6px 16px;
  font-size: 0.9375rem;
  border-width: 1px;
}
.prog-dots {
  min-width: 0;
}
`;

export default function SessionStyles() {
  return <style data-testid="session-styles">{SESSION_CSS}</style>;
}
