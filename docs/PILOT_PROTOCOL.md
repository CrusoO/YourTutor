# Pilot protocol (draft for sign-off)

Status: **draft**. Nothing here is approved until the go/no-go review in `docs/GO_NO_GO.md` is
signed. Items marked *decide* need a person's decision; the numbers are proposals.

## 1. Question

Does practising with YourTutor for a few weeks help students in the launch chapter reach "can do
it" (ladder level 4) on its skills, safely, and do families and teachers find it usable?

## 2. Who and how long

* 30 to 50 families, or one school class, in the launch curriculum and grade (*decide*: which).
* Six weeks of free use, with the pilot starting on a Monday. Students choose when to practise;
  nobody is told how much to do. Sessions are capped by the student's grade band.
* Enrolment is by guardian, through the guardian page, with consent recorded first.

## 3. Consent

* `tutoring` is required to take part. `teacher_share` is only asked for when a teacher takes part.
  `ai_processing` and `free_text` are optional and off by default; the app works without them.
  `research_pseudonymised` is asked for only if the comparison below is used.
* Guardians can export or delete everything at any time from their page. Guests are deleted after
  the profile's retention window (90 days in `default_strict`).
* The jurisdiction profile and the consent wording are reviewed by legal before enrolment (Track B4).

## 4. What is measured

Reported weekly from `python -m app.metrics pilot` (aggregate only, no names):

* Share of mistakes followed by a response (hint, check your work, reveal, probe, break). Target 90% or more.
* Diagnosis mix (slip, misconception, prerequisite gap, incomplete procedure, disengagement, generic).
* Unhinted-correct rate on first attempts.
* Ladder progress: skills started, reached level 4, reached level 7 (retention), median days to level 4.
* Wheel-spinning alerts and how many resolve (only for families who shared with a teacher).
* Weekly active days and session completion.
* Ask (if enabled): answered, clarified and out-of-scope shares; content gaps per chapter.
* Language-model use (if enabled): fallback share and tokens per 100 calls. Leak, tone and
  grounding rates come from the offline eval suites, which must stay at their gates.

## 5. Primary outcome (pre-registered, to be confirmed before the first student starts)

**Primary:** the share of the launch chapter's skills that a student has at ladder level 4 or
higher after six weeks, among students who practised on at least eight days.

**Secondary:** time to level 4; level 7 reach at six weeks; intervention share; weekly active days.

No outcome is added or dropped after the pilot starts. If it changes, the change and its reason are
written here with a date.

## 6. Optional comparison (research module)

Only if the research module is switched on and `research_pseudonymised` consent exists:
matched pre- and post-test forms A and B (the checkpoints), delivered on paper or through the app,
scored by the server, exported pseudonymised. Groups: use as designed, or a waiting group that
starts after six weeks. Measurement only: checkpoint answers never change a student's mastery or
what the tutor does. Analysis is by group and never by individual child.

## 7. Safety during the pilot

* A distress phrase pauses tutoring, tells the guardian (and the teacher if shared) and shows only
  the authored gentle message. The operator reads every flag within one working day.
* AI replies sampled for review are read by a teacher; `bad` replies are logged and the cause is
  fixed before the next week. Pilot week one samples 100% of replies.
* Stop rules (*decide*): stop the pilot for a family on request; stop the whole pilot if a distress
  flag is mishandled, if personal data leaks, or if the leak rate eval ever fails.

## 8. Reporting

Weekly note to the pilot group (engineering, curriculum lead, teacher): the metrics above, the
open flags and bad AI replies, and the content gaps. At six weeks: the primary outcome with its
denominator, what worked, what did not, and a recommendation.
