# Brownie research plan

Source: Brownie-COMPLETE-PLAN-v3.md, Part 4, and Brownie-Voice-Marketing-and-Pricing.md sections 3 and 6 (5 Nov 2026), in the parent folder (not in this repo).
Roadmap versions are in [ROADMAP.md](ROADMAP.md).

## 1. How research turns into a version

```
Question backlog -> Research sprint (2 weeks) -> Memo (facts labelled Checked / Memory / Assumption)
-> Decision record (docs/DECISIONS/ADR-xxx) -> Feature Cards -> Build behind flags -> Release -> Measure -> back to the backlog
```

Rules:
1. Every claim is labelled Checked, Memory or Assumption. Anything decision-critical gets two independent sources or a direct measurement.
2. Research with minors happens **only through schools or guardians, with consent**. No recordings without consent. Names are removed.
3. Every version starts with a research sprint, so the next version's plan exists before the current one launches.
4. Agents never run studies on minors. They prepare protocols and consent forms for the founder and the schools.
5. Do not store children's text. Use synthetic paraphrases for safety eval refreshes.

## 2. Research tracks (always on)

| Track | Question it answers | Methods |
|---|---|---|
| Learning efficacy | Does Brownie fix mistakes durably and move outside scores? | Outside tests; the 14-day "still fixed" metric; comparison groups; honest null results |
| Safety | Are we catching distress and harm in all languages, without blocking learning? | Monthly eval-set refresh from flagged cases (no raw child text stored; use synthetic paraphrases); a counsellor review; red-teaming |
| Language | Is Hindi and Hinglish natural and correct? | Native reviewers; blind ratings; error logs |
| Content and law | Are items original, licensed and correct? | Provenance audits; near-duplicate scans; monthly 200-item audit; counsel questions |
| Teachers | Does Brownie save teachers time? | Time logs; interviews; weekly active use |
| Market and pricing | Who pays, how much, and do they renew? | Principal interviews; price tests; renewal tracking |
| Habits and UX | Does the conversation feel natural? Where do people drop off? | Usability tests; chip vs typing share; drop-off funnels |
| Models and cost | Is the routing right? Is the cost per learner on target? | Blind quality ratings of Haiku vs Sonnet on hard turns; cost dashboards |
| Voice (now, v1.0) | Is the speech recognition and the maths-speech parsing accurate, fast and private enough? | Consented **adult** clips first, then children's clips through schools with consent; code-mix-aware error scoring; maths-term accuracy; latency; cost per minute |
| Pricing | What will parents, adults and schools pay, and does usage fit our margins? | Price surveys; landing-page price tests; principal interviews; a monthly cost-per-learner review |
| Competition | What do PW, Vedantu, free AI and coaching do in exam season? | Teardowns; student interviews |

## 3. Dated research calendar

