import { enrolPilot, setStudentId, studentLogin, today } from "./api";

const DEV_CARD_KEY = "yt_dev_pilot_card";

/** Temporary UI testing: set NEXT_PUBLIC_SKIP_LOGIN=true (see docker-compose web env). */
export function skipLogin(): boolean {
  return process.env.NEXT_PUBLIC_SKIP_LOGIN === "true";
}

let booting: Promise<void> | null = null;

export function ensureDevStudent(): Promise<void> {
  if (!skipLogin() || typeof window === "undefined") {
    return Promise.resolve();
  }
  if (booting) return booting;
  booting = (async () => {
    const cached = store()?.getItem(DEV_CARD_KEY);
    if (cached) {
      try {
        const { family_code, pin } = JSON.parse(cached) as { family_code: string; pin: string };
        await studentLogin(family_code, pin);
        const me = await today();
        setStudentId(me.student_id);
        return;
      } catch {
        store()?.removeItem(DEV_CARD_KEY);
      }
    }
    const card = await enrolPilot({
      first_name: "Dev",
      grade: 9,
      board: "bhutan",
      paper_ref: "dev-skip-login",
      scopes: ["tutoring", "research_pseudonymised"],
    });
    store()?.setItem(
      DEV_CARD_KEY,
      JSON.stringify({ family_code: card.family_code, pin: card.pin }),
    );
    await studentLogin(card.family_code, card.pin);
    const me = await today();
    setStudentId(me.student_id);
  })();
  return booting;
}

function store(): Storage | null {
  return window.localStorage;
}
