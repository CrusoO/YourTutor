# Go / no-go review for the pilot

Status: **not signed**. Engineering fills the "evidence" column from the repository; the people who
own each gate fill the rest. Nothing here has been signed by anyone yet.

| # | Gate | Owner | Evidence | Met |
| --- | --- | --- | --- | --- |
| 1 | The launch chapter's items, lessons, scenes and passages are approved and the chapter is live | Curriculum lead | `python -m app.author status content --chapter <id>` shows READY; four reason-choice items (`ITEM.LIN1.R.0001, 0004, 0007, 0031`) approved by a teacher | |
| 2 | Policy simulation passes (PLAN section 9) | Engineering | full test suite, ordered and with two random seeds, run once at the end | |
| 3 | Phrasing evals: leak 0%, tone violations 0% | Engineering | `python -m app.llm.evals` accepted; a live run once a key exists | |
| 4 | Grounding evals: unsupported < 1%, abstention at least 95%, citations at least 98%, guard 100%, injection 0 | Engineering | `python -m app.ask.evals` accepted; a live run once a key exists | |
| 5 | Medium-locale strings reviewed by a native reviewer | Curriculum lead + reviewer | `python -m app.content locale-status content --locale <code>` shows no missing or unreviewed strings | |
| 6 | Jurisdiction profile and consent wording reviewed | Legal | profile file in `config/jurisdictions/`, consent copy | |
| 7 | Safety: distress pause and flag, PII stripping, rate limits | Engineering | `tests/hardening`, `tests/ask` | |
| 8 | Operator can install and run from the guide | Operations | a person other than the author follows `docs/OPERATOR.md`; `python -m app.operator check` prints no FAIL | |
| 9 | A restore from backup has been tested | Operations | restore log | |
| 10 | Pilot protocol approved, primary outcome pre-registered | Curriculum lead + engineering | `docs/PILOT_PROTOCOL.md` section 5 confirmed | |
| 11 | Metrics dashboard readable | Engineering | `GET /admin/metrics/pilot` | |

## Known gaps engineering is aware of

* The live language-model path has never run against a real model, so its eval numbers are offline.
* Moderation of student words is a word list.
* The offline player does not show lesson beats; offline practice only.
* Ask search is lexical; there is no embedding model.
* Rate limits are per process; a gateway is needed in front of several API processes.

## Decision

| Role | Name | Decision (go / no-go) | Date | Signature |
| --- | --- | --- | --- | --- |
| Curriculum lead | | | | |
| Engineering | | | | |
| Legal | | | | |
