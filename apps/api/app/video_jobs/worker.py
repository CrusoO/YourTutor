"""Video-job worker: claims queued jobs and runs the engine subprocess."""

from __future__ import annotations

import json
import logging
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import VideoJobRow

logger = logging.getLogger("yourtutor.worker.vj")

# Configurable via monkeypatch in tests
_ENGINE_DIR: Path = Path(settings.engine_dir)
_TIMEOUT: int = settings.video_job_timeout_seconds
_POLL_SECONDS: float = 0.5
_CANCEL_CHECK_SECONDS: float = 4.0
_IDLE_SLEEP_SECONDS: float = 5.0


def _now() -> datetime:
    return datetime.now(tz=UTC)


@contextmanager
def _db(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Session context manager: commit on success, rollback on exception."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── crash recovery ────────────────────────────────────────────────────────────


def reset_running_jobs(factory: sessionmaker[Session]) -> int:
    """On worker startup: reset any stuck-running jobs back to queued."""
    with _db(factory) as db:
        rows = list(db.scalars(select(VideoJobRow).where(VideoJobRow.status == "running")))
        for row in rows:
            row.status = "queued"
            row.started_at = None
        return len(rows)


# ── claim ─────────────────────────────────────────────────────────────────────


def claim_one_job(factory: sessionmaker[Session]) -> uuid.UUID | None:
    """Claim one queued job using FOR UPDATE SKIP LOCKED; return its id or None."""
    with _db(factory) as db:
        row = db.scalars(
            select(VideoJobRow)
            .where(VideoJobRow.status == "queued")
            .with_for_update(skip_locked=True)
            .limit(1)
        ).first()
        if row is None:
            return None
        row.status = "running"
        row.started_at = _now()
        return row.id


# ── DB helpers ────────────────────────────────────────────────────────────────


def _push_events(
    factory: sessionmaker[Session],
    job_id: uuid.UUID,
    events: list[dict],
    stage: str | None,
) -> None:
    try:
        with _db(factory) as db:
            row = db.get(VideoJobRow, job_id)
            if row is None:
                return
            row.events = list(events)
            if stage is not None:
                row.stage = stage
    except Exception as exc:
        logger.warning("push_events failed for %s: %s", job_id, exc)


def _mark_done(
    factory: sessionmaker[Session],
    job_id: uuid.UUID,
    result_dir: Path,
    mp4_sha256: str | None,
    events: list[dict],
) -> None:
    with _db(factory) as db:
        row = db.get(VideoJobRow, job_id)
        if row is None:
            return
        row.status = "done"
        row.error_code = None
        row.result_path = str(result_dir)
        row.lesson_mp4_sha256 = mp4_sha256 or None
        row.sources_json_path = str(result_dir / "sources.json")
        row.qa_json_path = str(result_dir / "qa.json")
        row.events = list(events)
        row.completed_at = _now()


def _mark_failed(
    factory: sessionmaker[Session],
    job_id: uuid.UUID,
    error_code: str,
    events: list[dict],
) -> None:
    with _db(factory) as db:
        row = db.get(VideoJobRow, job_id)
        if row is None:
            return
        if row.status == "cancelled":
            return
        row.status = "failed"
        row.error_code = error_code
        row.events = list(events)
        row.completed_at = _now()


def _mark_cancelled(
    factory: sessionmaker[Session],
    job_id: uuid.UUID,
    events: list[dict],
) -> None:
    with _db(factory) as db:
        row = db.get(VideoJobRow, job_id)
        if row is None:
            return
        if row.status != "cancelled":
            row.status = "cancelled"
            row.error_code = "cancelled"
        row.events = list(events)
        row.completed_at = _now()


def _is_api_cancelled(factory: sessionmaker[Session], job_id: uuid.UUID) -> bool:
    with _db(factory) as db:
        row = db.get(VideoJobRow, job_id)
        return row is not None and row.status == "cancelled"


# ── subprocess helpers ────────────────────────────────────────────────────────


def _popen_engine(engine_dir: Path, request_file: Path) -> subprocess.Popen:  # type: ignore[type-arg]
    """Start the engine process. Extracted for monkeypatching in tests."""
    # On Windows, .cmd shims require shell=True; on POSIX, shell is unnecessary.
    return subprocess.Popen(
        ["pnpm", "video:job", str(request_file)],
        cwd=str(engine_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=(sys.platform == "win32"),
    )


def _wait_and_kill(proc: subprocess.Popen, timeout: float = 5.0) -> None:  # type: ignore[type-arg]
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait()
        except ProcessLookupError:
            pass


def _tail_new_lines(path: Path, pos: int) -> tuple[list[dict], int]:
    """Read new lines from events.jsonl since the last read position."""
    if not path.exists():
        return [], pos
    try:
        with path.open() as fh:
            fh.seek(pos)
            chunk = fh.read()
            new_pos = fh.tell()
    except OSError:
        return [], pos
    events = []
    for line in chunk.splitlines():
        stripped = line.strip()
        if stripped:
            try:
                events.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass
    return events, new_pos


def _handle_exit(
    factory: sessionmaker[Session],
    job_id: uuid.UUID,
    returncode: int,
    result_path: Path,
    all_events: list[dict],
) -> None:
    if returncode == 3:
        _mark_cancelled(factory, job_id, all_events)
        return

    result: dict = {}
    if result_path.exists():
        try:
            result = json.loads(result_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    if returncode == 0:
        files = {
            f.get("name", ""): f.get("sha256")
            for f in result.get("files", [])
            if isinstance(f, dict)
        }
        _mark_done(factory, job_id, result_path.parent, files.get("lesson.mp4"), all_events)
    else:
        code = (result.get("code") or "build_failed") if result else "build_failed"
        _mark_failed(factory, job_id, str(code), all_events)


# ── run one job ───────────────────────────────────────────────────────────────


def run_one_job(factory: sessionmaker[Session], job_id: uuid.UUID) -> None:
    with _db(factory) as db:
        row = db.get(VideoJobRow, job_id)
        if row is None:
            return
        request_data = dict(row.request_json)

    request_id: str = request_data.get("requestId") or str(job_id)
    engine_dir = _ENGINE_DIR.resolve()
    job_dir = engine_dir / "dist" / "jobs" / request_id
    events_path = job_dir / "events.jsonl"
    result_path = job_dir / "result.json"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, prefix="vj_") as tmp:
        json.dump(request_data, tmp)
        tmp_path = Path(tmp.name)

    try:
        proc = _popen_engine(engine_dir, tmp_path)
        deadline = time.monotonic() + _TIMEOUT
        last_cancel_check = time.monotonic()
        last_pos = 0
        all_events: list[dict] = []
        last_stage: str | None = None

        try:
            while True:
                time.sleep(_POLL_SECONDS)

                new_events, last_pos = _tail_new_lines(events_path, last_pos)
                if new_events:
                    all_events.extend(new_events)
                    for ev in reversed(new_events):
                        if ev.get("stage"):
                            last_stage = ev["stage"]
                            break
                    _push_events(factory, job_id, all_events, last_stage)

                ret = proc.poll()
                if ret is not None:
                    # Final drain before handling exit
                    extra, last_pos = _tail_new_lines(events_path, last_pos)
                    all_events.extend(extra)
                    _handle_exit(factory, job_id, ret, result_path, all_events)
                    return

                if time.monotonic() > deadline:
                    logger.warning("job %s timed out after %ds", job_id, _TIMEOUT)
                    proc.send_signal(signal.SIGTERM)
                    _wait_and_kill(proc)
                    _mark_failed(factory, job_id, "build_failed", all_events)
                    return

                if time.monotonic() - last_cancel_check > _CANCEL_CHECK_SECONDS:
                    last_cancel_check = time.monotonic()
                    if _is_api_cancelled(factory, job_id):
                        logger.info("job %s cancelled by API", job_id)
                        proc.send_signal(signal.SIGTERM)
                        _wait_and_kill(proc)
                        return  # router already set status=cancelled; leave it

        except BaseException:
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                pass
            raise

    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


# ── main loop ─────────────────────────────────────────────────────────────────


def main_loop(factory: sessionmaker[Session]) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    n = reset_running_jobs(factory)
    if n:
        logger.info("reset %d stuck running job(s) to queued", n)
    logger.info("video-job worker started (timeout=%ds, engine=%s)", _TIMEOUT, _ENGINE_DIR)
    while True:
        try:
            job_id = claim_one_job(factory)
            if job_id is None:
                time.sleep(_IDLE_SLEEP_SECONDS)
                continue
            logger.info("claimed job %s", job_id)
            run_one_job(factory, job_id)
            logger.info("finished job %s", job_id)
        except KeyboardInterrupt:
            logger.info("worker stopping (KeyboardInterrupt)")
            break
        except Exception:
            logger.exception("unhandled error in main loop")
            time.sleep(_IDLE_SLEEP_SECONDS)
