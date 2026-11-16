/**
 * Audience themes: ONE design system, three audiences (school students now; college students and working adults
 * later). A theme is data: tone, density, motion, mascot. The colours it changes are in app/semantic.css and are
 * checked by tests/ui/semantic.test.ts. There is no visible switch yet; the audience comes from a stored device
 * choice or from the signed-in student's grade band, and is school when neither says otherwise.
 */
export const AUDIENCES = ["school", "college", "work"] as const;
export type Audience = (typeof AUDIENCES)[number];

export type AudienceTheme = {
  tone: "warm" | "calm";
  density: "regular" | "compact";
  motion: "full" | "calm";
  mascot: boolean;
};

export const AUDIENCE_THEMES: Record<Audience, AudienceTheme> = {
  school: { tone: "warm", density: "regular", motion: "full", mascot: true },
  college: { tone: "calm", density: "compact", motion: "calm", mascot: false },
  work: { tone: "calm", density: "compact", motion: "calm", mascot: false },
};

export const DEFAULT_AUDIENCE: Audience = "school";
export const AUDIENCE_KEY = "yt.audience";

export function isAudience(value: unknown): value is Audience {
  return typeof value === "string" && (AUDIENCES as readonly string[]).includes(value);
}

/**
 * Who the screens are for. Order: a choice stored on this device (set by a later switch or by support), then the
 * grade band the API sent with the signed-in student (`college*` or `work*`/`adult*`), then school.
 */
export function resolveAudience(input: { stored?: string | null; bandId?: string | null }): Audience {
  if (isAudience(input.stored)) return input.stored;
  const band = (input.bandId ?? "").toLowerCase();
  if (band.startsWith("college")) return "college";
  if (band.startsWith("work") || band.startsWith("adult")) return "work";
  return DEFAULT_AUDIENCE;
}

/** Put the theme on <html>. Reduce motion (from Comfort or the device) is never overwritten. */
export function applyAudience(audience: Audience, root: HTMLElement = document.documentElement): void {
  const theme = AUDIENCE_THEMES[audience];
  root.setAttribute("data-audience", audience);
  root.setAttribute("data-density", theme.density);
  root.setAttribute("data-mascot", theme.mascot ? "on" : "off");
  const motion = root.getAttribute("data-motion");
  if (motion !== "reduce") {
    if (theme.motion === "calm") root.setAttribute("data-motion", "calm");
    else if (motion === "calm") root.removeAttribute("data-motion");
  }
}

export function storedAudience(): string | null {
  try {
    return window.localStorage.getItem(AUDIENCE_KEY);
  } catch {
    return null;
  }
}
