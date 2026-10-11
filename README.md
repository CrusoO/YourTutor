# YourTutor

Pedagogy-first AI tutor for Class 9–10 maths (Bhutan + Assam SEBA). The **orchestrator decides what to do next; the LLM only phrases it.**

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

`.gitattributes` forces LF line endings so YAML, Python, and GitHub Actions do not pick up CRLF on Windows.

## Local checks (same as CI)

```bash
# API
cd apps/api
pip install -r requirements-dev.txt
ruff check .
mypy app
pytest

# Web
cd apps/web
npm install
npm run lint
npm test
```

`ALLOW_DRAFT_CONTENT=true` is for local/demo only. Production must leave it unset or false.

## Milestone status

**M0** scaffold and **M1** content pipeline are in this repo. Auth and sessions start at M2.

```
cd apps/api
python -m app.content.validate ../../content
```

Operator guide for a pilot: [docs/OPERATOR.md](docs/OPERATOR.md).
