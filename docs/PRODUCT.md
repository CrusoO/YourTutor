# Brownie: the product, end to end

Source: Brownie-COMPLETE-PLAN-v3.md Part 1, and Brownie-Voice-Marketing-and-Pricing.md sections 4 to 6 (5 Nov 2026), in the parent folder (not in this repo). Adapted for the YourTutor repo.
Labels from the sources are kept: **Checked** (verified with a source), **Memory** (from memory, to verify), **Assumption** (an estimate to measure), **Judgment** (a recommendation).
Roadmap: [ROADMAP.md](ROADMAP.md). Decisions: [DECISIONS](DECISIONS/).

## 1. The promise

> Brownie finds the exact mistake you are making, fixes it with you, and proves it stayed fixed. It is never confidently wrong.

Everything follows from three words: **diagnose, fix, prove**.

## 2. Who Brownie is for (in launch order)

| Order | Who | When | Through whom |
|---|---|---|---|
| 1 | Class 10 students: Board Sprint (maths, Algebra first) | Live 15 Dec 2026, through the Feb 2027 boards, and the CBSE second Class 10 exam about May 2027 | Teacher class codes; guardian sign-up with a consent record |
| 2 | Adults (18+): college students, job seekers, self-learners | From 15 Dec 2026 | Google or email sign-in, self-serve |
| 3 | Classes 6 to 8 in affordable private schools (the strategic wedge; fractions and decimals first) | New session, April 2027 | The school (data fiduciary); Brownie is its processor |
| 4 | Nepal (Nepali language) | After the April pilot proves out | Schools |
| 5 | College STEM and coding; government-exam aspirants | 2028+ | Colleges; self-serve |
| 6 | Work skills (IT, data, office) | 2029+ | Companies |
| 7 | Everyone, lifelong | 2035 to 2040 north star | All channels |

See [ADR-002](DECISIONS/ADR-002-first-users-and-order.md).

## 3. What it feels like (four people, one week)

These are illustrations from the plan, not shipped behaviour.

