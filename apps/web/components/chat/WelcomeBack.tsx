"use client";

import { Choice } from "@/components/ui/choice";
import type { Memory } from "@/lib/chat/memory";
import { Bubble } from "./Bubbles";

/** Brownie greeting a returning learner by what they were doing, with one button to go on. */
export function WelcomeBack({ memory, onGo }: { memory: Memory; onGo: (kind: Memory["kind"]) => void }) {
  return (
    <div className="flex w-full flex-col gap-3" aria-live="polite" data-testid="welcome-back">
      <Bubble from="tutor" text={memory.text} />
      <div className="pl-11">
        <Choice onClick={() => onGo(memory.kind)} data-testid={`welcome-${memory.kind}`}>
          {memory.button}
        </Choice>
      </div>
    </div>
  );
}
