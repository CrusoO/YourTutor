import type { Messages } from "@/lib/messages";

/** Time-of-day greeting key from the visitor's own clock hour (0-23). Pure, so it is easy to test. */
export function greetingPart(hour: number): "chatGreetMorning" | "chatGreetAfternoon" | "chatGreetEvening" | "chatGreetNight" {
  if (hour >= 5 && hour < 12) return "chatGreetMorning";
  if (hour >= 12 && hour < 17) return "chatGreetAfternoon";
  if (hour >= 17 && hour < 22) return "chatGreetEvening";
  return "chatGreetNight";
}

/**
 * "Good morning, Mina" for a known name; just "Good morning" for a signed-in adult with no nickname; a
 * friendly generic line for guests and unknown visitors.
 */
export function greeting(copy: Messages, hour: number, name?: string | null, signedInAdult = false): string {
  const nickname = (name ?? "").trim();
  if (!nickname) return signedInAdult ? copy[greetingPart(hour)] : copy.chatGreetGuest;
  return copy.chatGreetNamed.replace("{greet}", copy[greetingPart(hour)]).replace("{name}", nickname);
}
