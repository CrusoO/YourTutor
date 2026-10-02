from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="YourTutor API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/ready")
def ready() -> dict[str, object]:
    return {
        "status": "ok",
        "allow_draft_content": settings.allow_draft_content,
    }
