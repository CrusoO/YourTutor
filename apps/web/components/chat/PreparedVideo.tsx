"use client";

/** The video that was built beforehand for a common question. It opens at once and says so; there is no progress bar. */
export function PreparedVideo({ src, title }: { src: string; title: string }) {
  return (
    <div className="flex flex-col gap-3" data-testid="prepared-video-card">
      <p className="m-0 text-[0.8125rem] text-muted">Prepared in advance. Brownie builds videos like this ahead of time for common questions, so this one opens at once.</p>
      <div className="overflow-hidden rounded-xl border border-line">
        {/* eslint-disable-next-line jsx-a11y/media-has-caption -- the captions are burned into the picture */}
        <video src={src} controls preload="metadata" className="w-full bg-black" style={{ maxHeight: "72vh" }} aria-label={title} data-testid="prepared-video" />
      </div>
    </div>
  );
}
