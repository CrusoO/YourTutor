"use client";

import { Choice } from "@/components/ui/choice";
import { useComfort, type ThemeChoice } from "@/lib/comfort";
import { useChatApi } from "./ChatProvider";

/** A row of mutually exclusive choices with a label. The selected one is shown by a check mark, not colour. */
export function Group<T extends string>({
  label,
  value,
  options,
  onPick,
  testid,
}: {
  label: string;
  value: T;
  options: { id: T; text: string }[];
  onPick: (id: T) => void;
  testid: string;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-col gap-2" data-testid={testid}>
      <span className="text-sm font-semibold text-muted">{label}</span>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <Choice key={o.id} selected={value === o.id} onClick={() => onPick(o.id)} data-testid={`${testid}-${o.id}`}>
            {o.text}
          </Choice>
        ))}
      </div>
    </div>
  );
}

/** Auto / Light / Dark. Used in the sidebar and in the Comfort dialog. */
export function ThemeSwitch() {
  const { copy } = useChatApi();
  const [comfort, update] = useComfort();
  return (
    <Group<ThemeChoice>
      label={copy.themeLabel}
      value={comfort.theme}
      onPick={(theme) => update({ theme })}
      testid="theme"
      options={[
        { id: "auto", text: copy.themeAuto },
        { id: "light", text: copy.themeLight },
        { id: "dark", text: copy.themeDark },
      ]}
    />
  );
}
