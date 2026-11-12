"use client";

import { useEffect, useState } from "react";
import { getCatalog, type Catalog, type CatalogItem } from "@/lib/agreements-api";
import { items as copyItems, roleIntro, roleTitle, ui, type Role } from "@/lib/agreement-copy";
import styles from "./Agreement.module.css";

/** One item: its own tick box, its own words. */
export function Tick({
  role,
  item,
  checked,
  onChange,
  disabled,
}: {
  role: Role;
  item: CatalogItem;
  checked: boolean;
  onChange: (on: boolean) => void;
  disabled?: boolean;
}) {
  const words = copyItems[role][item.id] ?? { label: item.id, detail: "" };
  return (
    <label className={styles.tick} data-testid={`tick-${item.id}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className={styles.text}>
        <span className={styles.label}>
          {words.label}
          <span className={styles.tag}>({item.required ? ui.required : ui.optional})</span>
        </span>
        {words.detail ? <span className={styles.detail}>{words.detail}</span> : null}
      </span>
    </label>
  );
}

/** The role's agreement as it is shown once at sign-up. Required items are their own group and must all be ticked. */
export default function AgreementForm({
  role,
  submitLabel = ui.agree,
  busy = false,
  onSubmit,
  catalog,
}: {
  role: Role;
  submitLabel?: string;
  busy?: boolean;
  onSubmit: (items: string[], version: string) => void;
  /** Supplied by a caller that already fetched it (the guardian's approval screen). */
  catalog?: Catalog;
}) {
  const [loaded, setLoaded] = useState<Catalog | null>(catalog ?? null);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");

  useEffect(() => {
    if (catalog) return;
    getCatalog(role)
      .then(setLoaded)
      .catch(() => setError(ui.failed));
  }, [role, catalog]);

  if (!loaded) return error ? <p className="banner">{error}</p> : <p>…</p>;
  const required = loaded.items.filter((i) => i.required);
  const optional = loaded.items.filter((i) => !i.required);
  const ready = required.every((i) => ticked.has(i.id));
  const toggle = (id: string, on: boolean) =>
    setTicked((current) => {
      const next = new Set(current);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  return (
    <form
      className="stack"
      data-testid={`agreement-${role}`}
      onSubmit={(event) => {
        event.preventDefault();
        if (ready) onSubmit(loaded.items.filter((i) => ticked.has(i.id)).map((i) => i.id), loaded.version);
      }}
    >
      <h2>{roleTitle[role]}</h2>
      <p>{roleIntro[role]}</p>
      <fieldset className={styles.group} data-testid="group-required">
        <legend>{role === "teacher" ? ui.groupTeacher : ui.groupNeeded}</legend>
        {required.map((item) => (
          <Tick key={item.id} role={role} item={item} checked={ticked.has(item.id)} onChange={(on) => toggle(item.id, on)} />
        ))}
      </fieldset>
      {optional.length ? (
        <fieldset className={styles.group} data-testid="group-optional">
          <legend>{ui.groupOptional}</legend>
          {optional.map((item) => (
            <Tick key={item.id} role={role} item={item} checked={ticked.has(item.id)} onChange={(on) => toggle(item.id, on)} />
          ))}
        </fieldset>
      ) : null}
      {role !== "teacher" ? <p className="muted">{ui.noTracking}</p> : null}
      {!ready ? <p className="muted">{ui.agreeNeeds}</p> : null}
      <button type="submit" disabled={!ready || busy}>
        {busy ? ui.saving : submitLabel}
      </button>
    </form>
  );
}