**Riya, Class 10, Board Sprint (minor, school code).**
- 7:40 pm: she opens Brownie from her teacher's class link. Brownie says it remembers the last fixed mistake and offers 3 quick ones, about 10 minutes. Buttons: [Let's go] [Something else].
- She answers on the maths keypad. A tick or cross shows in under 0.3 seconds.
- On a wrong answer, Brownie already knows which mistake it was, because her number matches a known mistake function. It asks a guiding question.
- She taps [Why?]. Brownie explains in two short bubbles, in Hinglish if she wrote in Hinglish, and reads it aloud when she taps the speaker.
- After 2 hints she still cannot do it, so a worked example follows, then a twin question she solves herself.
- Two days later, a check question confirms the mistake stayed fixed.
- Late at night (the plan's example is 11:15 pm), Brownie gently suggests sleep.
- If she types something showing distress, Brownie stops the topic, responds warmly, shows verified helplines, and alerts her teacher or counsellor through the school process.

**Sunita Ma'am, maths teacher.**
- Monday morning: one screen shows the class's most common mistakes, with counts.
- Below it: a printable 10-minute warm-up aimed at those mistakes, with an answer key.
- She approves 3 new questions in two minutes. They show "by Sunita Ma'am".
- Brownie should save her more time each week than it costs her.

**Riya's father (guardian).**
- Sunday: a specific note about one mistake she fixed. No marks, no comparisons.

**Aman, 21, engineering student (adult).**
- Signs in with Google, says he is 18+, and asks an open question about simultaneous equations in circuits.
- Brownie answers (adult tier), checks the maths with the solver, and when he is stuck twice on the same step, that one turn escalates to Sonnet.

## 4. The surfaces

| Surface | For | What it does |
|---|---|---|
| Chat thread (one continuous conversation) | Learners | Lessons, practice cards, hints and questions in one scroll. Streamed short replies, quick-reply chips, a maths keypad, push-to-talk voice input (live, editable transcript; spoken answers read back before checking) and voice-out |
| Practice player | Learners | The deterministic engine: item, answer, solver check, diagnosis, hint ladder, mastery |
| Teacher view | Teachers | Class mistake list, printable warm-up, class code management, approval cards |
| Review screen | Teachers and staff | Swipe-approve items: correct answer (solver-verified), wrong options with mistake labels, Hindi text, provenance. 2 approvals = live |
| Guardian view and weekly note | Parents | Specific progress, consent records, export and delete |
| School admin | Schools | Enrol classes, class codes, consent records, data agreement, the school learning-health report |
| Video lessons (EduVideoEngine) | Learners | Short explainer videos, pre-rendered for popular topics, streamed segments for new ones |
| Staff and ops | Founder | Content pipeline, metrics, budgets, safety flags, audits |
| Later: Teacher Feed, Mistake Monsters, Catch Brownie, WhatsApp Autopilot | n/a | Gated by the roadmap |

The video engine is a separate project. YourTutor meets it only through its static package and the contract in `docs/ENGINE_INTEGRATION.md`. See [adr/0001-engine-video-jobs.md](adr/0001-engine-video-jobs.md).

## 5. The system, layer by layer

```
CLIENT (Next.js 15, React 19)
  Chat thread, Practice player, Maths keypad, Quick-reply chips, Voice-out player
  safeStorage (never throws), AbortController timeouts, SSE stream reader, i18n en/hi
  Closed action registry (matched on-device, never from model output)
        |  HTTPS (CSP, headers); bearer to httpOnly cookie (Phase 2)
API (FastAPI)
  Auth: guest + age question, email OTP, Google, class code, family PIN, tiers
  Safety gate (every free-text route): lexicon (en/hi/Hinglish) + Haiku classifier
    -> one distress flow (stop, warm message, verified helplines, flag, pause, minimal record)
  Learning core (deterministic):
    SymPy verifier -> mistake functions + diagnosis -> policy (hint ladder, gating,
    wheel-spinning) -> BKT + 7-level ladder + FSRS (spaced checks)
  LLM layer (Anthropic SDK, async, streaming):
    router: Haiku 5.5 default, Sonnet 5.5 for hard turns (rules, 15% cap)
    answer-leak guard (verifier equivalence), refusal handling, prompt caching
    global daily and monthly budgets (shared counters), semaphore, timeouts
  Content: approved items only in prod, provenance, review workflow
  Privacy: school mode (fiduciary/processor), consent records, retention jobs, export
        |
  Postgres (Neon)            Offline content pipeline          EduVideoEngine
  events log, mastery,       templates + mistake functions     warm TTS + clip cache, layout,
  FSRS, consents             Sonnet Batch drafts -> verifier   frames piped to ffmpeg,
                             -> review (2x) -> approved        streamed segments, pre-rendered catalog
Ops: error tracking (personal data scrubbed), structured logs, uptime alerts,
     backups + restore test, CI (safety eval gate)
```

This is the target design. The repo may not match it yet. Where code and this document disagree, trust what is measured now, and note it.

## 6. One learner turn

1. The learner taps a chip, types, speaks, or enters an answer on the keypad.
2. If it is an answer:
   - the verifier checks it (SymPy equivalence, so 1/2 equals 0.5);
   - a tick or cross shows in under 300 ms;
   - mistake functions test whether the wrong value matches a known mistake;
   - the diagnosis picks a misconception, a slip, a prerequisite gap or an incomplete procedure.
3. The policy picks the next move: hint 1, hint 2, worked example, twin question, prerequisite probe, or a break. It also updates BKT, the ladder and FSRS (state is rebuildable from the events log).
4. If words are needed:
   - the router picks Haiku (default) or Sonnet (hard-turn rules, [ADR-005](DECISIONS/ADR-005-models-and-routing.md));
   - the safety gate screens the learner's text;
   - the model streams a short reply in the learner's language mix;
   - the answer-leak guard checks it does not reveal the answer before 2 hints and an attempt ([ADR-006](DECISIONS/ADR-006-answer-reveal-rule.md));
   - the safety classifier screens the output;
   - on a refusal or error, Brownie uses authored text.
5. The UI shows 1 or 2 short bubbles, one question and 3 or 4 chips, with voice-out on tap.
6. Logged: events, model, escalation reason, tokens, time to first token. **Not logged: the child's message text in production.**

## 7. The knowledge layer ("never confidently wrong")

The verification ladder:
1. Approved item bank: the stored answer, solver-verified.
2. Solver: two independent parses, then back-substitution, then sanity rules, then equivalence checks.
3. Teacher-reviewed fact list with sources.
4. Abstain: "Let's check this with your teacher", and the question goes to the review queue.

Brownie says "wrong" **only when a rung proved it.**

Mistake functions: each misconception is a small function over the item's numbers that returns the wrong answer a student with that mistake would give. Templates plus the solver produce verified items. See [ADR-008](DECISIONS/ADR-008-content-next.md).

Content law (from the plan):
- Never copy textbook or board-paper text.
- NCERT textbooks are non-commercial and no-derivatives, and NCERT terms forbid use in software.
- Openly licensed sources may be reused with attribution: Illustrative Mathics 6 to 8 (2019 edition only) and OpenStax.
- Avoid Khan Academy and CK-12 (non-commercial licences).
- Every item stores source, licence, author and reviewers.

## 8. Safety, privacy and the action registry

Safety:
- Two-layer detection on every free-text route, on input and output.
- An exam-stress category, and a gentle late-night stop for minors.
- Helplines are verified by the founder or counsel before production starts. Until then they carry `verified: false`. This document lists no helpline numbers.
- A safety eval of 300 or more phrases in CI: recall at least 0.98, false positives at most 3%.

Tiers: guest (a minor by default), minor, adult, corporate. Tiers change scope and safety strictness, never the action list.

The closed registry holds 7 actions: `start_practice`, `continue_learning`, `show_subjects`, `switch_language`, `new_chat` (needs confirmation), `sign_in_prompt`, `help`. It never widens without a written proposal and the founder's approval. Model output never becomes an action.

Privacy:
- School mode: the school is the data fiduciary, Brownie is the processor, with consent records, a data processing agreement and class codes.
- Direct minors: a guardian consent record, and limited tracking until counsel decides.
- Retention: OTPs 24 h, rate events 7 days, LLM metadata 90 days, no children's text stored in production.
- Export and delete are complete.
- Anthropic is the only LLM vendor in production ([ADR-004](DECISIONS/ADR-004-llm-vendor.md)).
- Law clock: DPDP core duties apply from about 13 to 14 May 2027. EU AI Act education obligations from 2 Dec 2027, if the EU is served. Counsel decides. This document makes no legal conclusion.

## 9. Voice

From [ADR-001](DECISIONS/ADR-001-launch-shape-and-voice.md) and the voice paper:
- Push-to-talk, not always listening.
- The transcript shows live and is editable.
- Spoken answers are parsed by a deterministic maths-speech parser (for example "x square" becomes x^2, "barabar" becomes =) and read back before checking. Never auto-submit.
- Language is detected per utterance (English, Hindi, Hinglish) and Brownie replies in the same mix.
- Barge-in: tapping the mic or stop cuts Brownie's speech.
- Targets: end of speech to transcript under 1 s; end of speech to first spoken reply word under 2.5 s.
- Audio is never stored by Brownie. Vendor contracts must say no retention and no training (check before signing). Prefer India data residency for Indian children.
- Voice is off by default for minors until the class's or guardian's consent includes voice.
- If recognition fails, show a try-again-or-type message and keep the keypad open.

Provider options (choose by bake-off, keep two). Prices are as listed in the voice paper and must be confirmed on each vendor's official page before signing up:

| Role | Option | Listed price and label |
|---|---|---|
| Speech-to-text, primary candidate | Sarvam (Saarika/Saaras) | Rs 30 per hour, billed per second [Checked, official docs] |
| Speech-to-text, alternative | ElevenLabs Scribe v2 Realtime | about $0.39 per hour [aggregators] |
| Speech-to-text, alternative | Deepgram Nova-3 Multilingual | about $0.0058 to 0.0092 per minute [aggregators disagree] |
| Speech-to-text, pricier | Google Chirp 3 | about $0.016 per minute [aggregators] |
| Speech-to-text, risky | Browser Web Speech API with on-device mode | Free; experimental; adults only, opt-in, if at all |
| Text-to-speech, English | Kokoro (self-hosted, already in the engine) | about Rs 0 extra [Assumption] |
| Text-to-speech, Hindi/Hinglish | Sarvam Bulbul, or Kokoro hf_alpha if it passes native review | Rs 15 to 30 per 10,000 characters [Checked for v2/v3; V4 Flash from a news report] |

## 10. Engagement rules (habits, never addiction)

- Every session gives back more than it takes. The end-of-week test: would the person be glad they spent this time?
- Children: no infinite feeds, individual leaderboards, autoplay, or push notifications to children. Sessions end. Class goals, not ranks.
- Teachers: the hook is time back (the mistake list, the warm-up, the parent notes). Measured as net minutes saved per week.
- Parents: one specific weekly note.
- Adults: an optional finite practice set; a verified skill record later.
- Habits take about 66 days (range 18 to 254) [as stated in the plan], so judge the loops at week 8 to 10.

## 11. Models and money

| Item | Number |
|---|---|
| Live model | Claude Haiku 5.5 (`claude-haiku-5-5`): $0.10 in / $0.50 out per million tokens [Checked] |
| Hard turns (15% or less) | Claude Sonnet 5.5 (`claude-sonnet-5-5`): $2 / $10. Offline drafting through Batch (50% off) [Checked] |
| LLM cost per learner per month | about $0.08 (all Haiku, explain-heavy) to about $0.31 (at the Sonnet cap); practice-only about $0.008 |
| School price to test | Rs 300 to 600 per student per year |
| Anchors | School management software about Rs 80 to 500 per student; LEAD about Rs 967 [Research, per the plan] |
| Budget for the first 100 learners | about $10 to 20 per month LLM plus hosting; hard caps in the console and the app |
| Exchange rate used | $1 = Rs 88 [Assumption; update monthly] |

With voice, full variable cost per learner is about Rs 5 to 14 a month (light), Rs 23 to 77 (typical) and Rs 74 to 249 (heavy), roughly Rs 0.15 to 8 per day [Assumption; measure in v1.0]. Voice now costs more than the LLM. The biggest levers are cached clips for authored text, tap-to-listen by default for paid voices, self-hosted Kokoro where native reviewers accept it, and the Sonnet cap. Fair-use caps: spoken input 10 min per day for students, 20 for adults; paid auto-read only on paid plans.

Fixed monthly cost at early stage is about $60 to 150 (Rs 5,300 to 13,200) [Assumption and aggregator figures]. Break-even is about 100 to 260 paying users, or 1 to 2 schools of about 300 students [Judgment].

### Plans (recommendation, not final; run the pricing research first)

Target: at least 70% gross margin at typical use, with caps protecting heavy use. Prices include GST; check with a chartered accountant. Margins are after 18% GST and a payment fee of about 2.4%.

| Plan | Who | Price | Includes |
|---|---|---|---|
| Free | Everyone (adults directly; students via teacher or guardian) | Rs 0 | Unlimited practice with the solver; 10 AI explanations per day; 5 spoken minutes per day; tap-to-listen (Kokoro) |
| Teacher | Teachers | Rs 0 forever | Class codes, mistake lists, warm-ups, approval cards |
| Board Sprint Pass | Class 10 students (bought by a parent) | Rs 299 until the Feb/Mar boards, plus Rs 149 for the May improvement sprint | All Board Sprint packs; 15 spoken min per day; Hindi voice; parent note |
| Student | Students, through a guardian | Rs 99 per month or Rs 799 per year | All packs; 15 spoken min per day |
| Adult Plus | 18+ | Rs 199 per month or Rs 1,499 per year | Open topics; 20 spoken min per day; Sonnet hard turns; Bulbul voices |
| School | Classes 6 to 8 (April), Class 10 sprints | Rs 499 per student per year list; pilot Rs 299 for the first term, or a free one-term pilot with a renewal commitment | Everything, plus teacher tools and the school learning-health report; fair-use voice (5 to 10 min per day, Kokoro voices) |

The voice paper's own margin estimates range widely (for example about 0 to 68% for Board Sprint Pass). They depend on real voice usage. The paper says to raise prices or tighten caps before v1.2 if research sprint R2 lands at the high end, and to price the Board Sprint Pass at Rs 399 if R2 shows heavy voice use.

Anchors [Checked unless noted]: a PW Class 10 batch costs about Rs 1,499 to 2,200 (the source cites PW pages). ChatGPT Go at Rs 399 per month [Research, earlier]. Brownie should be a cheap add-on that fixes your mistakes, not a replacement batch [Judgment].

Payments: only through a provider the founder approves. Test mode only until the founder approves go-live. Never store card or UPI details.

### Advertising rules (from the voice paper)

- DPDP s.9(3) says a data fiduciary shall not do targeted advertising directed at children [Memory, to verify]. So no targeted ads at students. Reach them through teachers, schools and parents. Use ads only for adults.
- Check ASCI education-ad guidelines [Memory, to verify].
- No "guaranteed marks" or "top 1%" claims. No fear or countdowns aimed at children. Show real product footage only [Judgment].
- Channels in order: teachers (free forever), short organic demo videos aimed at parents and teachers, parents (weekly note), schools, adults (targeted ads to 18+ only), Hindi media and creators (paid, disclosed), product-led sharing (adults only; class quests for students).

API rules: no temperature or other sampling settings; no prefill; check `stop_reason`; structured outputs; cache prefixes of 512 tokens or more; count tokens with `count_tokens`.

## 12. How we measure

- **North star:** mistakes fixed and still fixed 14 days later, per active learner per week.
- **Learning:** outside-test gain versus a comparison group (Board Sprint: pre-boards with school consent; pilot: a pre/post outside test).
- **Trust:** published content error rate under 1%; safety eval scores.
- **Teachers:** net minutes saved; weekly active.
- **Students:** 3 or more sessions a week; drop-off after Brownie's first message.
- **Parents:** weekly note opened.
- **Business:** renewals; cost per learner; Sonnet share.
- **Speed:** reaction under 300 ms; time to first token p50 at most 1.5 s; first video play under 15 s.

## 13. What Brownie will not do

- Guess answers, or mark a child wrong without proof.
- Copy textbooks or board papers.
- Use addictive mechanics on children.
- Send children's text to free-tier AI vendors.
- Store anyone's voice recordings. Audio is streamed to the speech recogniser and discarded. Minors use voice only when the school's or guardian's consent covers it.
- Run targeted ads at children.
- Widen the action registry quietly.
- Sell high-pressure packages to parents.
- Go wide before each gate is passed.
