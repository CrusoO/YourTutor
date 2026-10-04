"""Study assignment and comparison tokens. Pure helpers plus persistence."""

from __future__ import annotations

import random
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import expires_after, hash_code, new_token, now_utc
from app.config import settings
from app.db.models import (
    CheckpointFormRow,
    CheckpointResultRow,
    CheckpointTokenRow,
    ConsentRow,
    ItemRow,
    MasteryRow,
    PaperEntryRow,
    SessionRow,
    StudentRow,
    StudyParticipantRow,
)

COOKIE_NAME = "yt_cp"
REFERRER_POLICY = "no-referrer"
EXPORT_FIELDS = [
    "pseudonym",
    "group",
    "site",
    "form",
    "occasion",
    "score",
    "grade",
    "board",
    "diagnostic_baseline",
    "consent_version",
    "active_minutes",
    "active_days",
]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def assign_within_site(
    existing_pretests: list[str], *, seed: int, group: str
) -> tuple[str, str]:
    """Counterbalance pretest A/B within a site+arm. Posttest is the other form."""
    del group
    rng = random.Random(seed)
    a = existing_pretests.count("A")
    b = existing_pretests.count("B")
    if a < b:
        pretest = "A"
    elif b < a:
        pretest = "B"
    else:
        pretest = rng.choice(["A", "B"])
    return pretest, "B" if pretest == "A" else "A"


def assign_participant(
    session: Session,
    *,
    site_id: str,
    group: str,
    consent_id: uuid.UUID,
    student_id: uuid.UUID | None = None,
    assignment_method: str = "random",
    household_id: str | None = None,
) -> StudyParticipantRow:
    if group not in {"tutor", "comparison"}:
        raise HTTPException(status_code=400, detail="group must be tutor or comparison")
    consent = session.get(ConsentRow, consent_id)
    if consent is None or consent.revoked_at is not None:
        raise HTTPException(status_code=400, detail="consent_ref required")
    if household_id:
        prior = session.scalar(
            select(StudyParticipantRow).where(StudyParticipantRow.household_id == household_id)
        )
        if prior is not None:
            group = prior.group
    if group == "tutor" and student_id is None:
        raise HTTPException(status_code=400, detail="tutor arm requires student_id")
    existing = session.scalars(
        select(StudyParticipantRow.pretest_form).where(
            StudyParticipantRow.site_id == site_id,
            StudyParticipantRow.group == group,
        )
    ).all()
    seed = secrets.randbelow(2**31)
    pretest, posttest = assign_within_site(list(existing), seed=seed, group=group)
    row = StudyParticipantRow(
        id=uuid.uuid4(),
        student_id=student_id,
        site_id=site_id,
        household_id=household_id,
        pseudonymous_code=f"p_{uuid.uuid4().hex[:10]}",
        group=group,
        consent_id=consent_id,
        assigned_at=now_utc(),
        assignment_method=assignment_method,
        assignment_seed=str(seed),
        pretest_form=pretest,
        posttest_form=posttest,
    )
    session.add(row)
    session.flush()
    return row


def _occasion_for(participant: StudyParticipantRow, form: str) -> str:
    if form == participant.pretest_form:
        return "pretest"
    if form == participant.posttest_form:
        return "posttest"
    raise HTTPException(status_code=400, detail="token form must match assignment")


def _issue_one_token(
    session: Session,
    *,
    checkpoint_id: str,
    participant: StudyParticipantRow,
    form: str,
    occasion: str,
) -> str:
    token = new_token()
    session.add(
        CheckpointTokenRow(
            id=uuid.uuid4(),
            checkpoint_id=checkpoint_id,
            form=form,
            token_hash=hash_code(token),
            consent_id=participant.consent_id,
            participant_id=participant.id,
            expires_at=expires_after(settings.session_ttl_seconds),
            issued_at=now_utc(),
            occasion=occasion,
            used_at=None,
        )
    )
    return token


def issue_comparison_token(
    session: Session,
    *,
    checkpoint_id: str,
    participant_id: uuid.UUID,
    form: str | None = None,
) -> str:
    tokens = issue_comparison_tokens(
        session,
        checkpoint_id=checkpoint_id,
        participant_id=participant_id,
        form=form,
    )
    if form:
        return tokens["token"]
    return tokens["pretest"]["token"]


