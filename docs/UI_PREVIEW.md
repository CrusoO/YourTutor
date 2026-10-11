# UI preview: see the app on your PC and your phone

Dev only. The preview uses its own database (`yourtutor_preview`) so it never touches your normal
dev data, and six ready-made students ("scenarios") so you can open any state in one click.

Commands below were run on Windows 11 with Docker Desktop. Run them from the repo root in
PowerShell unless it says otherwise. Do not paste Linux paths such as `/content` into Git Bash as
separate arguments (it rewrites them); the `sh -c "..."` form below avoids that.

## 1. One-time setup

```powershell
# a separate database for the preview
docker compose up -d postgres redis
docker compose exec postgres createdb -U tutor yourtutor_preview
docker compose exec postgres psql -U tutor -d yourtutor_preview -c "CREATE EXTENSION IF NOT EXISTS vector"
```

## 2. Start the stack on the preview database

```powershell
$env:POSTGRES_DB = "yourtutor_preview"
$env:DEV_TOOLS = "true"
$env:NEXT_PUBLIC_DEV_TOOLS = "true"
docker compose up -d --build api web
```

Then create the tables, load the content and seed the five scenarios (about a minute):

```powershell
docker compose exec api sh -c "alembic upgrade head && python -m app.content load /content && python -m app.dev seed_scenarios"
```

It prints the family code and PIN of each scenario. They are always the same:

| Scenario | Family code | PIN | What you see |
| --- | --- | --- | --- |
| new_student | DEVNEW | 1234 | First run: no history |
| mid_chapter | DEVMID | 1234 | Four skills done, the fifth started |
| skill_at_level_4 | DEVLV4 | 1234 | The first skill done |
| review_due | DEVRVW | 1234 | A review is overdue: the next session opens with a warm-up |
| all_skills_level_4 | DEVALL | 1234 | The whole chapter at level 4 |
| slip_prone | DEVSLP | 1234 | Every skill at level 4, so questions are application items: a wrong sign shows Check your work, Help opens the stuck-point picker |

To reset them (the app writes to them as you click around), press **Reset scenarios** on the
`/dev` page, or run the `seed_scenarios` command again.

## 3. On the PC

Open <http://localhost:3000/dev>, press **Log in as ...** next to a scenario. You land on Subjects as
that student (Maths, then Chapters, then the chapter's skill path; Today is still at `/today`). `/dev/lessons` lists every lesson; click one to play it without logging in.

`/dev` is a 404 unless `NEXT_PUBLIC_DEV_TOOLS=true`, and the API's `/dev/*` routes are a 404 unless
`DEV_TOOLS=true` and `ALLOW_DRAFT_CONTENT=true`. Never switch these on in production.

## 4. On a phone (same Wi-Fi)

1. Find the PC's address: `ipconfig` and read the **IPv4 Address** of your Wi-Fi adapter, for example
   `192.168.1.20`.
2. Restart the stack so the browser on the phone talks to the PC, not to itself:

   ```powershell
   $env:POSTGRES_DB = "yourtutor_preview"
   $env:DEV_TOOLS = "true"
   $env:NEXT_PUBLIC_DEV_TOOLS = "true"
   $env:NEXT_PUBLIC_API_URL = "http://192.168.1.20:8000"
   $env:CORS_EXTRA_ORIGINS = "http://192.168.1.20:3000"
   $env:NEXT_ALLOWED_DEV_ORIGINS = "192.168.1.20"
   docker compose up -d --build api web
   ```

   (`CORS_EXTRA_ORIGINS` lets the API accept the phone's page; `NEXT_ALLOWED_DEV_ORIGINS` lets the
   Next.js dev server serve it. Wildcards are refused.)
3. On the phone open `http://192.168.1.20:3000/dev`.
4. If it does not load, allow the two ports through the Windows firewall once, in an
   **administrator** PowerShell:

   ```powershell
   New-NetFirewallRule -DisplayName "YourTutor preview" -Direction Inbound -Protocol TCP -LocalPort 3000,8000 -Action Allow -Profile Private
   ```

   Remove it later with `Remove-NetFirewallRule -DisplayName "YourTutor preview"`.

The web dev server already listens on all interfaces (`npm run dev` uses `--hostname 0.0.0.0`) and
Docker publishes ports 3000 and 8000 on the PC, so no other setting is needed. Use a private
network, not public Wi-Fi.

## 5. Screenshots at phone size (Playwright)

`npm run test:ui` plays every scenario in a 360 px wide browser and saves screenshots to
`apps/web/test-results/screens/` (not in git). It re-seeds the scenarios first, so every run starts
from the same state.

First time only: `cd apps/web; npx playwright install chromium`. The API must be running with
`DEV_TOOLS=true`, `ALLOW_DRAFT_CONTENT=true` and the preview database. If another API already uses
port 8000, start one on another port and point the tests at it:

```powershell
cd apps/api
$env:POSTGRES_DB = "yourtutor_preview"; $env:ALLOW_DRAFT_CONTENT = "true"; $env:DEV_TOOLS = "true"
python -m uvicorn app.main:app --port 8001
# in a second window:
cd apps/web
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8001"
npm run test:ui -- --workers=1
```

`--workers=1` keeps it to one browser, which matters on a PC with little free memory.

## Troubleshooting

- **`/dev` shows "Could not load scenarios":** the API was started without `DEV_TOOLS=true`.
- **"Not seeded" under a scenario:** run the `seed_scenarios` command in step 2.
- **Log in fails on the phone:** `NEXT_PUBLIC_API_URL` must be the PC's address, not `localhost`, and
  the web container must be rebuilt/restarted after you change it.
- **Your normal dev data:** it lives in the `yourtutor` database and is not used here. To return to
  it, unset the variables above (`Remove-Item Env:POSTGRES_DB`, etc.) and `docker compose up -d`.


## Page-weight budget (lesson screen)

A lesson screen must stay under 200 KB over the wire (150 KB of script). Check it against a
production build, with the API allowing the production origin:

```powershell
cd apps/web; npm run build; npx next start -p 3002
$env:CORS_EXTRA_ORIGINS = "http://127.0.0.1:3002"   # before starting the API
$env:PLAYWRIGHT_NO_WEB = "true"; $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:3002"
npm run test:weight
```

Measured on 2026-10-10: 130 KB total, 118 KB of it script. Lighthouse itself is not used; this is the
same budget as a number that CI can check.
