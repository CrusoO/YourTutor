"""Delete a video job's output folder, and only ever a folder directly inside the jobs directory.

The path stored on a job row is data, not trust: it can be a Windows path written by the host
worker, or be wrong. Only its last component is used, it must look like a job id, the folder must
sit directly under the configured jobs directory, and a symbolic link is never followed.
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path, PureWindowsPath

from app.config import settings

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def jobs_dir() -> Path:
    """Where the engine writes job folders (ENGINE_JOBS_DIR in Docker, else <engine>/dist/jobs)."""
    if settings.engine_jobs_dir:
        return Path(settings.engine_jobs_dir)
    return Path(settings.engine_dir) / "dist" / "jobs"


def job_folder_name(job_id: uuid.UUID, result_path: str | None, request_json: dict | None) -> str:
    """The folder name a job's files live under (the last part of its result path, if any)."""
    if result_path:
        return PureWindowsPath(result_path).name
    request_id = (request_json or {}).get("requestId")
    return str(request_id) if request_id else str(job_id)


def delete_job_folder(name: str, root: Path | None = None) -> bool:
    """Remove `<jobs dir>/<name>`. True if removed; False if absent or not safe to remove."""
    if not _SAFE_NAME.match(name):
        return False
    base = (root if root is not None else jobs_dir()).resolve()
    target = base / name
    if target.is_symlink() or not target.is_dir():
        return False
    if target.resolve().parent != base:
        return False
    shutil.rmtree(target, ignore_errors=True)
    return True
