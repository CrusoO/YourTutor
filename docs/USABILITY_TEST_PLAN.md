# Usability test plan: five student testers

Purpose: find out whether a 15 to 18 year old can start, switch the look, finish a review and find their
chapter without help. This tests the screens, not the student. Nothing a tester types is recorded by the
app; you write down only what you see.

## Before you start

* Testers: five students aged 15 to 18, ideally a mix of phone-only and laptop users, one or two who
  prefer dark mode, and one who reads mainly in an Indic language. Get a guardian's consent for anyone
  under 18, and tell the tester they can stop at any time.
* Setup: the app running with the seed scenarios (`python -m app.dev seed_scenarios`), dev tools on. Use
  the tester's own phone if possible. Clear site data between testers (or use a private window) so each
  one meets the guest first visit.
* Two logins you will need: the `mid_chapter` student (for tasks 3 and 4, open `/dev` and tap its login)
  and a fresh browser for task 1. Screen recording is optional and needs the tester's agreement.
* Time: about 20 minutes per tester.

## What to say

Read this out and nothing more: "This is an app for revising maths. I want to see what is easy and what is
confusing. There are no wrong answers and you cannot fail. Please say out loud what you are thinking. I
will not help, but I will take notes. You can stop whenever you like."

## Tasks

Give each task as a card, one at a time, in this order.

| # | Task card (what the tester reads) | Done when |
|---|---|---|
| 1 | "You have just opened this app for the first time. Do one question." | A practice question is on screen and the tester has answered it. |
| 2 | "The screen is too bright (or too dark) for you. Change it, and make the text a bit bigger." | The theme and the text size have changed, and the tester says so. |
| 3 | "You have a review waiting. Find it and finish it." (use the `mid_chapter` student) | The tester has answered the review questions and reached the end screen. |
| 4 | "Your class is working on Linear equations. Find that chapter." | The chapter page is open. |

## What to observe without helping

* Where the tester's eyes and finger go first. Which card or button do they try? Do they notice the
  "Try one question" card, the Settings item, the Today panel and its Start button?
* Hesitation longer than five seconds. Say nothing; note the screen and what they were looking at.
* Reading aloud, or asking "what does this mean?". Write the exact word they stumbled on.
* Wrong turns: a tap that opened something they did not want, or a back button press.
* Reactions to feedback after an answer: do they understand what to do next? Do they feel judged?
* Anything they try that does nothing (a tap that is not a button, a drag, a hover).
* Do not suggest, point, or say "try the menu". If a tester is stuck for two minutes, mark the task
  "not done", note where, and move on.

## Measures (write them on the sheet for each task)

* Time on task, from the moment they start reading the card to "done". Use a phone stopwatch.
* Taps: count taps or clicks from the start screen to done (a back press counts as one).
* Errors: each time they open the wrong thing or have to go back. One mark each.
* Ease rating: ask one question after each task, "How easy was that? 1 is very hard, 5 is very easy."
* At the end, two open questions: "What was the most confusing moment?" and "What would you change first?"

Reference numbers from our own automated runs (expect people to be slower): guest first question 5 taps or
fewer from the start screen, resume 1 tap, review 1 tap, chapter 2 taps.

## Findings template

Copy one row per finding. Use the tester's own words in the third column.

| id | screen | expected | what happened | tester (T1 to T5) | severity (blocker, major, minor, polish) |
|----|--------|----------|---------------|-------------------|------------------------------------------|
| F-1 | | | | | |

## Summary sheet (fill in after all five)

| task | testers who finished | median time | median taps | total errors | median ease (1 to 5) |
|------|----------------------|-------------|-------------|--------------|----------------------|
| 1 First question | /5 | | | | |
| 2 Theme and text size | /5 | | | | |
| 3 Finish a review | /5 | | | | |
| 4 Find the chapter | /5 | | | | |

A task counts as a problem if fewer than 4 of 5 finish it, or the median ease is below 4. Take every
problem and every blocker or major finding into the next refinement round (`docs/UI_REFINEMENT_*.md`).

## Privacy

Record first names or initials only, no school, no photos of faces, no screen recording that shows a
real student's account. Keep the notes on one device and delete them when the findings are in the
refinement document.
