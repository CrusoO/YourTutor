# YourTutor

Pedagogy-first AI tutor for CBSE Class 10 maths (Board Sprint, algebra first). The **orchestrator decides what to do next; the LLM only phrases it.**

See [PLAN.md](PLAN.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Windows: Docker Desktop + WSL2

Work **inside the WSL filesystem**, not `/mnt/c`. Bind mounts from the Windows drive are slow and break file watchers.

1. Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) and enable the **WSL2** backend.
2. Install Ubuntu from the Microsoft Store. Open that distro (not PowerShell) for daily work.
3. Clone this repo in WSL, for example `~/src/YourTutor`.
4. Copy env and start the stack:

```bash
cp .env.example .env
docker compose up --build
```

5. Check health:

- API: http://localhost:8000/health
- Web: http://localhost:3000/api/health
- Web UI: http://localhost:3000

The web image is a production build served with `next start`. `NEXT_PUBLIC_*` values are compiled into the browser bundle, so they are build arguments in `docker-compose.yml`: change one and rebuild the image (`docker compose build web`).

`.gitattributes` forces LF line endings so YAML, Python, and GitHub Actions do not pick up CRLF on Windows.

## Local checks (same as CI)

```bash
# API (CI installs the pinned requirements-dev.lock: Linux, Python 3.12)
cd apps/api
pip install -r requirements-dev.lock   # on Windows or macOS use requirements-dev.txt
ruff check .
mypy .
pytest

# Web
cd apps/web
npm install
npm run lint          # tsc --noEmit
npm test              # vitest
npm run build
npm run check:weight  # page-weight budget (home JS 128 KB, CSS 25 KB, page 150 KB, gzip)
```

To refresh the API lock files, see [apps/api/README.md](apps/api/README.md).

## Model calls

The tutor chat and the lessons call Claude through the official Anthropic SDK (`apps/api/app/llm/anthropic_client.py`, key `ANTHROPIC_API_KEY`). Groq, Gemini and OpenRouter keep a plain HTTP path (`app/explain/service.py`, `service_chat.py`). The chat withholds a practice item's answer (`app/explain/answer_guard.py`) and can stream (`POST /explain/chat/stream`). With no key, replies are authored text.

`ALLOW_DRAFT_CONTENT=true` is for local/demo only. Production must leave it unset or false.

## Status

Versions, targets and gates are in [docs/ROADMAP.md](docs/ROADMAP.md); what has merged is in [CHANGELOG.md](CHANGELOG.md). Features kept behind flags are in [docs/parked.md](docs/parked.md).

Validate the content:

```
cd apps/api
python -m app.content.validate ../../content
```

Operator guide for a pilot: [docs/OPERATOR.md](docs/OPERATOR.md).
