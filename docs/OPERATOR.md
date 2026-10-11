# Operator guide: run a pilot

For the person who installs and looks after YourTutor for a school or a group of families. You need
a machine with Docker, Python 3.12 or newer, and Node 20 or newer. Commands are run from the
repository root unless a folder is named.

## 1. First install

```bash
docker compose up -d postgres redis                  # the database (pgvector) and the cache
cd apps/api
python -m pip install -e .                           # or the packages in pyproject.toml
python -m alembic upgrade head                       # create the tables
python -m app.content validate ../../content/        # must print OK
python -m app.content load ../../content/            # load skills, items, lessons, passages
cd ../web && npm install && npm run build
```

Settings are environment variables (a `.env` file next to `apps/api` works; never commit it).
The ones that matter:

| Variable | Pilot value | What it does |
| --- | --- | --- |
| `APP_ENV` | `production` | Blocks authoring tools. |
| `ALLOW_DRAFT_CONTENT` | `false` | Only approved content is served. |
| `DEV_TOOLS` | `false` | Hides the preview pages and dev endpoints. |
| `TOKEN_PEPPER` | a long random string | Hashes tokens and codes. Changing it signs everyone out. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `OTP_FROM_EMAIL` | your mail server | Sign-in codes and weekly reports. Without `SMTP_HOST` they only go to the log. |
| `JURISDICTION_PROFILE` | `default_strict` | Consent scopes, quiet hours, retention, report channels (`config/jurisdictions/`). |
| `PUBLIC_WEB_URL` | the guardian page address | The link in weekly reports. |
| `CORS_EXTRA_ORIGINS` | the web address | Where the browser app is served from. |
| `LLM_API_KEY`, `LLM_MODEL_FAST`, `LLM_MODEL_STRONG` | optional | Without them every reply is authored text. |
| `ASK_ENABLED` | `false` until reviewed | Study Mode Ask. |

Start the API with `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` from `apps/api`
and the web app with `npm run start` from `apps/web`.

## 2. Check that it is ready

```bash
cd apps/api && python -m app.operator check
```

One line per check (database, migrations at head, content loaded, profile valid, draft content and
dev tools off in production, token pepper changed, email configured, rate limits on). Fix every
`FAIL` before families are invited. It exits 1 if anything failed, so it can sit in a deploy script.

## 3. Try it with demo families (not for production data)

On a throwaway database with `ALLOW_DRAFT_CONTENT=true` and `DEV_TOOLS=true`:

```bash
cd apps/api && python -m app.dev seed_scenarios
```

This creates six students in known states and a preview teacher with a class. Open `/dev` on the
web app to sign in as any of them, `/staff/login` for the guardian and teacher pages. See
`docs/UI_PREVIEW.md`. Never run it against the pilot database.

## 4. Enrol the pilot families

1. A guardian signs in at `/staff/login` with their email and the code that arrives, creates each
   child, and records consent (`tutoring` is required; `teacher_share`, `ai_processing`,
   `free_text` and `research_pseudonymised` are optional and only if the profile offers them).
2. The guardian sets a PIN for the child. The child signs in with the family code and the PIN.
3. For a school, an admin gives teachers and children a `site_id` and the teacher builds a class.
   A teacher sees only children whose guardian chose `teacher_share`.

## 5. Weekly jobs

Run these from cron or a scheduler (they are idempotent):

```bash
cd apps/api
python -m app.reports weekly            # the guardian report; once a week is enough, run it daily
python -m app.retention purge_guests    # delete idle guests (default 90 days)
```

The report waits for the profile's quiet hours to end, never sends a week twice, and sends nothing
for a week without practice.

## 6. When something goes wrong

* **Students cannot start a session, "paused":** a distress flag is open. The guardian sees it on
  their page and acknowledges it; otherwise it lifts by itself after 24 hours.
* **429 Too many requests:** the per-address limits in `config/limits.yaml`. Raise a limit there;
  `RATE_LIMIT_ENABLED=false` turns them off (do not, in production).
* **A 500 error:** the browser shows only "something went wrong" and a request id. Search the API
  log for that id.
* **Content is wrong:** edit the YAML, `python -m app.content validate`, then `load`. Approved
  content that you edit goes back to draft by itself until a teacher approves it again.
* **A family asks for their data or deletion:** the guardian page has both buttons; or an admin
  calls `GET /parents/{id}/export` and `DELETE /parents/{id}`.

## 7. Backups

Back up the `yourtutor` PostgreSQL database (`pg_dump`) and the `content/` folder. Everything a
student did is in the database; nothing else holds learner data. Test a restore before the pilot.
