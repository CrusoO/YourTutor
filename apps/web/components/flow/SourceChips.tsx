export type SourceChip = { id: string; title: string };

/** Where an explanation comes from (an approved authored source). Nothing when there is none. */
export default function SourceChips({ sources, label }: { sources?: SourceChip[]; label: string }) {
  if (!sources || sources.length === 0) return null;
  return (
    <ul className="source-chips" aria-label={label}>
      {sources.map((s) => (
        <li key={s.id} title={s.id}>
          {s.title}
        </li>
      ))}
    </ul>
  );
}
