"use client";

import { notFound } from "next/navigation";
import { useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Brand } from "@/components/ui/brand";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Choice } from "@/components/ui/choice";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Toaster, toast } from "@/components/ui/sonner";
import { StatusChip } from "@/components/ui/status-chip";
import { SuggestionCard, SuggestionCardSkeleton } from "@/components/ui/suggestion-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ChapterStatus } from "@/lib/api";
import { devToolsEnabled } from "@/lib/dev";
import { locale } from "@/lib/api";
import { t } from "@/lib/messages";

const STATUSES: ChapterStatus[] = [
  "not_started",
  "learning",
  "can_do_it",
  "solid",
  "review_due",
  "coming_soon",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="m-0 text-sm font-semibold uppercase tracking-wide text-muted">{title}</h2>
      {children}
    </section>
  );
}

function Showcase({ theme }: { theme: "light" | "dark" }) {
  const copy = t(locale());
  const [picked, setPicked] = useState("9");
  return (
    <div
      data-theme={theme}
      data-testid={`ui-${theme}`}
      className="ui-root flex min-w-0 flex-1 flex-col gap-6 rounded-[var(--radius-card)] border border-line p-5"
    >
      <div className="flex items-center justify-between gap-3">
        <Brand />
        <span className="text-sm font-semibold text-muted">{theme === "light" ? "Light" : "Dark"}</span>
      </div>

      <h1 className="m-0 font-display text-3xl font-medium leading-tight">Good morning, Mina</h1>

      <Section title="Buttons">
        <div className="flex flex-wrap gap-2">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button disabled>Disabled</Button>
        </div>
      </Section>

      <Section title="Suggestion cards">
        <div className="grid gap-3 sm:grid-cols-2">
          <SuggestionCard tone="accent" icon="play" title="Continue: two-step equations" tag="Learning" onClick={() => toast("Opens the lesson")} />
          <SuggestionCard tone="success" icon="refresh" title="Review due" tag="3 cards" onClick={() => toast("Opens the review")} />
          <SuggestionCard tone="warning" icon="alert" title="Stuck now" tag="2 students" onClick={() => toast("Opens the list")} />
          <SuggestionCard tone="neutral" icon="book" title="My notes" tag="Soon" disabled onClick={() => {}} />
          <SuggestionCard tone="accent" icon="calendar" title="Today's plan" tag="12 min" href="#plan" />
          <SuggestionCardSkeleton />
        </div>
      </Section>

      <Section title="Status chips">
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => (
            <StatusChip key={s} status={s} copy={copy} />
          ))}
        </div>
      </Section>

      <Section title="Choice chips">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Class">
          {["8", "9", "10"].map((g) => (
            <Choice key={g} selected={picked === g} onClick={() => setPicked(g)} disabled={g === "10"} tag={g === "10" ? "Coming soon" : undefined}>
              Class {g}
            </Choice>
          ))}
        </div>
      </Section>

      <Section title="Fields">
        <label className="flex flex-col gap-1.5 text-sm font-semibold">
          Family code
          <Input placeholder="For example ABC123" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-semibold">
          Message
          <Textarea rows={3} placeholder="Ask for a topic" />
        </label>
      </Section>

      <Section title="Card, progress, avatar">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Avatar>
                <AvatarFallback>M</AvatarFallback>
              </Avatar>
              <div>
                <CardTitle>Linear equations</CardTitle>
                <CardDescription>4 of 12 skills you can do</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Progress value={33} aria-label="Chapter progress" />
            <span className="text-sm text-muted">33% of the chapter</span>
          </CardContent>
        </Card>
      </Section>

      <Section title="Tabs">
        <Tabs defaultValue="a">
          <TabsList>
            <TabsTrigger value="a">Heatmap</TabsTrigger>
            <TabsTrigger value="b">Stuck now</TabsTrigger>
          </TabsList>
          <TabsContent value="a" className="pt-3 text-sm text-muted">
            Skills by student.
          </TabsContent>
          <TabsContent value="b" className="pt-3 text-sm text-muted">
            Who needs a hand.
          </TabsContent>
        </Tabs>
      </Section>

      <Section title="Dialog, sheet, toast, scroll">
        <div className="flex flex-wrap gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">Open dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogTitle className="m-0 text-lg font-semibold">Delete this child?</DialogTitle>
              <DialogDescription className="text-sm text-muted">
                This removes all their progress. You can export it first.
              </DialogDescription>
              <div className="mt-4 flex justify-end gap-2">
                <DialogClose asChild>
                  <Button variant="ghost">Keep</Button>
                </DialogClose>
                <DialogClose asChild>
                  <Button>Delete</Button>
                </DialogClose>
              </div>
            </DialogContent>
          </Dialog>
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline">Open sheet</Button>
            </SheetTrigger>
            <SheetContent side="right" className="p-5">
              <SheetTitle className="m-0 text-lg font-semibold">Workspace</SheetTitle>
              <SheetDescription className="text-sm text-muted">A panel beside the chat.</SheetDescription>
              <div className="mt-4">
                <SheetClose asChild>
                  <Button variant="secondary">Back to chat</Button>
                </SheetClose>
              </div>
            </SheetContent>
          </Sheet>
          <Button variant="outline" onClick={() => toast("Saved on this device")}>
            Show toast
          </Button>
        </div>
        <ScrollArea className="h-24 rounded-xl border border-line">
          <ul className="m-0 list-none p-3 text-sm">
            {Array.from({ length: 12 }, (_, i) => (
              <li key={i} className="py-1">
                Recent session {i + 1}
              </li>
            ))}
          </ul>
        </ScrollArea>
      </Section>
    </div>
  );
}

/** Developer-only gallery of every design-system component, light and dark side by side. */
export default function DevUiPage() {
  if (!devToolsEnabled()) notFound();
  return (
    <main className="mx-auto flex max-w-[1500px] flex-col gap-4 bg-bg p-4 lg:flex-row">
      <Showcase theme="light" />
      <Showcase theme="dark" />
      <Toaster />
    </main>
  );
}
