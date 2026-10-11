"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

/** Routes that bring their own full-width layout (the new chat shell and the design gallery). */
const BARE = [/^\/$/, /^\/dev\/ui(\/|$)/];

/** The legacy phone-column wrapper for every other screen, until each one moves into the workspace panel. */
export default function AppFrame({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "/";
  if (BARE.some((rule) => rule.test(path))) return <>{children}</>;
  return <div className="phone">{children}</div>;
}
