"use client";

import { useCallback, useEffect, useState } from "react";
import { createVideoJob, getVideoJobTopics, type VideoJob, type VideoJobTopic } from "@/lib/api";
import { useStudent } from "@/lib/useStudent";
import { JobCard } from "@/components/chat/JobCard";
import { VideoCard } from "@/components/chat/VideoCard";
import { SourcesDrawer } from "@/components/chat/SourcesDrawer";
import { TopicChips } from "@/components/chat/TopicChips";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export default function VideoJobsPage() {
  const student = useStudent();

  const [topics, setTopics] = useState<VideoJobTopic[]>([]);
  const [topicsError, setTopicsError] = useState(false);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [nodePrefix, setNodePrefix] = useState("cbse.10.maths");

  const [activeJob, setActiveJob] = useState<VideoJob | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [jobDone, setJobDone] = useState(false);

  const loadTopics = useCallback(
    (prefix: string) => {
      if (!student) return;
      setTopicsLoading(true);
      setTopicsError(false);
      getVideoJobTopics(prefix)
        .then((r) => setTopics(r.topics))
        .catch(() => setTopicsError(true))
        .finally(() => setTopicsLoading(false));
    },
    [student],
  );

  useEffect(() => {
    loadTopics(nodePrefix);
  }, [loadTopics, nodePrefix]);

  async function pickTopic(nodeId: string) {
    setJobError(null);
    setJobDone(false);
    try {
      const created = await createVideoJob(nodeId, crypto.randomUUID());
      setActiveJob(created);
    } catch {
      setJobError("Could not start the job — please try again.");
    }
  }

  function handleJobDone(job: VideoJob) {
    setActiveJob(job);
    setJobDone(true);
  }

  function reset() {
    setActiveJob(null);
    setJobDone(false);
    setJobError(null);
  }

  if (!student) {
    return (
      <main className="phone">
        <p className="text-sm text-[var(--c-text)]">Please sign in to access video lessons.</p>
      </main>
    );
  }

  const jobTitle =
    topics.find((t) => t.node_id === activeJob?.node_id)?.section_title ?? activeJob?.node_id ?? "";

  return (
    <main className="phone">
      <div className="stack">
        <h1 className="text-xl font-semibold text-[var(--c-text)]">Video Lessons</h1>

        {jobError && (
          <p className="text-sm text-[var(--c-danger)]" role="alert">
            {jobError}
          </p>
        )}

        {activeJob ? (
          <div className="space-y-3">
            <JobCard jobId={activeJob.id} title={jobTitle} onDone={handleJobDone} />
            {jobDone && (
              <>
                <VideoCard jobId={activeJob.id} />
                <SourcesDrawer jobId={activeJob.id} />
              </>
            )}
            <Button variant="ghost" size="sm" onClick={reset} className="text-xs">
              ← Back to topics
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <label
                htmlFor="node-prefix"
                className="text-sm font-medium text-[var(--c-text)]"
              >
                Curriculum
              </label>
              <input
                id="node-prefix"
                value={nodePrefix}
                onChange={(e) => setNodePrefix(e.target.value)}
                placeholder="e.g. cbse.10.maths"
                className="min-w-[16ch] flex-1 rounded-md border border-[var(--c-input-line)] bg-[var(--c-surface)] px-3 py-1.5 text-sm text-[var(--c-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--c-focus)]"
              />
            </div>

            {topicsLoading && (
              <div className="space-y-2">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-3/4" />
              </div>
            )}
            {topicsError && (
              <p className="text-sm text-[var(--c-danger)]" role="alert">
                Could not load topics — please reload.
              </p>
            )}
            {!topicsLoading && !topicsError && topics.length === 0 && (
              <p className="text-sm text-[var(--c-muted)]" data-testid="no-topics">
                No topics available for this curriculum yet.
              </p>
            )}
            {!topicsLoading && topics.length > 0 && (
              <TopicChips topics={topics} selected={null} onSelect={pickTopic} />
            )}
          </div>
        )}
      </div>
    </main>
  );
}
