"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { LanguageSwitch } from "@/components/ui/language-switch";
import { useComfort, type Effects, type Motion, type Paper, type Spacing, type TextSize } from "@/lib/comfort";
import { useChatApi } from "./ChatProvider";
import { Group, ThemeSwitch } from "./ComfortSettings";

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
          <div className="flex flex-col gap-2" data-testid="settings-language">
            <span className="text-sm font-semibold text-muted">{copy.language}</span>
            <LanguageSwitch showSoon />
          </div>
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
          <Group<Paper>
            label={copy.boardPaperLabel}
            value={comfort.paper}
            onPick={(paper) => update({ paper })}
            testid="paper"
            options={[
              { id: "plain", text: copy.paperPlain },
              { id: "grid", text: copy.paperGrid },
            ]}
          />
          <Group<Effects>
            label={copy.effectsLabel}
            value={comfort.effects}
            onPick={(effects) => update({ effects })}
            testid="effects"
            options={[
              { id: "auto", text: copy.effectsAuto },
              { id: "reduce", text: copy.effectsReduce },
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
