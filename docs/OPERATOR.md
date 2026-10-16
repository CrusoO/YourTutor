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
| `JURISDICTION_PROFILE` | `default_strict` | Consent scopes, quiet hours, retention, report channels (`config/jurisdictions/`). |
| `PUBLIC_WEB_URL` | the guardian page address | The link in weekly reports. |
| `CORS_EXTRA_ORIGINS` | the web address | Where the browser app is served from. |
| `TRUSTED_PROXIES` | empty, or `127.0.0.1` behind a proxy on this machine | Addresses or CIDR ranges whose `X-Forwarded-For` header is believed. See section 8.1. |
| `LLM_API_KEY`, `LLM_MODEL_FAST`, `LLM_MODEL_STRONG` | optional | Without them every reply is authored text. |
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
python -m app.retention purge_guests         # delete idle guests

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
