"use client";

import { Button } from "@/components/ui/button";
import { Choice } from "@/components/ui/choice";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useComfort, type Motion, type Spacing, type TextSize, type ThemeChoice } from "@/lib/comfort";
import { useChatApi } from "./ChatProvider";

/** A row of mutually exclusive choices with a label. The selected one is shown by a check mark, not colour. */
function Group<T extends string>({
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

/** Settings > Comfort: theme, text size, line spacing and motion. Everything stays on this device. */
export function ComfortDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { copy } = useChatApi();
  const [comfort, update] = useComfort();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="comfort-dialog">
        <DialogTitle className="m-0 text-xl font-semibold">{copy.comfortTitle}</DialogTitle>
        <DialogDescription className="m-0 mb-4 text-sm text-muted">{copy.comfortHint}</DialogDescription>
        <div className="flex flex-col gap-5">
          <ThemeSwitch />
          <Group<TextSize>
            label={copy.textSizeLabel}
            value={comfort.text}
            onPick={(text) => update({ text })}
            testid="text-size"
            options={[
              { id: "s", text: copy.textSizeS },
              { id: "m", text: copy.textSizeM },
              { id: "l", text: copy.textSizeL },
            ]}
          />
          <Group<Spacing>
            label={copy.spacingLabel}
            value={comfort.spacing}
            onPick={(spacing) => update({ spacing })}
            testid="spacing"
            options={[
              { id: "normal", text: copy.spacingNormal },
              { id: "relaxed", text: copy.spacingRelaxed },
            ]}
          />
          <Group<Motion>
            label={copy.motionLabel}
            value={comfort.motion}
            onPick={(motion) => update({ motion })}
            testid="motion"
            options={[
              { id: "auto", text: copy.motionAuto },
              { id: "reduce", text: copy.motionReduce },
            ]}
          />
        </div>
        <div className="mt-6 flex justify-end">
          <DialogClose asChild>
            <Button data-testid="comfort-close">{copy.settingsClose}</Button>
          </DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  );
}