| Sprint | Dates | Feeds | Questions | Methods and sample | Output |
|---|---|---|---|---|---|
| **R1 Board Sprint discovery** | 6 to 20 Nov 2026 | v1.0 | Where exactly do Class 10 students lose marks in Algebra? What board question formats matter? What do teachers need before pre-boards? Which helplines and exam-counselling lines are current? | 5 Class 10 maths teachers, 10 students (through teachers or guardians), 5 parents; public board format specs (formats only, no copying); helpline verification calls; counsel on class code and guardian consent | A mistake map for linear equations; format spec; verified helpline list; a consent design memo. Plus voice and price research: a speech-to-text bake-off (300 consented adult clips: en/hi/Hinglish, maths phrases, noise, low-end phones), a maths-speech parser test, a voice listening test (Kokoro vs Bulbul), vendor contract checks (no retention, no training), and a 30-parent price survey |
| **R2 Live learning** | 15 Dec 2026 to 15 Jan 2027 | v1.1 | Does the conversation feel natural? Do chips and keypad work on low-end phones? Is the routing right? Where do students drop off? | Usage analytics; 8 usability sessions; 50 hard turns rated blind by 2 teachers (Haiku vs Sonnet); cost tracking | UX fixes list; routing thresholds tuned; v1.1 cards |
| **R3 School sales and 6-8 content** | 5 Jan to 15 Mar 2027 | v1.2 | What will principals pay for April? Which fractions and decimals mistakes are most common in Classes 6 to 8? Which outside test do we use? | 10 principal interviews and price test; Teacher Autopilot with 5 to 10 teachers (name mistakes, approve cards); choose and pilot an outside test instrument | Price decision; the fractions mistake library; test protocol; 2 to 3 signed schools |
| **R4 Board Sprint outcomes** | 25 Feb to 31 Mar 2027 | v1.2 / v1.3 | Did active users do better on pre-boards or boards than similar classmates? | With school consent: compare scores; interviews | An honest results memo (including a null result if that is the finding) |
| **R5 Consent and law** | 1 Feb to 30 Apr 2027 | v1.3 | Is everything ready for DPDP core duties (about 13 to 14 May)? | Counsel review of notices, consent flows, retention and processor terms | Signed-off legal pack |
| **R6 Pilot term** | Apr to Sep 2027 | v2.0 | Learning gains (pre/post outside test), teacher minutes saved, habit loops at week 8 to 10, error rate | A pre-registered pilot plan; monthly checks; teacher and parent interviews | The pilot report |
| **R7 v2 scoping** | Jul to Oct 2027 | v2.0 | Voice input improvements; WhatsApp Autopilot; Nepal discovery; Mistake Monsters tests | Adult voice-sample tests; 10 Nepali teacher interviews; small A/B tests on the game loop | v2.0 decision record and feature cards |
| **R8 onward** | 2028+ | v3+ | Colleges, coding, aspirants; then work skills; then global | The same cycle | n/a |

## 4. Voice studies (from the voice paper, section 3)

| # | Study | How | Pass bar | When |
|---|---|---|---|---|
| V1 | Speech-to-text bake-off | 300 consented **adult** utterances: English, Hindi and Hinglish; maths phrases; quiet and noisy; low-end Android mic. Score with a code-mix-aware method, maths-term accuracy, latency and cost | Maths-term accuracy 95% or more *after* the parser and read-back; p50 latency under 1 s | R1, 6 to 20 Nov |
| V2 | Maths-speech parser accuracy | The same clips through the parser; count wrong expressions that would have been checked without read-back | 0 silent mis-parses | R1 |
| V3 | Children's audio (later, with consent) | Only through a school, with guardian consent; a small sample | Within 5 points of the adult accuracy | R2/R3 |
| V4 | Voice listening test | 10 students and 5 teachers rate Kokoro-en, Kokoro hf_alpha and Bulbul voices (1 to 5) | Average 4.0 or more for the chosen voice | R1/R2 |
| V5 | Vendor contracts | Data retention, training use, location, deletion, sub-processors, price lock | No retention and no training, in writing | Before v1.0 |
| V6 | Real usage | After launch: voice minutes per session, characters listened, cache hit rate | Recalibrates the cost model | R2 |

## 5. Pricing research (from the voice paper, section 6)

1. **Parents (R1/R2):** a price-sensitivity survey with 30 Class 10 parents, plus landing-page price points.
2. **Adults (R2):** an A/B test of price points for 4 weeks. Measure conversion and 30-day retention.
3. **Schools (R3):** 10 principal interviews. What will they pay, and what proof do they need?
4. **Usage (R2):** real spoken minutes, characters listened, cache hit rate and Sonnet share. Recompute costs and adjust caps or prices before v1.2.
5. **Tax and payments:** GST treatment of online education services and the invoice format, checked with a chartered accountant. The payment gateway's UPI fee on the chosen plan.

## 6. What each research memo must contain

- **Question:** the decision it feeds.
- **Method and sample**, including the consent route.
- **Findings**, each labelled Checked, Memory or Assumption, with sources.
- **What would change our mind.**
- **Recommendation**, and the Feature Cards it produces.

## 7. Instrumentation the product must log (without children's text)

- funnels;
- chip vs typing share;
- time to first reaction and time to first token;
- Sonnet share and reasons;
- mistakes fixed and still fixed after 14 days (the north star);
- teacher time-on-task;
- content error audits.

At the start of each stage, list the research questions the next version needs and the data required to answer them.
