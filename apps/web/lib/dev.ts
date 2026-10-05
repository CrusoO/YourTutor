/** Dev tools (the /dev pages) exist only when this flag is set at build/start time. */
export function devToolsEnabled(): boolean {
  return process.env.NEXT_PUBLIC_DEV_TOOLS === "true";
}