def issue_comparison_tokens(
    session: Session,
    *,
    checkpoint_id: str,
    participant_id: uuid.UUID,
    form: str | None = None,
) -> dict:
    participant = session.get(StudyParticipantRow, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="participant not found")
    if participant.group != "comparison":
        raise HTTPException(status_code=400, detail="tokens are for comparison group")
    if participant.consent_id is None:
        raise HTTPException(status_code=400, detail="consent_ref required")
    consent = session.get(ConsentRow, participant.consent_id)
    if consent is None or consent.revoked_at is not None:
        raise HTTPException(status_code=400, detail="consent required")
    if participant.posttest_form is None:
        raise HTTPException(status_code=400, detail="posttest form required")
    if form is not None:
        if form not in {"A", "B"}:
            raise HTTPException(status_code=400, detail="form must be A or B")
        occasion = _occasion_for(participant, form)
        token = _issue_one_token(
            session,
            checkpoint_id=checkpoint_id,
            participant=participant,
            form=form,
            occasion=occasion,
        )
        return {"token": token, "form": form, "occasion": occasion}
    pretest = _issue_one_token(
        session,
        checkpoint_id=checkpoint_id,
        participant=participant,
        form=participant.pretest_form,
        occasion="pretest",
    )
    posttest = _issue_one_token(
        session,
        checkpoint_id=checkpoint_id,
        participant=participant,
        form=participant.posttest_form,
        occasion="posttest",
    )
    return {
        "pretest": {"form": participant.pretest_form, "token": pretest, "occasion": "pretest"},
        "posttest": {"form": participant.posttest_form, "token": posttest, "occasion": "posttest"},
    }


def lookup_checkpoint_token(session: Session, raw: str) -> CheckpointTokenRow:
    row = session.scalar(
        select(CheckpointTokenRow).where(CheckpointTokenRow.token_hash == hash_code(raw))
    )
    if row is None or _as_utc(row.expires_at) < now_utc():
        raise HTTPException(status_code=401, detail="invalid token")
    return row


def consume_token(session: Session, row: CheckpointTokenRow) -> None:
    if row.used_at is not None:
        raise HTTPException(status_code=409, detail="token already used")
    row.used_at = now_utc()
    session.flush()


def persist_checkpoint_result(
    session: Session,
    *,
    checkpoint_id: str,
    form: str,
    score: dict,
    occasion: str,
    student_id: uuid.UUID | None = None,
    participant_id: uuid.UUID | None = None,
) -> CheckpointResultRow:
    row = CheckpointResultRow(
        id=uuid.uuid4(),
        student_id=student_id,
        participant_id=participant_id,
        checkpoint_id=checkpoint_id,
        form=form,
        score=float(score.get("score", 0)),
        per_skill=score.get("per_skill") or {},
        occasion=occasion,
        taken_at=now_utc(),
    )
    session.add(row)
    session.flush()
    return row


def form_payload(session: Session, checkpoint_id: str, form: str) -> dict:
    row = session.scalar(
        select(CheckpointFormRow).where(CheckpointFormRow.checkpoint_id == checkpoint_id)
    )
    ids: list[str] = []
    if row is not None:
        ids = list(row.form_a if form == "A" else row.form_b)
    items = []
    for item_id in ids:
        item = session.get(ItemRow, item_id)
        if item is None:
            continue
        stem = item.stem if isinstance(item.stem, dict) else {}
        items.append(
            {
                "id": item.id,
                "stem": stem.get("en", ""),
                "type": item.type,
                "options": [
                    {"id": opt.get("id"), "en": opt.get("en")}
                    for opt in (item.options or [])
                    if isinstance(opt, dict)
                ],
            }
        )
    html = _printable_html(checkpoint_id, form, items)
    return {
        "checkpoint_id": checkpoint_id,
        "form": form,
        "items": items,
        "html": html,
    }


def _printable_html(checkpoint_id: str, form: str, items: list[dict]) -> str:
    rows = []
    for index, item in enumerate(items, start=1):
        opts = "".join(f"<li>{opt.get('en') or opt.get('id')}</li>" for opt in item.get("options") or [])
        options = f"<ol type='a'>{opts}</ol>" if opts else "<p>Answer: ________</p>"
        rows.append(f"<section><h2>{index}. {item['stem']}</h2>{options}</section>")
    body = "\n".join(rows) or "<p>No items.</p>"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<meta name='referrer' content='no-referrer'>"
        f"<title>Checkpoint {checkpoint_id} form {form}</title>"
        "<style>body{font-family:sans-serif;max-width:40rem;margin:1rem auto;}"
        "h1,h2{font-weight:600} section{margin-bottom:1.5rem}</style></head>"
        f"<body><h1>Checkpoint {checkpoint_id} — Form {form}</h1>{body}</body></html>"
    )


