import type { ContextLike } from "@/lib/chat/machine";

/**
 * English copy for the signed-in welcome on the chat home. Hindi and Nepali show this English until a person
 * translates it (the app never machine-translates).
 */
export const introCopy = {
  signedInAs: "You are signed in as {name}.",
  signedInStudent: "You are signed in.",
  teacher: "You are signed in as a teacher.",
  guardian: "You are signed in as a parent or guardian.",
  canAsk: "You can ask me about {topics}. Tap a button, or type a topic in the box above.",
  soon: "Other subjects and classes are coming.",
  notYet: "Nothing is ready for your class yet. For now Brownie has {subjects}.",
  none: "Nothing is ready for learners yet. We are adding subjects and classes.",
  teacherHelp: "See how your classes are doing and who needs a hand.",
  guardianHelp: "See how your child is doing and manage their account.",
  chipStart: "Start {topic}",
  chipRevise: "Revise what I learned",
  chipChapters: "Pick a chapter",
  chipClasses: "See my classes",
  chipStuck: "Who is stuck?",
  chipChild: "How is my child doing?",
  chipAdd: "Add a child",
} as const;

/** The subjects that have real content right now, as "Class 10 Maths" style labels (never a made-up list). */
export function liveSubjects(
  ctx: ContextLike | null,
  classLabel: (grade: number) => string,
  prettify: (id: string) => string,
): string[] {
  const seen = new Set<string>();
  for (const curriculum of ctx?.curricula ?? []) {
    for (const g of curriculum.grades) {
      for (const s of g.subjects) {
        if (s.books.length > 0) seen.add(`${classLabel(g.grade)} ${prettify(s.id)}`);
      }
    }
  }
  return [...seen];
}
