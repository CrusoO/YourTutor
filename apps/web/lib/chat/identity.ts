import { setStaffToken, staffToken, today, whoAmI, hasStudentToken } from "@/lib/api";
import type { Role } from "./machine";

export type Identity = { role: Role; name?: string };

/**
 * Who is already signed in on this device, from the existing tokens. A student token wins (a guest or a
 * family student); otherwise a guardian or teacher token. Returns null when nobody is signed in.
 */
export async function currentIdentity(): Promise<Identity | null> {
  if (hasStudentToken()) {
    try {
      const me = await today();
      return me.guest ? { role: "guest" } : { role: "student", name: me.display_name };
    } catch {
      /* an expired token: fall through to "not signed in" */
    }
  }
  if (staffToken()) {
    try {
      const who = await whoAmI();
      if (who.role === "teacher") return { role: "teacher" };
      if (who.role === "parent") return { role: "parent" };
    } catch {
      setStaffToken("");
    }
  }
  return null;
}
