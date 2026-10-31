# ADR 0001: Integrate EduVideoEngine video jobs into YourTutor

**Status:** accepted (2026-10-23)  
**Engine contract:** `ENGINE_INTERFACE.md §10`, adopted at v0  
**Engine ADR:** EduVideoEngine `docs/adr/0086-curriculum-map-and-video-job.md`

---

## Context

A student should be able to pick a verified CBSE maths topic, request a narrated lesson video  
from the EduVideoEngine, and watch it with a Sources panel that cites the book section and  
explains provenance and caveats.

The engine produces `lesson.mp4`, `sources.json`, `qa.json` and `events.jsonl` by running  
`pnpm video:job <request.json>` (a subprocess, not an import).  
A build takes several minutes, so the job must be asynchronous.

---

## Decision

### 1. Integration mechanism: subprocess, no shared code

YourTutor spawns `pnpm video:job` in the engine folder via a Python subprocess.  
No engine code is imported; no `node_modules` are shared; no engine paths appear in YourTutor code.  
The only data crossing the boundary is:

- **In:** a JSON request file written by YourTutor to a temp path  
- **Out:** files in `dist/jobs/<requestId>/` that YourTutor reads after the process exits

This satisfies the rule of independence (ENGINE_INTERFACE.md §1).

### 2. Student identity stays in YourTutor

The `video_jobs` table links `student_id` → `students`.  
The engine request file carries only curriculum identity (`nodeId`, locale, options).  
The student's identity never leaves YourTutor's database.

### 3. Worker: plain Python subprocess loop

Redis and the `rq` package are present in the compose stack, but no RQ worker  
was ever instantiated in this repository — Redis was only pinged.  
A plain poll-and-spawn loop (`python -m app.video_jobs.worker`) is sufficient for the  
pilot (one job at a time is the expected load) and adds no new infrastructure.  
If concurrent jobs or distributed workers become necessary, migrate to RQ at that point.

The worker:
- Claims jobs with `FOR UPDATE SKIP LOCKED`  
- Writes a temp request file with no student data  
- Runs the engine command with `subprocess.Popen`  
- Tails `events.jsonl` to write live progress into the DB row  
- Enforces a configurable hard timeout (`VIDEO_JOB_TIMEOUT_SECONDS`, default 600)  
- Sends SIGTERM on cancel; reads exit code 3 as `cancelled`  
- Resets any row stuck in `running` at startup (crash recovery)

### 4. Topic list: curriculum tables, not a copied map

The topic picker reads `chapters` and `sections` tables (migrations 0009–0011).  
Section titles and printed page numbers from `cbse-maths.json` are imported once as  
static data at startup — never copied into YourTutor's content directory.  
No book text is stored, shown or logged anywhere.

### 5. Error codes: two classes of message

`no_curriculum_data` and `no_lesson_for_topic` → "Not available yet."  
All other failure codes → "Something went wrong — please try again."  
Both messages are non-alarming and do not expose engine internals.

### 6. Sources panel: verbatim caveats plus two fixed lines

`sources.json` caveats are shown verbatim.  
Two additional lines are always appended regardless of what `sources.json` contains:

- "No person has confirmed these page numbers."  
- "The voice in this video is AI-generated."

These are non-negotiable disclosures; they may never be suppressed.

---

## Consequences

- `docs/ENGINE_INTEGRATION.md` is the canonical consumer-side record; update it when the  
  engine bumps the contract version.
- Migration 0026 (`video_jobs`) is the DB anchor for this feature.
- No new infrastructure is needed for the pilot; a single `python -m app.video_jobs.worker`  
  process is sufficient.
- If the engine folder is absent or the command is not found, the worker logs the error and  
  the job row stays `queued`; the student sees "Something went wrong — please try again."
- The feature is behind normal consent (`tutoring` scope, same as sessions).

---

## What this does not decide

- Audio format or quality (engine decision, ADR 0084)  
- Whether the player in the engine package replaces YourTutor's own lesson player (§3 of  
  ENGINE_INTERFACE.md; deferred to INT work package)  
- Offline caching of video files (a host concern; deferred)
