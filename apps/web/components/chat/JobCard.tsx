"use client";

import { useEffect, useRef, useState } from "react";
import { cancelVideoJob, getVideoJob } from "@/lib/api";
import type { VideoJob } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import * as Progress from "@radix-ui/react-progress";

const TERMINAL: ReadonlySet<VideoJob["status"]> = new Set(["done", "failed", "cancelled"]);
const FAST_MS = 3_000;
const SLOW_MS = 30_000;

function stageToProgress(job: VideoJob): number {
  if (job.status === "done") return 100;
  if (job.status === "failed" || job.status === "cancelled") return 0;
  const stageMap: Record<string, number> = { build: 38, render: 66, qa: 94 };
  return stageMap[job.stage ?? ""] ?? (job.status === "running" ? 20 : 5);
}

function statusLabel(job: VideoJob): string {
  if (job.stage_label) return job.stage_label;
  const labels: Record<VideoJob["status"], string> = {
    queued: "Waiting in queue…",
    running: "Building lesson…",
    done: "Lesson ready",
    failed: "Build failed",
    cancelled: "Cancelled",
  };
  return labels[job.status];
}

interface JobCardProps {
  jobId: string;
  title: string;
  onDone?: (job: VideoJob) => void;
}

export function JobCard({ jobId, title, onDone }: JobCardProps) {
  const [job, setJob] = useState<VideoJob | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  // Stable ref so onDone changes don't restart the polling effect
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  });

  useEffect(() => {
    mountedRef.current = true;

    function clearTimer() {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }

    async function poll() {
      if (!mountedRef.current) return;
      if (document.visibilityState === "hidden") {
        timerRef.current = setTimeout(poll, SLOW_MS);
        return;
      }
      try {
        const updated = await getVideoJob(jobId);
        if (!mountedRef.current) return;
        setJob(updated);
        if (TERMINAL.has(updated.status)) {
          if (updated.status === "done") onDoneRef.current?.(updated);
          return; // stop polling
        }
        timerRef.current = setTimeout(
          poll,
          updated.status === "running" ? FAST_MS : SLOW_MS,
        );
      } catch {
        if (mountedRef.current) timerRef.current = setTimeout(poll, SLOW_MS);
      }
    }

    function onVisible() {
      if (document.visibilityState === "visible") {
        clearTimer();
        void poll();
      }
    }

    document.addEventListener("visibilitychange", onVisible);
    void poll();

    return () => {
      mountedRef.current = false;
      clearTimer();
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [jobId]); // onDone is stable via onDoneRef — no restart needed

  async function handleCancel() {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    try {
      const updated = await cancelVideoJob(jobId);
      if (mountedRef.current) setJob(updated);
    } catch {
      // next poll will pick up the updated status
    }
  }

  if (!job) {
    return (
      <div className="space-y-3 rounded-xl border border-[var(--c-line)] bg-[var(--c-surface)] p-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-1.5 w-full" />
        <Skeleton className="h-7 w-20" />
      </div>
    );
  }

  const isActive = !TERMINAL.has(job.status);
  const progress = stageToProgress(job);

  return (
    <div className="space-y-3 rounded-xl border border-[var(--c-line)] bg-[var(--c-surface)] p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-[var(--c-text)]">{title}</p>
          <p className="mt-0.5 text-xs text-[var(--c-muted)]">{statusLabel(job)}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isActive && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleCancel}
              className="h-7 px-2 text-xs"
            >
              Cancel
            </Button>
          )}
          {job.status === "done" && (
            <span className="text-xs font-medium text-[var(--c-success)]">Done</span>
          )}
          {job.status === "failed" && (
            <span className="text-xs font-medium text-[var(--c-danger)]">
              {job.error_code ?? "Failed"}
            </span>
          )}
          {job.status === "cancelled" && (
            <span className="text-xs font-medium text-[var(--c-muted)]">Cancelled</span>
          )}
        </div>
      </div>

      <Progress.Root
        aria-label="Job progress"
        aria-valuenow={progress}
        className="relative h-1.5 w-full overflow-hidden rounded-full bg-[var(--c-surface-2)]"
        value={progress}
      >
        <Progress.Indicator
          className={`h-full transition-transform duration-500 ease-out ${
            job.status === "done"
              ? "bg-[var(--c-success)]"
              : job.status === "failed" || job.status === "cancelled"
                ? "bg-[var(--c-danger)]"
                : "bg-[var(--c-accent)]"
          }`}
          style={{ transform: `translateX(-${100 - progress}%)` }}
        />
      </Progress.Root>
    </div>
  );
}
