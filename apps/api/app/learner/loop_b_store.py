"""The database store behind Loop B (`RecordStore`).

The compare-and-set is a real one: an UPDATE that only matches while the stored version is still the
one the job read, or an INSERT guarded by the primary key for a learner's first record. Either loser
simply gets False and the job re-reads and retries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import LoopBRecordRow, LoopBSnapshotRow
from app.learner.loop_b import LearnerRecord, Snapshot, TraitObservation


def _encode_record(record: LearnerRecord) -> dict[str, Any]:
    return {
        "processed": dict(record.processed),
        "mastery": dict(record.mastery),
        "observations": {
            trait: [
                {"session_id": o.session_id, "at": o.at.isoformat(), "x": o.x} for o in observations
            ]
            for trait, observations in record.observations.items()
        },
    }


def _decode_record(version: int, data: dict[str, Any]) -> LearnerRecord:
    return LearnerRecord(
        version=version,
        processed={str(k): int(v) for k, v in (data.get("processed") or {}).items()},
        mastery={str(k): float(v) for k, v in (data.get("mastery") or {}).items()},
        observations={
            trait: tuple(
                TraitObservation(
                    session_id=str(o["session_id"]),
                    at=datetime.fromisoformat(o["at"]),
                    x=float(o["x"]),
                )
                for o in rows
            )
            for trait, rows in (data.get("observations") or {}).items()
        },
    )


def _encode_snapshot(snapshot: Snapshot) -> dict[str, Any]:
    return {
        "mastery": dict(snapshot.mastery),
        "mastery_delta": dict(snapshot.mastery_delta),
        "traits": {
            name: {"mean": t.mean, "variance": t.variance, "n": t.n}
            for name, t in snapshot.traits.items()
        },
    }


class SqlRecordStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self, learner_id: str) -> LearnerRecord:
        row = self._session.get(LoopBRecordRow, uuid.UUID(learner_id))
        if row is None:
            return LearnerRecord()
        self._session.refresh(row)  # another writer may have moved it since this session read it
        return _decode_record(row.version, row.data or {})

    def compare_and_set(
        self, learner_id: str, expected_version: int, record: LearnerRecord, snapshot: Snapshot
    ) -> bool:
        student_id = uuid.UUID(learner_id)
        data = _encode_record(record)
        if expected_version == 0:
            if not self._insert_first(student_id, record, data, snapshot):
                return False
        else:
            result = self._session.execute(
                update(LoopBRecordRow)
                .where(
                    LoopBRecordRow.student_id == student_id,
                    LoopBRecordRow.version == expected_version,
                )
                .values(version=record.version, data=data, updated_at=snapshot.created_at)
            )
            if result.rowcount != 1:  # type: ignore[attr-defined]
                return False
        self._session.add(
            LoopBSnapshotRow(
                id=uuid.uuid4(),
                student_id=student_id,
                session_id=snapshot.session_id,
                watermark=snapshot.watermark,
                record_version=snapshot.record_version,
                versions={
                    "graph_version": snapshot.versions.graph_version,
                    "param_version": snapshot.versions.param_version,
                    "policy_version": snapshot.versions.policy_version,
                },
                payload=_encode_snapshot(snapshot),
                created_at=snapshot.created_at,
            )
        )
        self._session.flush()
        return True

    def _insert_first(
        self, student_id: uuid.UUID, record: LearnerRecord, data: dict[str, Any], snapshot: Snapshot
    ) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(
                    LoopBRecordRow(
                        student_id=student_id,
                        version=record.version,
                        data=data,
                        updated_at=snapshot.created_at,
                    )
                )
                self._session.flush()
        except IntegrityError:
            return False  # someone else wrote the first record; the job will re-read and retry
        return True
