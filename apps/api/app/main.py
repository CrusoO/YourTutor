from fastapi import FastAPI

from app.auth.admin import router as admin_router
from app.auth.router import router as auth_router
from app.config import settings

app = FastAPI(title="YourTutor API", version="0.2.0")
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/ready")
def ready() -> dict[str, object]:
    return {
        "status": "ok",
        "allow_draft_content": settings.allow_draft_content,
    }
