/**
 * One answer to "should anything move on its own?". True when the device asks for reduced motion
 * (prefers-reduced-motion) or the person chose "less motion" in Comfort (data-motion="reduce" on <html>).
 * Every autoplay, timed rotation, hop animation and smooth scroll asks this, then shows its static fallback.
 */
export function reducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof document !== "undefined" && document.documentElement.getAttribute("data-motion") === "reduce") return true;
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** The `behavior` for scrollIntoView and scrollTo. */
export function scrollBehavior(): ScrollBehavior {
  return reducedMotion() ? "auto" : "smooth";
}
