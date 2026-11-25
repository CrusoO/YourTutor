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
python -m app.content load ../../content/            # sync registries, then load whatever content exists
cd ../web && npm install && npm run build
```

`content/` is the production content root and is a near-empty skeleton: the validate and load
commands succeed with `OK: 0 skills, 0 items`, and **production serves nothing until the content
factory stamps content** under `content/cbse/<class>/<subject>/`. Only the factory CLI writes
there. `validate` warns about every curriculum chapter whose overlay file does not exist yet. The
old Class 9 linear-equations draft pack is a test fixture in `apps/api/tests/fixtures/legacy_content/`
(draft, never for production); to try the app with it on a throwaway database use
`python -m app.content load tests/fixtures/legacy_content` with `ALLOW_DRAFT_CONTENT=true`. See
`content/README.md`.

Settings are environment variables (a `.env` file next to `apps/api` works; never commit it).
The API run on the host does not read the repository-root `.env` (the one `docker compose` uses). It needs
the database settings (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB`) set in `apps/api/.env` or in its environment, with the same password as the database;
the systemd example in 8.2 does this with `EnvironmentFile`. A password that differs from the
database's shows up as `FAIL database` in `python -m app.operator check` and as a `503` from `/ready`.
The ones that matter:

| Variable | Pilot value | What it does |
| --- | --- | --- |
| `APP_ENV` | `production` | Blocks authoring tools. |
| `ALLOW_DRAFT_CONTENT` | `false` | Only approved content is served. |
| `DEV_TOOLS` | `false` | Hides the preview pages and dev endpoints. |
| `POSTGRES_PASSWORD` | a long random string | Required. No default. Change it before any real data; production refuses `tutor`. Postgres reads it only on first start, so changing it later needs `ALTER USER` or a recreated volume (see 8.3). |
| `TOKEN_PEPPER` | a long random string | Hashes tokens and codes. Changing it signs everyone out. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `OTP_FROM_EMAIL` | your mail server | Sign-in codes and weekly reports. Without `SMTP_HOST` they only go to the log. |
| `SMS_PROVIDER`, `PHONE_SIGNIN_ENABLED`, `PHONE_DEFAULT_CALLING_CODE` | `console` / `false` / your country code | Phone sign-in. `SMS_PROVIDER=console` and `fake` send nothing (the code is never logged); `vendor` is a stub until the owner picks an SMS vendor and an adapter is written in `apps/api/app/auth/sms.py`. Production refuses `PHONE_SIGNIN_ENABLED=true` with console or fake. |
| `CHILD_PROFILES_ENABLED`, `ROLE_AGREEMENTS_REQUIRED`, `APPROVAL_TTL_SECONDS` | `false` / `false` / `604800` | A child's limited-mode profile with a guardian approval link (needs `PUBLIC_WEB_URL` set to the real site); make teacher routes refuse until the teacher terms are accepted; how long an approval link lives. |
| `JURISDICTION_PROFILE` | `default_strict` | Consent scopes, quiet hours, retention, report channels (`config/jurisdictions/`). |
| `PUBLIC_WEB_URL` | the guardian page address | The link in weekly reports. |
| `CORS_EXTRA_ORIGINS` | the web address | Where the browser app is served from. |
| `TRUSTED_PROXIES` | empty, or `127.0.0.1` behind a proxy on this machine | Addresses or CIDR ranges whose `X-Forwarded-For` header is believed. See section 8.1. |
| `ANTHROPIC_API_KEY`, `LLM_MODEL_FAST`, `LLM_MODEL_STRONG` | optional | Without them every reply is authored text. Models are named `anthropic/<model>`; production refuses any other name. |
| `ASK_ENABLED` | `false` until reviewed | Study Mode Ask. |

Start the API with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from `apps/api`
and the web app with `npm run start -- --hostname 127.0.0.1` from `apps/web`. Both listen on this
machine only; section 8 puts a proxy in front for the internet.

