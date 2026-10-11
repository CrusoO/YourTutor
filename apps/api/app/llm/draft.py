"""`draft_content`: an authoring tool that asks the model for practice items from authored passages.

It is never a runtime path. Output is always `status: draft`, has no reviewer or hash, and carries
reviewer placeholders instead of translations (nothing is machine-translated). Each item must pass
the item schema, the machine solver (the stem must solve to the stated answer), the verifier (it
accepts its own answer) and the hint leak check. Items still go through `content validate` and
teacher approval before they are ever served. Refuses to run when APP_ENV is production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.config import settings
from app.content.leak import hint_leaks_answer
from app.content.schema import Item
from app.content.stem_solve import check_item_stem_answer
from app.llm.prompt import PROMPTS_DIR, Prompt
from app.llm.provider import Provider, ProviderError
from app.verifier.check import verify_response

NE = "<Nepali — to be filled by reviewer>"
AS = "<Assamese — to be filled by reviewer>"
VERSION = "draft_content/v1"
TEXT_FIELDS_ONE = ("stem", "prediction_prompt")


class DraftRefused(RuntimeError):
    pass


@dataclass
class DraftReport:
    written: list[Path] = field(default_factory=list)
    rejected: list[tuple[int, str]] = field(default_factory=list)  # (index in reply, reason)


def _loc(text: object) -> dict[str, str]:
    return {"en": str(text), "ne": NE, "as": AS}


def _slug(skill_id: str) -> str:
    return re.sub(r"[^A-Z0-9]+", ".", skill_id.upper()).strip(".")


def _next_ids(out_dir: Path, skill_id: str, how_many: int) -> list[str]:
    prefix = f"ITEM.DRAFT.{_slug(skill_id)}."
    taken = {p.stem for p in out_dir.glob("*.yaml")} if out_dir.is_dir() else set()
    ids: list[str] = []
    n = 1
    while len(ids) < how_many:
        candidate = f"{prefix}{n:04d}"
        if candidate not in taken:
            ids.append(candidate)
        n += 1
    return ids


def _build(raw: dict[str, Any], item_id: str, skill_id: str) -> dict[str, Any]:
    """The item dict, with everything the model must not decide forced to safe values."""
    answer = str(raw.get("answer", "")).strip()
    accept = [str(a) for a in raw.get("accept") or []] or [answer]
    return {
        "id": item_id,
        "skill_ids": [skill_id],
        "difficulty": raw.get("difficulty", 0.4),
        "type": raw.get("type", "expression"),
        "pool": "practice",
        "role": raw.get("role", "procedure"),
        "stem": _loc(raw.get("stem", "")),
        "answer": {"sympy": answer, "accept": accept},
        "solution_steps": [_loc(s) for s in raw.get("solution_steps") or []],
        "hints": [{"level": i + 1, **_loc(h)} for i, h in enumerate((raw.get("hints") or [])[:3])],
        "prediction_prompt": _loc(raw.get("prediction_prompt", "")),
        "misconception_rules": [],
        "reviewed_by": None,
        "status": "draft",
    }


def _problem(item: Item) -> str | None:
    """Why this item is not acceptable, or None."""
    if item.type.value not in {"expression", "numeric"}:
        return f"type {item.type.value} is not drafted yet"
    if not verify_response(
        item.answer.sympy, answer_sympy=item.answer.sympy, accept=item.answer.accept
    ):
        return "the verifier does not accept its own answer"
    solved = check_item_stem_answer(item)
    if solved not in (None, "manual", "teacher"):
        return f"answer mismatch: {solved}"
    for hint in item.hints:
        if hint.level <= 2 and hint_leaks_answer(hint.en, item.answer.sympy):
            return f"hint level {hint.level} leaks the answer"
    return None


def _prompt(skill_id: str, passages: str, count: int) -> Prompt:
    template = (PROMPTS_DIR / "draft_content" / "v1.md").read_text(encoding="utf-8")
    user = template.format_map({"skill_id": skill_id, "count": count, "passages": passages.strip()})
    return Prompt(system="You help a teacher draft practice items.", user=user, version=VERSION,
                  max_words=0)  # fmt: skip


def draft_items(
    *,
    skill_id: str,
    passages: str,
    count: int,
    provider: Provider,
    out_dir: Path,
    model: str | None = None,
) -> DraftReport:
    if settings.app_env.lower() == "production":
        raise DraftRefused("draft_content is an authoring tool and is disabled in production")
    report = DraftReport()
    try:
        reply = provider.complete(
            _prompt(skill_id, passages, count), model or settings.llm_model_strong
        )
    except ProviderError as exc:
        report.rejected.append((0, f"provider error: {exc}"))
        return report
    try:
        parsed = yaml.safe_load(reply.text)
    except yaml.YAMLError:
        parsed = None
    if not isinstance(parsed, list):
        report.rejected.append((0, "the reply was not a YAML list of items"))
        return report
    entries = [e for e in parsed if isinstance(e, dict)]
    ids = _next_ids(out_dir, skill_id, len(entries))
    for index, raw in enumerate(entries):
        data = _build(raw, ids[index], skill_id)
        try:
            item = Item.model_validate(data)
        except ValidationError as exc:
            report.rejected.append(
                (index, f"schema: {str(exc).splitlines()[0]} {exc.errors()[0]['msg']}")
            )
            continue
        problem = _problem(item)
        if problem:
            report.rejected.append((index, problem))
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{item.id}.yaml"
        if path.exists():
            report.rejected.append((index, f"{path.name} already exists"))
            continue
        dumped = item.model_dump(mode="json", by_alias=True, exclude_none=False)
        path.write_text(
            yaml.safe_dump(dumped, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        report.written.append(path)
    return report
