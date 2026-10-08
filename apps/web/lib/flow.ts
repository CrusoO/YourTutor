import type { ChapterStatus } from "@/lib/api";
import type { Messages } from "@/lib/messages";

/** Plain-words label for a skill or chapter status. */
export function statusLabel(copy: Messages, status: ChapterStatus): string {
  switch (status) {
    case "not_started":
      return copy.statusNotStarted;
    case "learning":
      return copy.statusLearning;
    case "can_do_it":
      return copy.statusCanDoIt;
    case "solid":
      return copy.statusSolid;
    case "review_due":
      return copy.statusReviewDue;
    case "coming_soon":
      return copy.comingSoon;
  }
}

/** Why a session ended, in words a student can read. Never shows a raw code. */
export function reasonCopy(copy: Messages, reason: string | null | undefined): string {
  switch (reason) {
    case "soft_cap":
      return copy.reasonSoftCap;
    case "hard_cap":
      return copy.reasonHardCap;
    case "idle":
      return copy.reasonIdle;
    case "break":
      return copy.reasonBreak;
    case "chapter_complete":
      return copy.reasonChapterComplete;
    case "consent_revoked":
      return copy.reasonConsent;
    default:
      return copy.reasonOther;
  }
}

export type DoneSummary = {
  learned: { id: string; title: string; status: ChapterStatus }[];
  practised: { id: string; title: string; status: ChapterStatus }[];
  skills: { id: string; title: string; status: ChapterStatus }[];
  next: { id: string; title: string } | null;
  remaining_active_minutes: number;
  chapter: { id: string; title: string; status: ChapterStatus } | null;
  recommended_chapter: string | null;
};
