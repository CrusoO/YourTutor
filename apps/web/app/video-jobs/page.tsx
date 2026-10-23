"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  authFetch,
  cancelVideoJob,
  createVideoJob,
  getVideoJob,
  getVideoJobTopics,
  type VideoJob,
  type VideoJobTopic,
} from "@/lib/api";
import { useStudent } from "@/lib/useStudent";

// These two caveats are always shown — non-suppressible.
const MANDATORY_CAVEATS = [
  "No person has confirmed these page numbers.",
  "The voice in this video is AI-generated.",
];

const POLL_MS = 3_000;
const TERMINAL = new Set(["done", "failed", "cancelled"]);

type Sources = {
  caveats?: string[];
  book?: { title?: string };
  [key: string]: unknown;
};

export default function VideoJobsPage() {
  const student = useStudent();

  // topic picker
  const [topics, setTopics] = useState<VideoJobTopic[]>([]);
  const [topicsError, setTopicsError] = useState(false);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [nodePrefix, setNodePrefix] = useState("cbse.10.maths");

  // active job
  const [job, setJob] = useState<VideoJob | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);

  // video player
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const prevVideoUrl = useRef<string | null>(null);

  // sources panel
  const [sources, setSources] = useState<Sources | null>(null);

  // ── load topics ────────────────────────────────────────────────────────────

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

  // ── polling ────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!job || TERMINAL.has(job.status)) return;
    const id = setInterval(async () => {
      try {
        const updated = await getVideoJob(job.id);
        setJob(updated);
      } catch {
        // network blip — keep polling
      }
    }, POLL_MS);
    return () => clearInterval(id);
  }, [job?.id, job?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── fetch sources when job finishes ───────────────────────────────────────

  useEffect(() => {
    if (job?.status !== "done") return;
    authFetch(`/video-jobs/${job.id}/sources.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: Sources | null) => setSources(data))
      .catch(() => setSources(null));
  }, [job?.status, job?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── clean up blob URL ──────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      if (prevVideoUrl.current) URL.revokeObjectURL(prevVideoUrl.current);
    };
  }, []);

  // ── actions ────────────────────────────────────────────────────────────────

  async function pickTopic(nodeId: string) {
    setJobError(null);
    setSources(null);
    setVideoUrl(null);
    setVideoError(null);
    try {
      const created = await createVideoJob(nodeId, crypto.randomUUID());
      setJob(created);
    } catch {
      setJobError("Could not start the job — please try again.");
    }
  }

  async function loadVideo() {
    if (!job) return;
    setVideoLoading(true);
    setVideoError(null);
    try {
      const r = await authFetch(`/video-jobs/${job.id}/lesson.mp4`);
      if (!r.ok) throw new Error("Download failed");
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      if (prevVideoUrl.current) URL.revokeObjectURL(prevVideoUrl.current);
      prevVideoUrl.current = url;
      setVideoUrl(url);
    } catch {
      setVideoError("Could not load the video — please try again.");
    } finally {
      setVideoLoading(false);
    }
  }

  async function cancelJob() {
    if (!job) return;
    try {
      const updated = await cancelVideoJob(job.id);
      setJob(updated);
    } catch {
      // ignore — the poll will catch the state
    }
  }

  // ── render helpers ─────────────────────────────────────────────────────────

  function groupByChapter(ts: VideoJobTopic[]) {
    const map = new Map<string, { title: string; sections: VideoJobTopic[] }>();
    for (const t of ts) {
      if (!map.has(t.chapter_title)) {
        map.set(t.chapter_title, { title: t.chapter_title, sections: [] });
      }
      map.get(t.chapter_title)!.sections.push(t);
    }
    return [...map.values()];
  }

  if (!student) {
    return (
      <main className="stack">
        <p>Please sign in to access video lessons.</p>
      </main>
    );
  }

  // ── job status card ────────────────────────────────────────────────────────

  const jobCard = job && (
    <section className="stack" style={{ marginTop: "1.5rem" }}>
      <h2 style={{ fontSize: "1.1rem" }}>
        {job.status === "queued" && "Waiting in queue…"}
        {job.status === "running" && (job.stage_label ?? "Building lesson…")}
        {job.status === "done" && "Lesson ready"}
        {job.status === "failed" && "Build failed"}
        {job.status === "cancelled" && "Cancelled"}
      </h2>

      {/* progress bar — indeterminate while running */}
      {(job.status === "queued" || job.status === "running") && (
        <progress
          aria-label="Building lesson"
          style={{ width: "100%", height: "6px" }}
        />
      )}

      {job.status === "failed" && (
        <p className="banner" role="alert" style={{ color: "var(--c-error, #c00)" }}>
          {job.error_message ?? "Something went wrong — please try again."}
        </p>
      )}

      {/* cancel button for active jobs */}
      {(job.status === "queued" || job.status === "running") && (
        <button onClick={cancelJob} style={{ alignSelf: "flex-start" }}>
          Cancel
        </button>
      )}

      {/* video player section */}
      {job.status === "done" && (
        <div className="stack">
          {!videoUrl && (
            <button
              onClick={loadVideo}
              disabled={videoLoading}
              style={{ alignSelf: "flex-start" }}
            >
              {videoLoading ? "Loading video…" : "Watch video"}
            </button>
          )}
          {videoError && (
            <p className="banner" role="alert">
              {videoError}
            </p>
          )}
          {videoUrl && (
            /* eslint-disable-next-line jsx-a11y/media-has-caption */
            <video
              src={videoUrl}
              controls
              style={{ width: "100%", maxWidth: "720px", borderRadius: "8px" }}
              aria-label="Lesson video"
            />
          )}

          {/* sources panel */}
          <details open style={{ marginTop: "1rem" }}>
            <summary style={{ cursor: "pointer", fontWeight: 600 }}>
              Sources &amp; caveats
            </summary>
            <div
              className="stack"
              style={{
                fontSize: "0.875rem",
                padding: "0.75rem",
                background: "var(--c-surface, #f5f5f5)",
                borderRadius: "6px",
                marginTop: "0.5rem",
              }}
            >
              {sources?.book?.title && (
                <p>
                  <strong>Book:</strong> {sources.book.title}
                </p>
              )}
              {sources?.caveats?.map((c, i) => (
                <p key={i} className="muted">
                  {c}
                </p>
              ))}
              {/* mandatory caveats — always shown */}
              {MANDATORY_CAVEATS.map((c) => (
                <p key={c} style={{ fontStyle: "italic" }} className="muted">
                  {c}
                </p>
              ))}
            </div>
          </details>
        </div>
      )}

      <button
        onClick={() => {
          setJob(null);
          setSources(null);
          setVideoUrl(null);
        }}
        style={{ alignSelf: "flex-start", marginTop: "0.5rem" }}
      >
        ← Back to topics
      </button>
    </section>
  );

  // ── topic picker ───────────────────────────────────────────────────────────

  const chapters = groupByChapter(topics);

  return (
    <main className="stack">
      <h1>Video Lessons</h1>

      {jobError && (
        <p className="banner" role="alert">
          {jobError}
        </p>
      )}

      {/* show the job card while a job is active */}
      {jobCard}

      {/* topic picker — always visible so the student can start another job */}
      {!job && (
        <section className="stack">
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
            <label htmlFor="node-prefix" style={{ fontWeight: 600 }}>
              Curriculum prefix
            </label>
            <input
              id="node-prefix"
              value={nodePrefix}
              onChange={(e) => setNodePrefix(e.target.value)}
              placeholder="e.g. cbse.10.maths"
              style={{ flex: 1, minWidth: "16ch", padding: "6px 8px" }}
            />
          </div>

          {topicsLoading && <p className="muted">Loading topics…</p>}
          {topicsError && (
            <p className="banner" role="alert">
              Could not load topics — please reload.
            </p>
          )}

          {!topicsLoading && !topicsError && chapters.length === 0 && (
            <p className="muted" data-testid="no-topics">
              No topics available for this curriculum yet.
            </p>
          )}

          {chapters.map((ch) => (
            <div key={ch.title} className="stack" style={{ gap: "0.25rem" }}>
              <h2 style={{ fontSize: "1rem", margin: "0.75rem 0 0.25rem" }}>{ch.title}</h2>
              <ul className="plain" style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                {ch.sections.map((t) => (
                  <li key={t.node_id}>
                    <button
                      className="card"
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "10px 14px",
                        cursor: "pointer",
                      }}
                      onClick={() => pickTopic(t.node_id)}
                      data-testid={`topic-${t.node_id}`}
                    >
                      <span style={{ fontWeight: 500 }}>{t.section_title}</span>
                      {t.page_start != null && (
                        <span className="muted" style={{ marginLeft: "0.5rem", fontSize: "0.8em" }}>
                          pp. {t.page_start}
                          {t.page_end != null && t.page_end !== t.page_start
                            ? `–${t.page_end}`
                            : ""}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