def _student_for_participant(session: Session, part: StudyParticipantRow) -> StudentRow | None:
    if part.student_id:
        return session.get(StudentRow, part.student_id)
    if part.consent_id:
        consent = session.get(ConsentRow, part.consent_id)
        if consent is not None:
            return session.get(StudentRow, consent.student_id)
    return None


def _diagnostic_baseline(session: Session, student_id: uuid.UUID) -> str:
    rows = session.scalars(select(MasteryRow).where(MasteryRow.student_id == student_id)).all()
    if not rows:
        return ""
    mean = sum(row.p_known for row in rows) / len(rows)
    return f"{mean:.3f}"


def _tutor_activity(
    session: Session, student_id: uuid.UUID, pretest_at: datetime | None, posttest_at: datetime | None
) -> tuple[str, str]:
    if pretest_at is None or posttest_at is None:
        return "", ""
    start, end = _as_utc(pretest_at), _as_utc(posttest_at)
    if end < start:
        start, end = end, start
    sessions = session.scalars(
        select(SessionRow).where(SessionRow.student_id == student_id)
    ).all()
    minutes = 0
    days: set[str] = set()
    for row in sessions:
        stamp = _as_utc(row.last_active_at or row.started_at)
        if start <= stamp <= end:
            minutes += int(row.active_ms or 0)
            days.add(stamp.date().isoformat())
    return str(minutes // 60_000), str(len(days))


def analytics_csv_rows(session: Session) -> list[dict[str, str]]:
    from app.auth.consent import has_scope

    participants = session.scalars(select(StudyParticipantRow)).all()
    results = session.scalars(select(CheckpointResultRow)).all()
    by_part: dict[uuid.UUID, list[CheckpointResultRow]] = {}
    for result in results:
        if result.participant_id:
            by_part.setdefault(result.participant_id, []).append(result)
    rows = []
    for part in participants:
        if part.student_id and not has_scope(session, part.student_id, "research_pseudonymised"):
            continue
        if not part.student_id:
            consent = session.get(ConsentRow, part.consent_id) if part.consent_id else None
            if consent is None or not has_scope(session, consent.student_id, "research_pseudonymised"):
                continue
        student = _student_for_participant(session, part)
        consent = session.get(ConsentRow, part.consent_id) if part.consent_id else None
        grade = str(student.grade) if student is not None else ""
        board = student.board if student is not None else ""
        baseline = _diagnostic_baseline(session, student.id) if student is not None else ""
        consent_version = consent.version if consent is not None else ""
        taken = by_part.get(part.id) or []
        pretest_at = next((r.taken_at for r in taken if r.occasion == "pretest"), None)
        posttest_at = next((r.taken_at for r in taken if r.occasion == "posttest"), None)
        active_minutes, active_days = "", ""
        if part.group == "tutor" and student is not None:
            active_minutes, active_days = _tutor_activity(session, student.id, pretest_at, posttest_at)
        extras = {
            "grade": grade,
            "board": board,
            "diagnostic_baseline": baseline,
            "consent_version": consent_version,
            "active_minutes": active_minutes,
            "active_days": active_days,
        }
        if not taken:
            rows.append(
                {
                    "pseudonym": part.pseudonymous_code,
                    "group": part.group,
                    "site": part.site_id,
                    "form": part.pretest_form or "",
                    "occasion": "",
                    "score": "",
                    **extras,
                }
            )
            continue
        for result in taken:
            rows.append(
                {
                    "pseudonym": part.pseudonymous_code,
                    "group": part.group,
                    "site": part.site_id,
                    "form": result.form,
                    "occasion": result.occasion,
                    "score": f"{result.score:.3f}",
                    **extras,
                }
            )
    return rows


def score_submitted_answers(session: Session, answers: list[dict]) -> tuple[dict, list[dict]]:
    from app.checkpoint.score import score_answers
    from app.verifier.check import verify_response

    scored = []
    for answer in answers:
        item_id = answer.get("item_id")
        item = session.get(ItemRow, item_id) if item_id else None
        correct = False
        if item is not None:
            raw_answer = item.answer if isinstance(item.answer, dict) else {}
            correct = verify_response(
                answer.get("response") or "",
                answer_sympy=str(raw_answer.get("sympy", "")),
                accept=list(raw_answer.get("accept") or []),
                item_type=item.type,
                verify=item.verify,
                options=list(item.options or []),
            )
        scored.append(
            {
                "item_id": item_id,
                "skill_id": item.primary_skill if item is not None else "",
                "correct": correct,
            }
        )
    return score_answers(scored), scored


def enter_paper_answers(
    session: Session,
    *,
    pseudonym: str,
    form: str,
    occasion: str,
    answers: list[dict],
    entry_pass: int,
    checkpoint_id: str,
) -> dict:
    if entry_pass not in {1, 2}:
        raise HTTPException(status_code=400, detail="entry_pass must be 1 or 2")
    if form not in {"A", "B"}:
        raise HTTPException(status_code=400, detail="form must be A or B")
    participant = session.scalar(
        select(StudyParticipantRow).where(StudyParticipantRow.pseudonymous_code == pseudonym)
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="participant not found")
    mismatches: list[str] = []
    if entry_pass == 2:
        first = session.scalar(
            select(PaperEntryRow)
            .where(
                PaperEntryRow.participant_id == participant.id,
                PaperEntryRow.form == form,
                PaperEntryRow.occasion == occasion,
                PaperEntryRow.entry_pass == 1,
            )
            .order_by(PaperEntryRow.created_at.desc())
        )
        if first is None:
            raise HTTPException(status_code=400, detail="first entry required")
        first_map = {row.get("item_id"): row.get("response") for row in (first.answers or [])}
        second_map = {row.get("item_id"): row.get("response") for row in answers}
        keys = set(first_map) | set(second_map)
        mismatches = [
            key for key in sorted(keys) if first_map.get(key) != second_map.get(key)
        ]
    result = None
    if not mismatches:
        result, _ = score_submitted_answers(session, answers)
        persist_checkpoint_result(
            session,
            checkpoint_id=checkpoint_id,
            form=form,
            score=result,
            occasion=occasion,
            student_id=participant.student_id,
            participant_id=participant.id,
        )
    row = PaperEntryRow(
        id=uuid.uuid4(),
        participant_id=participant.id,
        checkpoint_id=checkpoint_id,
        form=form,
        occasion=occasion,
        entry_pass=entry_pass,
        answers=answers,
        mismatches=mismatches,
        score=None if result is None else float(result.get("score", 0)),
        created_at=now_utc(),
    )
    session.add(row)
    session.flush()
    return {
        "id": str(row.id),
        "pseudonym": pseudonym,
        "form": form,
        "occasion": occasion,
        "entry_pass": entry_pass,
        "mismatches": mismatches,
        "score": result,
    }


def paper_entry_html() -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='referrer' content='no-referrer'>"
        "<title>Paper checkpoint entry</title>"
        "<style>body{font-family:sans-serif;max-width:40rem;margin:1.5rem auto}"
        "label,textarea,input,select{display:block;width:100%;margin:.4rem 0}"
        "textarea{min-height:8rem}</style></head><body>"
        "<h1>Paper checkpoint entry</h1>"
        "<p>Admin only. Second pass flags mismatches. Scoring never writes mastery.</p>"
        "<form id='paper'>"
        "<label>Pseudonym <input name='pseudonym' required></label>"
        "<label>Checkpoint id <input name='checkpoint_id' value='CP.LIN1.CLASS9'></label>"
        "<label>Form <select name='form'><option>A</option><option>B</option></select></label>"
        "<label>Occasion <select name='occasion'><option>pretest</option>"
        "<option>posttest</option></select></label>"
        "<label>Entry pass <select name='entry_pass'><option value='1'>1</option>"
        "<option value='2'>2</option></select></label>"
        "<label>Answers JSON [{item_id, response}] <textarea name='answers'>[]</textarea></label>"
        "<button type='submit'>Save</button></form>"
        "<pre id='out'></pre>"
        "<script>document.getElementById('paper').addEventListener('submit',async(e)=>{"
        "e.preventDefault();const f=e.target;"
        "const body={pseudonym:f.pseudonym.value,checkpoint_id:f.checkpoint_id.value,"
        "form:f.form.value,occasion:f.occasion.value,entry_pass:Number(f.entry_pass.value),"
        "answers:JSON.parse(f.answers.value||'[]')};"
        "const r=await fetch('/admin/checkpoints/paper',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});"
        "document.getElementById('out').textContent=await r.text();});</script>"
        "</body></html>"
    )
