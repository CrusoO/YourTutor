"use client";

import { useEffect, useRef, useState } from "react";
import { authFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icons";
import { useCopy } from "@/lib/locale";
import { CaptionedVideo, type CaptionTrack } from "./CaptionedVideo";

interface VideoCardProps {
  jobId: string;
  /** Fetch the video as soon as the card appears (the lesson page does; the topic list waits for a click). */
  autoLoad?: boolean;
}

export function VideoCard({ jobId, autoLoad = false }: VideoCardProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const revokeRef = useRef<string | null>(null);
  const [captions, setCaptions] = useState<CaptionTrack | null>(null);
  const captionsRevokeRef = useRef<string | null>(null);
  const copy = useCopy();
  const frameRef = useRef<HTMLDivElement>(null);
  // Full window: the browser's full-screen mode where it exists, else a page-filling overlay (some phones).
  const [expanded, setExpanded] = useState(false);
  const [overlay, setOverlay] = useState(false);

  useEffect(() => {
    const onChange = () => setExpanded(document.fullscreenElement === frameRef.current);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOverlay(false);
    };
    document.addEventListener("fullscreenchange", onChange);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("fullscreenchange", onChange);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  async function toggleExpand() {
    const frame = frameRef.current;
    if (!frame) return;
    if (overlay) return setOverlay(false);
    if (document.fullscreenElement) return void document.exitFullscreen();
    if (document.fullscreenEnabled && frame.requestFullscreen) {
      try {
        await frame.requestFullscreen();
        return;
      } catch {
        /* refused: fall back to the overlay */
      }
    }
    setOverlay(true);
  }
  const full = expanded || overlay;

  // Revoke the blob URL when the component unmounts to free memory
  useEffect(() => {
    return () => {
      if (revokeRef.current) URL.revokeObjectURL(revokeRef.current);
      if (captionsRevokeRef.current) URL.revokeObjectURL(captionsRevokeRef.current);
    };
  }, []);

  useEffect(() => {
    if (autoLoad) void loadVideo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoLoad, jobId]);

  async function loadVideo() {
    setLoading(true);
    setError(null);
    try {
      const r = await authFetch(`/video-jobs/${jobId}/lesson.mp4`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      if (revokeRef.current) URL.revokeObjectURL(revokeRef.current);
      revokeRef.current = url;
      setBlobUrl(url);
      void loadCaptions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the video — please try again.");
    } finally {
      setLoading(false);
    }
  }

  /** The caption track, if the engine wrote one. Any failure just means no captions button (the video is unchanged). */
  async function loadCaptions() {
    try {
      const job = await (await authFetch(`/video-jobs/${jobId}`)).json();
      const info = job?.captions;
      if (!info || info.format !== "webvtt" || typeof info.url !== "string") return;
      const r = await authFetch(info.url);
      if (!r.ok) return;
      const vtt = new Blob([await r.arrayBuffer()], { type: "text/vtt" });
      const url = URL.createObjectURL(vtt);
      if (captionsRevokeRef.current) URL.revokeObjectURL(captionsRevokeRef.current);
      captionsRevokeRef.current = url;
      setCaptions({ src: url, lang: typeof info.language === "string" ? info.language : "en" });
    } catch {
      /* no captions button */
    }
  }

  if (!blobUrl) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-[var(--c-line)] bg-[var(--c-surface)] p-4">
        <Button
          variant="default"
          size="sm"
          onClick={loadVideo}
          disabled={loading}
          className="gap-2"
        >
          <Icon name="play" size={16} />
          {loading ? "Loading…" : "Watch video"}
        </Button>
        {error && (
          <p className="text-xs text-[var(--c-danger)]" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <div
      ref={frameRef}
      className={
        overlay
          ? "fixed inset-0 z-50 flex items-center justify-center bg-black"
          : expanded
            ? "relative flex h-full w-full items-center justify-center bg-black"
            : "relative overflow-hidden rounded-xl border border-[var(--c-line)]"
      }
      data-testid="video-frame"
    >
      <CaptionedVideo
        captions={captions}
        buttonTop={56}
        src={blobUrl}
        controls
        preload="metadata"
        className={full ? "h-full w-full bg-black object-contain" : "w-full bg-black"}
        style={full ? undefined : { maxHeight: "72vh" }}
        aria-label="Lesson video"
      />
      <button
        type="button"
        onClick={() => void toggleExpand()}
        aria-pressed={full}
        aria-label={full ? copy.lessonVideoCollapse : copy.lessonVideoExpand}
        title={full ? copy.lessonVideoCollapse : copy.lessonVideoExpand}
        data-testid="video-expand"
        style={{ position: "absolute", top: 12, right: 12, left: "auto", width: "auto", zIndex: 2 }}
        className="inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-full border-0 bg-black/60 px-3 text-[0.75rem] font-medium text-white backdrop-blur-sm transition-colors hover:bg-black/80"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          {full ? <path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" /> : <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />}
        </svg>
        {full ? copy.lessonVideoCollapse : copy.lessonVideoExpand}
      </button>
    </div>
  );
}
