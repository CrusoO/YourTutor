"use client";

import { forwardRef, useCallback, useEffect, useRef, useState, type VideoHTMLAttributes } from "react";
import { useCopy } from "@/lib/locale";

/** A caption track kept beside a video (WebVTT). Absent for old videos and for captions burned into the picture. */
export type CaptionTrack = { src: string; lang: string };

const KEY = "yt_captions";

/** The remembered choice on this device. Captions are ON unless the student turned them off. Never throws. */
export function readCaptionsPref(): boolean {
  try {
    return window.localStorage.getItem(KEY) !== "off";
  } catch {
    return true;
  }
}

function writeCaptionsPref(on: boolean): void {
  try {
    window.localStorage.setItem(KEY, on ? "on" : "off");
  } catch {
    /* storage blocked: the choice lasts until the page is closed */
  }
}

type Props = VideoHTMLAttributes<HTMLVideoElement> & {
  captions?: CaptionTrack | null;
  /** Distance of the button from the top of the parent in px; lower it when another button sits at the top right. */
  buttonTop?: number;
};

/**
 * A <video> with an optional native caption track and a Captions on/off button.
 * Without a track nothing extra is drawn. The button sits at the top right of the nearest positioned parent.
 */
export const CaptionedVideo = forwardRef<HTMLVideoElement, Props>(function CaptionedVideo({ captions, buttonTop = 12, ...video }, outerRef) {
  const copy = useCopy();
  const inner = useRef<HTMLVideoElement | null>(null);
  const [on, setOn] = useState(true);
  const has = Boolean(captions);

  const setRefs = useCallback(
    (el: HTMLVideoElement | null) => {
      inner.current = el;
      if (typeof outerRef === "function") outerRef(el);
      else if (outerRef) outerRef.current = el;
    },
    [outerRef],
  );

  // Read the remembered choice after mount (the first render is the same on server and client).
  useEffect(() => setOn(readCaptionsPref()), []);

  // Apply the choice to the track, and follow it if the player's own menu changes it.
  useEffect(() => {
    const el = inner.current;
    if (!el || !has) return;
    const apply = () => {
      const track = el.textTracks?.[0];
      if (track) track.mode = on ? "showing" : "hidden";
    };
    apply();
    const trackEl = el.querySelector("track");
    trackEl?.addEventListener("load", apply);
    const list = el.textTracks;
    const sync = () => {
      const track = list?.[0];
      if (!track) return;
      const showing = track.mode === "showing";
      if (showing !== on) {
        setOn(showing);
        writeCaptionsPref(showing);
      }
    };
    list?.addEventListener?.("change", sync);
    return () => {
      trackEl?.removeEventListener("load", apply);
      list?.removeEventListener?.("change", sync);
    };
  }, [on, has, captions?.src]);

  function toggle() {
    const next = !on;
    setOn(next);
    writeCaptionsPref(next);
  }

  return (
    <>
      {/* eslint-disable-next-line jsx-a11y/media-has-caption -- the track below is the captions; videos without one have them burned in */}
      <video ref={setRefs} {...video}>
        {captions ? <track kind="captions" src={captions.src} srcLang={captions.lang} label={copy.captionsTrackLabel} default /> : null}
      </video>
      {captions ? (
        <button
          type="button"
          onClick={toggle}
          aria-pressed={on}
          data-testid="captions-toggle"
          style={{ position: "absolute", top: buttonTop, right: 12, left: "auto", width: "auto", zIndex: 2 }}
          className="inline-flex min-h-11 min-w-11 cursor-pointer items-center gap-1.5 rounded-full border-0 bg-black/60 px-3 text-[0.8125rem] font-medium text-white backdrop-blur-sm transition-colors hover:bg-black/80 motion-reduce:transition-none"
        >
          <span>{copy.captionsLabel}</span>
          <span aria-hidden="true" className={on ? "rounded-full bg-white px-2 text-black" : "rounded-full border border-white/70 px-2"}>
            {on ? copy.captionsOn : copy.captionsOff}
          </span>
          <span className="sr-only">{on ? copy.captionsOn : copy.captionsOff}</span>
        </button>
      ) : null}
    </>
  );
});
