"use client";

import { useEffect, useRef } from "react";

/** The video that was built beforehand for a common question. It opens at once and says so; there is no progress bar. */
export function PreparedVideo({ src, title, poster }: { src: string; title: string; poster?: string }) {
  return (
    <div className="flex flex-col gap-3" data-testid="prepared-video-card">
      <p className="m-0 text-[0.8125rem] text-muted">Prepared in advance. Brownie builds videos like this ahead of time for common questions, so this one opens at once.</p>
      <div className="overflow-hidden rounded-xl border border-line">
        {/* eslint-disable-next-line jsx-a11y/media-has-caption -- the captions are burned into the picture */}
        <video src={src} poster={poster} controls preload="metadata" className="w-full bg-black" style={{ maxHeight: "72vh" }} aria-label={title} data-testid="prepared-video" />
      </div>
    </div>
  );
}

/**
 * The video opening over the lesson: it starts playing at once (the student just tapped to watch it) at the scene that explains the step they got wrong,
 * and closes with the button or Escape. A clean frame, so it can also be recorded as a clip.
 */
export function VideoDialog({ src, title, poster, startAt = 0, onClose }: { src: string; title: string; poster?: string; startAt?: number; onClose: () => void }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black p-4" role="dialog" aria-modal="true" aria-label={title} data-testid="video-dialog">
      <div className="flex w-full max-w-[56rem] flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="m-0 text-[0.875rem] text-white">Prepared in advance</p>
          <button type="button" onClick={onClose} data-testid="video-dialog-close" className="min-h-10 cursor-pointer rounded-full border-0 bg-white/20 px-4 text-[0.875rem] text-white hover:bg-white/30">
            Close
          </button>
        </div>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption -- the captions are burned into the picture */}
        <video
          ref={ref}
          src={src}
          poster={poster}
          controls
          autoPlay
          playsInline
          className="max-h-[78vh] w-full rounded-xl bg-black"
          data-testid="video-dialog-player"
          onLoadedMetadata={() => {
            if (ref.current && startAt > 0) ref.current.currentTime = startAt;
          }}
        />
      </div>
    </div>
  );
}
