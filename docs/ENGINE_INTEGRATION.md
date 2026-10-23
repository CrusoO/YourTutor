# ENGINE_INTEGRATION — YourTutor consumer contract

This file is the only record of how YourTutor talks to EduVideoEngine.
It is read-only from YourTutor's perspective.  
The engine owns the contract; its canonical source is `../EduVideoEngine/docs/ENGINE_INTERFACE.md §10`.  
A change on the engine side requires an engine ADR and a version bump;  
YourTutor adopts the new version by updating this file under its own ADR.

## Contract version adopted

**v0 (draft)** — see ADR 0086 in `EduVideoEngine/docs/adr/`.  
YourTutor ADR: `docs/adr/0001-engine-video-jobs.md`.

---

## 1. Command

```
pnpm video:job <request.json> [--fresh]
```

Run by a YourTutor worker process in the **engine folder** (`../EduVideoEngine`).

| Exit code | Meaning |
|-----------|---------|
| 0         | Done |
| 1         | Failed (see `result.json` for `code`) |
| 3         | Cancelled |

SIGTERM cancels a running job.

---

## 2. Request file schema

The file is written by YourTutor to a temp path; only these fields are sent.  
**Student identity must never appear in this file.**

```json
{
  "requestId":      "uuid-v4",
  "idempotencyKey": "uuid-v4",
  "curriculum": {
    "board":   "cbse",
    "grade":   10,
    "subject": "maths",
    "nodeId":  "cbse.10.maths.ch02.s2_3"
  },
  "options": {
    "locale": "en",
    "voice":  "default",
    "fps":    24,
    "theme":  "light"
  }
}
```

Any field outside this schema is refused by the engine (error code `invalid_request`).

---

## 3. Output layout

All outputs land in `<engine>/dist/jobs/<requestId>/`.

| File | Contents |
|------|----------|
| `events.jsonl` | One JSON event per line — the live progress stream |
| `result.json`  | `{ status, code?, files: [{ name, sha256 }] }` |
| `sources.json` | Book pointer, claims with trust tier, caveats |
| `qa.json`      | QA report |
| `lesson.mp4`   | The finished video |

---

## 4. Events stream

Each line in `events.jsonl`:

```json
{ "t": "<iso8601>", "jobId": "...", "stage": "retrieve", "status": "started", "code": null, "detail": null }
```

Stages (in order): `request`, `retrieve`, `ground`, `build`, `render`, `qa`, `job`.  
Statuses per stage: `started`, `done`, `skipped`, `failed`, `cancelled`.

The job's overall state is computed from the events alone.

---

## 5. Error codes and student-visible messages

| Engine code | Student message |
|-------------|-----------------|
| `no_curriculum_data` | "This topic isn't available yet." |
| `no_lesson_for_topic` | "This topic isn't available yet." |
| `invalid_request` | "Something went wrong — please try again." |
| `knowledge_base_invalid` | "Something went wrong — please try again." |
| `ungrounded_claims` | "Something went wrong — please try again." |
| `build_failed` | "Something went wrong — please try again." |
| `render_failed` | "Something went wrong — please try again." |
| `qa_failed` | "Something went wrong — please try again." |
| `cancelled` | "Request was cancelled." |

---

## 6. First nodeId in use

`cbse.10.maths.ch02.s2_3` — Class X Maths, Chapter 2, Section 2.3  
("Relationship between Zeroes and Coefficients of a Polynomial", printed pages 18–23).

Topic list is populated from the `chapters` and `sections` tables (migrations 0009–0011),  
which are loaded from `content/curricula/`.  
Section titles and printed page numbers are shown to the student; no book text is stored or served.

---

## 7. Book map

`EduVideoEngine/knowledge/books/cbse-maths.json` is imported once as static data at  
YourTutor startup (read-only, no copy into YourTutor's content directory).  
It contains structure only: section titles, file chapter numbers, and printed page numbers.  
No book text. Rights: all rights reserved (NCERT); permitted use: reference only (see engine ledger).

---

## 8. Sources panel caveats (always shown)

In addition to every caveat in `sources.json`, the UI always appends:

- "No person has confirmed these page numbers."
- "The voice in this video is AI-generated."

---

## 9. Worker

A plain Python subprocess loop (`python -m app.video_jobs.worker`).  
Not RQ — Redis is present in the compose stack but RQ workers were never instantiated.  
See `docs/adr/0001-engine-video-jobs.md` for the decision rationale.