> Only for a private network with no proxy (a school LAN): use `--host 0.0.0.0` and
> `--hostname 0.0.0.0`, and keep the machine off the internet. Do this on a public machine and anyone
> can reach the API directly.

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
`docs/UI_PREVIEW.md`. Never run it against the pilot database. `npm run dev` in `apps/web` listens
on this machine only; to open the demo from a phone over Wi-Fi use `npm run dev:lan` instead (see
`docs/UI_PREVIEW.md` section 4), which listens on every network interface: never on a shared network.

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
python -m app.retention all --dry-run  # count what would go (nothing is deleted)
python -m app.retention all             # purge_guests, approvals (expired child profiles), otp, rate_events, auth_sessions, llm_calls, video_jobs, profile_counts (method/error profile rows older than 26 weeks; empty while LEARNER_PROFILE_ENABLED is off)
```

`all` prints one line of counts per job (no personal data) and exits 1 only if a job failed. The
periods are constants at the top of `apps/api/app/retention.py`; the guest window is
`guest_retention_days` in the jurisdiction profile. Video files are deleted only inside
`ENGINE_JOBS_DIR` (or `<ENGINE_DIR>/dist/jobs`). Run it daily from cron on the machine that sees that
folder, with the same `.env` as the API: `20 3 * * * cd /srv/yourtutor/apps/api && set -a && . /srv/yourtutor/.env && set +a && python -m app.retention all >> /var/log/yourtutor-retention.log 2>&1`.

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

## 8. Put it on the internet

Sections 1 to 7 get YourTutor running on one machine. This section makes it reachable over HTTPS
for families. What was run on a development machine is said where it is used; anything marked
"(not tested)", and every command not said to be run, was not. The public address is written `tutor.example.org` below; use your own.

### 8.1 HTTPS and the front door

The browser app calls the API directly, at the address baked in as `NEXT_PUBLIC_API_URL` when you run
`npm run build`. The API has no `/api` prefix of its own. The simplest public layout is one address
with the API under `/api`: the proxy removes the prefix before the request reaches the API. The web
app has one route of its own, `/api/health`, which the proxy must keep for the web app.

Set these, then rebuild the web app (the first value is fixed at build time):

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://tutor.example.org/api` (before `npm run build`) |
| `PUBLIC_WEB_URL` | `https://tutor.example.org` |
| `CORS_EXTRA_ORIGINS` | `https://tutor.example.org` |
| `TRUSTED_PROXIES` | `127.0.0.1` (the proxy's address as the API sees it; a CIDR range works too) |

**`TRUSTED_PROXIES` behind a proxy.** The API believes `X-Forwarded-For` only from an address in
this list. With the list empty (the default) the header is ignored and the connecting address is used.
The standard command in section 1 starts uvicorn, which by default already replaces the connecting
address with the visitor's when the proxy is on this machine (127.0.0.1); checked with a real uvicorn,
visitors then get their own limits even with the list empty. Set the list anyway, because it covers
what uvicorn's default does not: a proxy at another address (a Docker network, another machine) and a
uvicorn started with `--no-proxy-headers`. There, with the list empty, every visitor appears as the
proxy's address and everyone shares one rate limit: people start getting `429 too many requests`.
`python -m app.operator check` prints a `warn proxy addresses` line when the running API has seen
`X-Forwarded-For` from this machine while the list is empty (checked with `--no-proxy-headers`; with
the default uvicorn the address is already replaced, so no warning appears). Several proxies in a row
all go in the list; the API uses the first address, counting from the right, that is not in it.

**Migration note.** Before this setting existed the API believed the first address in the header from
anyone, so a visitor could send a made-up address and escape the rate limits. It no longer does. A
deployment behind a proxy that upgrades should add `TRUSTED_PROXIES=127.0.0.1` (or the proxy's range)
to `.env` and restart the API; until then it relies on uvicorn's default as described above, or
shares one limit if that does not apply. A deployment with no proxy needs nothing.

**Option A: a reverse proxy with automatic certificates (Caddy).** Needs a public address, a DNS
name that points to the machine, and ports 80 and 443 open. Save as `/etc/caddy/Caddyfile`:

```
tutor.example.org {
	encode gzip
	handle /api/health {
		reverse_proxy 127.0.0.1:3000
	}
	handle_path /api/* {
		reverse_proxy 127.0.0.1:8000
	}
	handle {
		reverse_proxy 127.0.0.1:3000
	}
}
```

```bash
caddy validate --config /etc/caddy/Caddyfile      # prints "Valid configuration"
sudo systemctl reload caddy                        # (not tested) when installed from the Caddy package
```

What was tested: `caddy validate` on this file (the `caddy:2` image, with the proxy targets written as
`host.docker.internal:…`), and the routing with a copy that listened on a local port with HTTPS off.
`/api/health` answered from the web app, `/api/ready` from the API, and `/` from the web app. The
certificate request needs a real DNS name and was not tested; Caddy gets and renews the
certificate by itself.

**Option B: a tunnel, for a machine with no public address (Cloudflare Tunnel).** All steps are
(not tested). The tunnel does not remove the `/api` prefix, so it points at a local Caddy that does.

1. Put the domain in a Cloudflare account. Install `cloudflared` on the machine.
2. `cloudflared tunnel login`, then `cloudflared tunnel create yourtutor`.
3. Run Caddy on a local port with HTTPS off. Use the Caddyfile above, but start it with
   `{ auto_https off }` as the first block and `:8081 {` in place of `tutor.example.org {`.
4. Save `~/.cloudflared/config.yml`, with the tunnel id and credentials file from step 2:

```
tunnel: yourtutor
credentials-file: /home/YOU/.cloudflared/<tunnel id>.json
ingress:
  - hostname: tutor.example.org
    service: http://127.0.0.1:8081
  - service: http_status:404
```

5. `cloudflared tunnel route dns yourtutor tutor.example.org`, then `cloudflared tunnel run yourtutor`.

Cloudflare provides the HTTPS. The three variables in the table are the same.

### 8.2 Keeping it running

Run the API and the web app as services that start after a reboot. Example with systemd (not tested;
paths and the user name are yours). The `.env` file holds the settings from section 1.

`/etc/systemd/system/yourtutor-api.service`:

```
[Unit]
Description=YourTutor API
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=yourtutor
WorkingDirectory=/srv/yourtutor/apps/api
EnvironmentFile=/srv/yourtutor/.env
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/yourtutor-web.service`: the same, with `WorkingDirectory=/srv/yourtutor/apps/web`
and `ExecStart=/usr/bin/npm run start -- --hostname 127.0.0.1`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now yourtutor-api yourtutor-web
```

Postgres and Redis start with `docker compose up -d postgres redis`. The compose file sets
`restart: unless-stopped` on both, so Docker brings them back after a reboot.

**Logs.** Under systemd both services write to the journal: `journalctl -u yourtutor-api -f` (not
tested). The API logs one line per request, `METHOD /path STATUS`, with no query string and no
address. Caddy logs to its own journal: `journalctl -u caddy`.

**Find a request id.** A 500 error shows the person "something went wrong" and a request id (12
letters and digits; the same id is in the `X-Request-Id` response header). The error is logged as
`unhandled error <id> on METHOD /path`, followed by the stack trace:

```bash
journalctl -u yourtutor-api --since "1 day ago" | grep -A 30 "unhandled error <id>"   # (not tested)
```

### 8.3 Closing the doors

1. Only the proxy is public: ports 80 and 443 (and 22 for you). Ports 8000, 3000, 5432 and 6379 must
   not be reachable from outside. The API and the web app above listen on `127.0.0.1`. Do not use
   `--host 0.0.0.0` from the private-network note in section 1 on a public machine. Set
   `TRUSTED_PROXIES` as in 8.1: the API believes `X-Forwarded-For` only from those addresses, so
   anyone who reaches port 8000 directly can no longer send a made-up address to escape the rate
   limits.
2. `docker-compose.yml` publishes every port on `127.0.0.1` only (Postgres 5432, Redis 6379, API 8000,
   web 3000) and restarts Postgres and Redis after a reboot. Only the rendered result of
   `docker compose config` was checked (every port showed `host_ip: 127.0.0.1`); running containers
   were not restarted, so run `docker compose up -d postgres redis` again after updating. The
   `web` service in that file runs `npm run dev` and is for development only: do not start it for a
   pilot. Run `npm run build` and `npm run start` as in 8.2, and start only `postgres` and `redis`
   from compose.
3. Set the database password. `docker compose` has no default for `POSTGRES_PASSWORD` and stops with
   "required variable POSTGRES_PASSWORD is missing" if it is unset; put a long random value in `.env`
   before the first `docker compose up`. The API reads the same variable, and with `APP_ENV=production`
   it refuses to start while the password is still the development value `tutor`.
   `python -m app.operator check` has a `database password changed` line for the same reason. A
   password changed after the first start also needs `ALTER USER` inside Postgres.
4. Close the ports in the machine's firewall too, for example
   `sudo ufw default deny incoming && sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`
   (not tested). Docker's published ports can bypass `ufw`, which is why the `127.0.0.1` bindings in step 2 matter.
5. `.env` holds secrets: `chmod 600 /srv/yourtutor/.env` and let only the service user own it.
   Keep it, and `TOKEN_PEPPER`, outside the repository (the repository's `.gitignore` already excludes
   `.env`). Keep a copy of `TOKEN_PEPPER` in your password manager: losing it signs everyone out.

### 8.4 Scheduled jobs and backups

Run them as the service user. Save the script as `/srv/yourtutor/ops/daily.sh`, make it executable,
and run it from `crontab -e` with `15 3 * * * /srv/yourtutor/ops/daily.sh` (the script and cron are
not tested; `app.operator check` and the dump and restore were run by hand, with `docker exec` on the
Postgres container in place of `docker compose exec`; `app.reports` and `app.retention` were not run).

```bash
#!/usr/bin/env bash
set -u
cd /srv/yourtutor/apps/api
set -a; . /srv/yourtutor/.env; set +a

python -m app.reports weekly                 # the guardian report, safe to run every day
python -m app.retention all                  # retention: guests, sign-in codes, old rows, videos

if ! python -m app.operator check > /tmp/operator-check.txt 2>&1; then
  mail -s "YourTutor check FAILED" you@example.org < /tmp/operator-check.txt   # (not tested)
fi

# backup, 14 days kept
mkdir -p /srv/yourtutor/backups
docker compose -f /srv/yourtutor/docker-compose.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "/srv/yourtutor/backups/yourtutor-$(date +%F).sql.gz"
find /srv/yourtutor/backups -name 'yourtutor-*.sql.gz' -mtime +14 -delete
```

`python -m app.operator check` exits 1 when any line says `FAIL` (checked on a development
database: 7 of 8 checks passed and the exit code was 1). The `mail` line needs a mail program on the
machine; any command that sends you a message works in its place.

**Restore test, once before the pilot.** Restore into a spare database, never over the real one.
This was done on a development database: the dump was valid gzip, restored with no errors, and the
restored copy had 23 tables.

```bash
cd /srv/yourtutor
docker compose exec -T postgres createdb -U "$POSTGRES_USER" restore_test
gunzip -c backups/yourtutor-$(date +%F).sql.gz | docker compose exec -T postgres \
  psql -U "$POSTGRES_USER" -q -v ON_ERROR_STOP=1 restore_test
docker compose exec -T postgres psql -U "$POSTGRES_USER" -At restore_test \
  -c "select count(*) from information_schema.tables where table_schema='public'"
docker compose exec -T postgres dropdb -U "$POSTGRES_USER" restore_test
```

Copy the `backups/` folder to another machine or storage as well; a backup on the same disk does
not survive that disk failing.

### 8.5 Watching it

1. Set up an uptime check (any free service, or `cron` on another machine) that fetches
   `https://tutor.example.org/api/ready` every minute and alerts you by email or phone after two
   misses. The API answers `200` with `"database": "ok"` when it can reach Postgres (`select 1`, two
   seconds at most) and `503` with `{"status": "unavailable", "database": "down"}` when it cannot, for
   example after a wrong database password or with Postgres stopped. The body never holds connection
   details; the cause is in the API log. `"redis"` is reported as `ok` or `down` but never fails the
   check, because nothing in the app uses Redis yet. `/health` on the API is a separate liveness
   answer (the process is up) and is used by the compose healthcheck; it does not look at the database.
   Optionally also fetch `https://tutor.example.org/api/health`, which the proxy sends to the web app.
2. When it is down, in this order:
   1. Open the public address in a browser on a phone's mobile data, to rule out your own network.
   2. On the machine: `systemctl status yourtutor-api yourtutor-web caddy` (not tested), and
      `docker compose ps` for Postgres and Redis.
   3. `curl -s http://127.0.0.1:8000/ready` and `curl -s http://127.0.0.1:3000/api/health`. If
      these answer but the public address does not, the problem is the proxy or tunnel: read its log.
      A `503` from `/ready` means the API is up but cannot reach Postgres: check `docker compose ps`
      and the database password (8.3).
   4. If a service is down, read the last 50 lines of its journal, then
      `sudo systemctl restart <name>`. Run `python -m app.operator check` before telling families
      it is back.
   5. If Postgres lost its data or will not start, restore the latest file in `backups/` as in
      8.4, into the real database name only after you have stopped the API.

## 9. The content factory (verified questions)

Run from `apps/api`. Nothing here calls a model or a paid service. Design: `docs/adr/0004-content-factory-kernel.md`.
All commands take `--root <content folder>` (default: the repo's `content/`) before the command name.

| Command | What it does |
| --- | --- |
| `python -m app.factory certify TEMPLATE.yaml --reference-index FILE` | Runs every tuple of the template's parameter box through the full checker stack and, with zero failures, writes `factory/certificates/<id>.json` and a ledger entry. Use `--no-reference-index` only to say plainly that originality compares against nothing. Exit 1 means not certified; the failing tuples are printed. |
| `python -m app.factory stamp TEMPLATE.yaml --count N` | The only writer of tier A. Needs a current certificate for the same template hash. Writes stamped draft items to `items/factory/<lane>/` with a `verification` record and logs each stamp. |
| `python -m app.factory audit-sample --rate 0.02 [--exposure FILE]` | Lists a uniform random and a PPS sample of stamped items for a human to check (the exposure file is `{item_id: times shown}`). |
| `python -m app.factory report` | Stamped items per chapter and pass, fail, skip counts per checker. |
| `python -m app.factory ledger-verify` | Checks the hash chain of `factory/ledger.jsonl`. Run it in CI; any edit to an earlier line is reported. |
| `python -m app.factory suspend ITEM_ID --reason "..." [--undo]` | Switches an item off (or back on) in the database and the ledger. A suspended item is never served. |
| `python -m app.factory variants --source TEMPLATES_DIR [--kind diagnostic explain checkpoint] [--count N]` | Derives, certifies and stamps variants of one template per skill (resumable). `diagnostic` fills the diagnostic pool (probe warm-up), `explain` is role explain framed as "a classmate says X, choose the correct answer" (calculation-checked; it does not check a reason), `checkpoint` fills the checkpoint pool. Variant boxes are shrunk (at most 120 tuples) so each certifies in seconds. |
| `python -m app.factory forms` | Builds the matched A/B checkpoint forms of each chapter from stamped checkpoint items (same skill, difficulty within 0.1; at least 10 pairs or no form). Writes `checkpoints/<id>.yaml`. |

Then `python -m app.content load content/` as usual. A hand-written `tier: A` is ignored with a warning
unless an intact record in the ledger backs it. Stamped items are served only when the owner sets
`SERVE_TIER_A_UNREVIEWED=true` in the production environment (the code default stays off) and the item is original.
A tampered ledger makes `content validate` and `content load` fail. Migration `0035` adds the item columns
(`alembic upgrade head`, safe to run twice).

### 9.1 Where factory content lives and how it is read

Each lane owns one folder, `content/<board>/<class>/<subject>/` (for example `content/cbse/10/physics/`),
holding `skills/`, `misconceptions/`, `overlays/`, `items/factory/<lane>/` and its own `factory/`
(ledger, certificates, `factory/templates/*.yaml`). Run the factory commands with
`--root content/cbse/10/physics`. `python -m app.content validate content/` and `load content/` read the root
itself and every such subject folder; a root with no subject folders behaves as before.

- Items stamped by the factory (a verification record and a `factory-N` generator) are not checked
  against legacy item templates and are not queued for a teacher's stem check: the certificate is the
  check. A hand-edited stamped item loses that treatment and its tier.
- `factory-template/1` files have no schema in the content package. `validate` skips them with a
  warning; `python -m app.factory certify` is what checks a template.
- Every intact ledger under the root counts. A broken ledger is an error that names its folder.
- Stamped types: multiple choice (distractor procedures become `misconception_rules`, so each
  procedure must be a misconception id in the bank), numeric and expression (the lane supplies
  `item_type`, `answer_text`, optional `accept`, `verify` and `wrong_answers`).
- From generator `factory-2` the content hash covers option text and the item type. Items stamped
  under `factory-1` (the first physics pass) keep their old hash and `validate` warns to re-stamp them.

### 9.2 When is a stamped item served?

All of these must hold (the gate is `app/content/gate.py`; nothing here changes a default):

1. The item is loaded with an intact, ledger-listed record naming its current content (a stored row
   is re-hashed when read, so an edit in the database also removes the tier).
2. `SERVE_TIER_A_UNREVIEWED=true` (default false) and the item is original; or `ALLOW_DRAFT_CONTENT=true`
   in development.
3. The item is not suspended (`python -m app.factory suspend`); suspension beats every other switch.
4. The student's chapter is live. Either the overlay says `live: true` (the validator refuses that
   until approved counts hold), or, with `SERVE_TIER_A_UNREVIEWED=true`, every skill of the chapter
   has at least 5 practice items that the gate serves on their tier (a skill with no diagnostic item is simply skipped by the probe)
   (`gate.overlay_is_live_for_serving`). The overlay file stays `live: false`; nothing is flipped
   quietly. A missing role (explain, apply, transfer) lowers quality, not safety: the policy falls
   back and logs a content gap. `validate` says so: "not live by approval, but every skill is
   covered by calculation-checked items".

Lessons: a lesson that carries a `generated` block (worked-example lesson built from stamped
solution traces, wording template reviewed once by a person, no hand-built widget) is servable
under the same switch while every trace item stays backed by its stamp (`app/lessons/generated.py`).
Every other draft lesson still needs `status: approved`. No lesson uses this yet: the generator and
the one-time wording review are not built.

Other surfaces (offline packs, mistake list, ask search) use the status rule only: a draft stamped
item never appears there. The label learners see stays `Answer checked by calculation`; the factory
cannot emit `human-reviewed` or `teacher-approved`.

## 10. Reviewer-only launch on Vercel

This is for putting only the reviewer desk on Vercel (`vercel.json` at the repo root: service `api` =
`apps/api`, service `web` = `apps/web`). Checked against the code and Vercel's documentation on
2026-11-24; nothing here was deployed.

Settings, by name only (never write values into the repo):

- Database: the `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` settings (a hosted Postgres such as Neon; the API refuses the default dev password in production).
- Sign-in codes: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`. Without SMTP nobody can sign in.
- Reviewer desk: `REVIEWER_DESK_ENABLED=true` on the API, `NEXT_PUBLIC_REVIEWER_DESK=true` on the web build; optional `REVIEWER_ALLOWLIST`, `REVIEWER_DAILY_CAP_SECONDS`, `REVIEW_RATE_PER_DECISION_INR`, `REVIEW_MONTHLY_CAP_INR`.
- Keep `ALLOW_DRAFT_CONTENT` and `SERVE_TIER_A_UNREVIEWED` false: the review routes read drafts directly and need neither.
- `REVIEW_SNAPSHOT_ENABLED` (default true) and `REVIEW_SNAPSHOT_PATH` (default: the committed file) only need setting to turn the snapshot off or move it.

Plan: Vercel's Hobby plan is for personal, non-commercial use (Vercel's terms; not re-checked word for word here). Paying reviewers is commercial, so plan on Pro. Documented limits (Fluid compute): maximum duration 300 s on Hobby, 300 s default and up to 800 s on Pro; Python bundle 500 MB uncompressed; 2 GB memory by default.

Cold start. The review routes used to parse about 2,300 YAML files (13 MB) in the request: about 14 to 19 s on the development machine, per cold function instance (the per-process cache only helps a warm one). The API service root is `apps/api`, while `content/` and `config/` are at the repo root, outside it. Vercel documents that Python functions "include all files from your project that are reachable at build time", but nothing I could find says whether files outside a service `root` are copied into that service's build, and services are described as "built separately". So the YAML may be absent in the deployed function.

What the snapshot does: `app/content_review/review_snapshot.json.gz` (0.4 MB, inside `apps/api`) holds the validated items, misconception titles, Hindi strings and the chapter map. Measured here: reading it takes about 0.1 s and validating the items about 0.2 s (0.3 s with no YAML present), against about 14 s from YAML; with the YAML present, checking that the snapshot still matches takes about 0.7 s once per process. Content hashes are identical either way (tested for every item). Rule: with the desk on, use the snapshot when the content folder is absent, or when its signature matches the one recorded in the snapshot; otherwise parse the YAML. After any change under `content/` (items, misconceptions, overlays, curriculum) run `cd apps/api && PYTHONPATH=. python scripts/write_review_snapshot.py` and commit the file; a test fails when it is stale. If the YAML is absent the snapshot is the only truth, so a stale snapshot would be served: regenerate before every deploy that follows a content change.

Not proven, so the owner must check on a preview deployment: (1) whether `content/` reaches the API function (not needed for the review routes now, but other routes, and `apply-reviews` expect it); (2) the real cold-start time and memory of the API function; (3) the duration limit actually applied to the `api` service (a `maxDuration` per service is a deploy setting, not changed here); (4) whether `apply-reviews`, which writes YAML, can run on Vercel at all (it needs the YAML and a writable repo, which a function is unlikely to have; not verified), so plan to run it on a development machine against the database. The recommended change, for the owner to decide, is to keep `vercel.json` as it is, deploy a preview with the desk on, and open `/staff/review/chapters` as an admin: a fast answer with the snapshot in place proves the path.

## 11. Free reviewer pilot (three invited teachers, no email service)

For checking questions with three outside teachers and no learners. It needs no email service and
no domain: the admin hands each reviewer a one-time sign-in code, for example on WhatsApp.

**Set by name** (values in the host's secret settings, never in git):

- Database: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. The
  API has no single database URL setting; it builds the address from these five. Not tested against
  Neon: the driver asks for an encrypted connection when the server offers one, which Neon does.
- `TOKEN_PEPPER` (long random), `APP_ENV=production`, `CORS_EXTRA_ORIGINS` (the web address).
- API: `REVIEWER_DESK_ENABLED=true`. Web, set before `npm run build`: `NEXT_PUBLIC_REVIEWER_DESK=true`
  and `NEXT_PUBLIC_API_URL`.
- Keep `ALLOW_DRAFT_CONTENT=false` and `SERVE_TIER_A_UNREVIEWED=false`. Reviewers see draft questions
  on the review screen without either switch, and no learner is served a draft.
- `REVIEWER_SIGNIN_CODE_TTL_SECONDS` (default `900`, 15 minutes): how long a code lives.
- Leave the `SMTP_*` settings out. Section 10 says nobody can sign in without them; with admin-issued
  codes that no longer holds for reviewers.

**Free stack.** Neon free Postgres for the database; the free Vercel plan for the web app; the API as in
section 10, or on any host that runs Python. The free Vercel Hobby plan is for non-commercial use: that fits
three invited teachers and no learners. Move to Pro or another host before paying people or opening
the site wider.

**First admin (one-time command).** Nothing in the web app makes the first admin, so run this once
from `apps/api`, with the database settings above, after `python -m alembic upgrade head`:

    python -m app.auth.bootstrap admin-code you@example.org

It creates the admin account and prints a code (works once, 15 minutes; run it again for a new one).
It refuses an address that already belongs to another kind of account. Sign in at `/staff/login`:
type the email, press "I already have a code from the admin", enter the code. Do not press "Send
code": with no email service that fails.

**Invite a reviewer and give them a code.**

1. As admin open `/staff/review/reviewers`. Type the reviewer's email, press Invite.
2. Press "Create sign-in code" on their row. The code shows once, with a Copy button. Send it to them
   (WhatsApp is fine). It works once and expires in 15 minutes. A new code replaces an unused one; at
   most 5 per reviewer per hour. A suspended reviewer cannot be given a code.
3. The reviewer opens `/staff/login`, types their email, presses "I already have a code from the
   admin", enters the code and lands on `/staff/review`. To sign in again later they need a new code.
4. The reviewers page lists only accounts handled in the current visit. To get a row for someone
   invited earlier, Invite the same email again (it changes nothing else).

The database keeps who issued a code for whom and when (table `reviewer_code_issues`), never the code.

**First week, three teachers.**

- Day 1: run `python -m app.operator check`; sign in as admin; invite the three; send each a code;
  confirm each reaches the review screen (ask them to reply "in").
- Day 1 to 2: each does five questions; check the admin export (`GET /staff/review/export`) shows their
  counts and time.
- Through the week: send a fresh code whenever someone is signed out (a reviewer's session lasts 7 days, set by
  `REVIEWER_SESSION_TTL_SECONDS`; every other role's lasts 24 hours); suspend
  anyone who should stop; read the notes they leave.
- End of week: run `python -m app.content apply-reviews` and look at what two reviewers
  approved before anything is set to approved.

**Not covered yet:** the reviewer agreement and its acceptance, a quality multiplier on pay, and
a way to turn an approved question type into approved content for students (see section 12).

## 12. Template-level approval (records only)

Needs `REVIEWER_DESK_ENABLED=true` and `REVIEW_TEMPLATE_APPROVAL_ENABLED=true` (default false). With
it off, everything works as in section 11: each question is approved one by one by two reviewers.

**What it does.** The factory makes many questions from one template. A reviewer approves a template
by approving a few sample questions from it. The sample set is the same for every reviewer: the
questions of one template version sorted by difficulty then id, the easiest, the middle and the
hardest (all of them when there are fewer than three). A template version is the template id, its
hash and the generator version; any change to those is a new version and starts again, even if a
sample's text is identical. Each decision stores a `template_key` (sha256 of
"template_id|template_hash|generator_version", set by the server, column added by migration 0041;
NULL for items with no template and for older rows). A reviewer has approved a template when their
standing decision on every sample, at its current content hash and the version's current key, is
approve. Decisions with another or no key still count as ordinary item decisions, and an old
version's fix or reject does not block the new version. Run migrations before switching it on. A withdrawn decision does not count and a skip does not count. About
3 sample decisions per template are paid at the usual rate (section 11); pay is unchanged.

**How many reviewers.** `REVIEW_TEMPLATE_APPROVALS_REQUIRED` (default 1). Two are required for a
template id that starts with one of `REVIEW_TEMPLATE_DOUBLE_REVIEW_PREFIXES` (default
`TPL2.PHY,TPL2.CHEM,TPL2.BIO,TPL2.HEALTH`: laws and facts), and for `REVIEW_TEMPLATE_DOUBLE_REVIEW_PERCENT`
(default 15) per cent of the other templates, picked by `int(sha256(template_hash)[:8], 16) % 100`,
so the same template always gets the same answer. The two reviewers do not see each other's votes.

**Block and escalate.** A fix or reject on a sample by anyone blocks the template. All its questions
then enter every reviewer's todo list for one-by-one review (state `escalated`; `blocked` when the
samples are all its questions) until the template changes. Reviewers see only their own progress.

**What the admin sees.** `GET /staff/review/templates/summary` (counts by state in total and per
chapter, plus the blocked and escalated templates) and `GET /staff/review/templates/{template_id}`
(samples and each reviewer's progress by pseudonymous label). The admin page also shows the counts.
States: in_review, ready (enough reviewers approved all samples, nothing blocking), blocked, escalated.

**What it does not do.** It changes nothing a student is served, no item `status`, and not
`apply-reviews`. A `ready` template is a record only. Turning ready templates into approved content
(and using the label "Question type reviewed by a teacher") is a later step for the owner to review
after the first pilot results.

## 13. Reviewer terms (draft)

With `REVIEWER_DESK_ENABLED` on, an invited reviewer must accept the reviewer terms before any
review route works. They are signed in, shown the terms on the agreement page, and tick one box.
What is kept: who, which version and when (the `agreement_acceptances` table).

- **Where to edit the text.** `apps/web/lib/agreement-copy.ts`, the `reviewerTerms` list. The
  text is a DRAFT: a lawyer should read it before real reviewers are paid. `[contact]` in it is
  replaced by the setting below.
- **How a new version forces re-acceptance.** After editing the text, change `REVIEWER_VERSION`
  in `apps/api/app/auth/agreements.py` (for example to `reviewer-terms-v2`) and deploy. From then
  every reviewer gets 403 `terms_not_accepted` until they accept again; teachers and admins are
  not asked. The admin reviewers page shows "Terms accepted" or "Terms not yet accepted" for each.
- **Setting.** `REVIEWER_TERMS_CONTACT`: who a reviewer asks to see, correct or delete their
  details. The default is "the Brownie team"; set a real contact before inviting reviewers.
