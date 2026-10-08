"""Deterministic template instantiation. Answers via the allowlist parser."""

from __future__ import annotations

import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from app.content.diagnosis_fields import draft_fields
from app.content.language import lint_item_texts
from app.content.leak import hint_leaks_answer
from app.content.math_parse import ParseError, parse_math
from app.content.schema import Item, ItemTemplate
from app.content.signatures import has_one_x
from app.content.stem_solve import check_item_stem_answer
from app.content.templates import GENERATOR_VERSION, load_templates, template_hash, write_template
from app.content.validator import item_tier, last_step_matches_answer, load_bundle, validate_bundle

NE = "<Nepali — to be filled by reviewer>"
AS = "<Assamese — to be filled by reviewer>"


def loc(en: str) -> dict[str, str]:
    return {"en": en, "ne": NE, "as": AS}


_IDENT = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
PRACTICE_PER_SKILL = 20
MIN_PER_TIER = 5
TIER_TARGETS = {"easy": 7, "medium": 7, "hard": 6}


_LABELS = frozenset({"yes", "no", "every", "none", "one"})


def eval_formula(expr: str, params: dict[str, Any]) -> Any:
    if expr.strip() in _LABELS:
        return expr.strip()
    rendered = expr
    for key, value in sorted(params.items(), key=lambda row: -len(row[0])):
        rendered = re.sub(rf"\b{re.escape(key)}\b", str(value), rendered)
    parsed = parse_math(str(rendered))
    if parsed.free_symbols:
        return str(parsed)
    if parsed.is_integer:
        return int(parsed)
    if parsed.is_number:
        number = float(parsed)
        if number.is_integer():
            return int(number)
        return number
    return str(parsed)


def _sample_value(spec: Any, rng: random.Random) -> Any:
    if isinstance(spec, dict):
        if "choices" in spec:
            return rng.choice(list(spec["choices"]))
        low = int(spec.get("min", 1))
        high = int(spec.get("max", low))
        if high < low:
            high = low
        return rng.randint(low, high)
    return spec


def _render(text: str, params: dict[str, Any]) -> str:
    out = text
    for key, value in sorted(params.items(), key=lambda row: -len(row[0])):
        out = out.replace("{" + key + "}", str(value))
    return out


def _tier_for(template: ItemTemplate, params: dict[str, Any]) -> tuple[str, float] | None:
    answer: Any = params.get("answer")
    try:
        abs_answer = abs(int(answer))
    except (TypeError, ValueError):
        abs_answer = 0
    raw_coeff: Any = params.get("coeff", params.get("a"))
    try:
        parsed_coeff = abs(int(raw_coeff))
    except (TypeError, ValueError):
        parsed_coeff = 2
    coeff = parsed_coeff if parsed_coeff <= 8 else 2
    for rule in template.tier_rules:
        when = {k: v for k, v in rule.items() if k not in {"tier", "difficulty"}}
        if "max_abs_answer" in when and abs_answer > int(when["max_abs_answer"]):
            continue
        if "min_abs_answer" in when and abs_answer < int(when["min_abs_answer"]):
            continue
        if "max_abs_coeff" in when and coeff > int(when["max_abs_coeff"]):
            continue
        if "min_abs_coeff" in when and coeff < int(when["min_abs_coeff"]):
            continue
        return str(rule["tier"]), float(rule["difficulty"])
    return None


def _constraints_ok(template: ItemTemplate, params: dict[str, Any], stem: str) -> bool:
    cons = template.constraints or {}
    answer: Any = params.get("answer")
    try:
        ans_i = int(answer)
    except (TypeError, ValueError):
        ans_i = None
    if cons.get("answer_min") is not None and ans_i is not None and ans_i < int(cons["answer_min"]):
        return False
    if cons.get("answer_max") is not None and ans_i is not None and ans_i > int(cons["answer_max"]):
        return False
    if cons.get("nonzero_answer") and ans_i == 0:
        return False
    for name in cons.get("nonzero", []) or cons.get("nonzero_params", []):
        try:
            if int(params[name]) == 0:
                return False
        except (KeyError, TypeError, ValueError):
            return False
    if cons.get("no_one_x") and has_one_x(stem):
        return False
    if cons.get("no_trivial"):
        if ans_i == 0:
            return False
        if params.get("a") == 1 and "x" in stem and re.search(r"(?<![\d.])1x\b", stem):
            return False
        for name in ("a", "b", "n", "d"):
            try:
                if int(params.get(name)) == 0:  # type: ignore[arg-type]
                    return False
            except (TypeError, ValueError):
                continue
    distinct = cons.get("distinct") or []
    if distinct:
        seen: list[str] = []
        for name in distinct:
            try:
                seen.append(str(int(params[name])))
            except (KeyError, TypeError, ValueError):
                return False
        if len(set(seen)) != len(seen):
            return False
    return True


def instantiate(
    template: ItemTemplate,
    params: dict[str, Any],
    *,
    seed: int,
    index: int,
) -> Item:
    values = dict(params)
    for name, expr in (template.derived or {}).items():
        values[name] = eval_formula(expr, values)
    if template.answer_expr in {"yes", "no", "every", "none", "one"}:
        answer = template.answer_expr
    else:
        answer = eval_formula(template.answer_expr, values)
    values["answer"] = answer
    stem = _render(template.stem, values)
    if not _constraints_ok(template, values, stem):
        raise ValueError("template constraints failed")
    steps = [_render(step, values) for step in template.steps]
    raw_hints: dict[Any, str] = template.hints
    hints = []
    for level in (1, 2, 3):
        text = raw_hints.get(level) or raw_hints.get(str(level))
        if not text:
            raise ValueError(f"{template.id} missing hint {level}")
        hints.append({"level": level, **loc(_render(str(text), values))})
    rules = []
    for row in template.misconceptions:
        formula = row.get("formula") or ""
        wrong = eval_formula(formula, values) if formula else ""
        rules.append({"id": row["id"], "when_answer_equals": [str(wrong)]})
    verify = template.verify
    if isinstance(verify, str):
        verify = _render(verify, values)
    elif isinstance(verify, dict):
        verify = {
            key: _render(str(val), values) if isinstance(val, str) else val
            for key, val in verify.items()
        }
    assigned = _tier_for(template, values)
    if assigned is None:
        raise ValueError("no tier matched")
    _tier, difficulty = assigned
    digest = template_hash(template)
    item_id = f"ITEM.GEN.{template.id}.{seed}.{index:04d}"
    payload: dict[str, Any] = {
        "id": item_id,
        "skill_ids": [template.skill_id],
        "difficulty": difficulty,
        "type": template.type.value if hasattr(template.type, "value") else template.type,
        "pool": "practice",
        "role": template.role.value,
        "stem": loc(stem),
        "answer": {"sympy": str(answer), "accept": [str(answer)]},
        "solution_steps": [loc(step) for step in steps],
        "hints": hints,
        "prediction_prompt": loc(_render(template.prediction, values)),
        "misconception_rules": rules,
        "reviewed_by": None,
        "status": "draft",
        "template_id": template.id,
        "generator_version": GENERATOR_VERSION,
        "template_hash": digest,
    }
    if verify is not None:
        payload["verify"] = verify
    if template.options:
        payload["options"] = [opt.model_dump(by_alias=True) for opt in template.options]
    item = Item.model_validate(payload)
    item = Item.model_validate({**payload, **draft_fields(item)})
    errors, _warnings = lint_item_texts(
        stem=item.stem.en,
        hints=[hint.en for hint in item.hints],
        extras=[item.prediction_prompt.en, *[step.en for step in item.solution_steps]],
    )
    if errors:
        raise ValueError("; ".join(errors))
    _assert_instance(item, rules)
    return item


def _assert_instance(item: Item, rules: list[dict]) -> None:
    if has_one_x(item.stem.en):
        raise ValueError(f"{item.id} uses 1x")
    last = item.solution_steps[-1].en
    if not last_step_matches_answer(last, item.answer.sympy, item_type=item.type):
        raise ValueError(f"{item.id} last step mismatch")
    for hint in item.hints:
        if hint.level >= 3:
            continue
        if hint_leaks_answer(hint.en, item.answer.sympy):
            raise ValueError(f"{item.id} hint {hint.level} leaks")
    checked = check_item_stem_answer(item)
    if checked not in {None, "manual", "teacher"}:
        raise ValueError(checked)
    for rule in rules:
        for wrong in rule.get("when_answer_equals") or []:
            if str(wrong) == str(item.answer.sympy):
                raise ValueError(f"{item.id} misconception equals the answer")


def generate_instances(
    templates: list[ItemTemplate],
    *,
    seed: int,
    existing_stems: set[str],
    per_skill: int = PRACTICE_PER_SKILL,
) -> list[Item]:
    rng = random.Random(seed)
    by_skill: dict[str, list[ItemTemplate]] = defaultdict(list)
    for template in templates:
        by_skill[template.skill_id].append(template)
    out: list[Item] = []
    seen = set(existing_stems)
    for skill_id, group in sorted(by_skill.items()):
        counts = {"easy": 0, "medium": 0, "hard": 0}
        index = 0
        attempts = 0
        while sum(counts.values()) < per_skill and attempts < 12000:
            attempts += 1
            template = group[index % len(group)]
            params = {name: _sample_value(spec, rng) for name, spec in template.parameters.items()}
            try:
                values = dict(params)
                for name, expr in (template.derived or {}).items():
                    values[name] = eval_formula(expr, values)
                if template.answer_expr not in {"yes", "no", "every", "none", "one"}:
                    values["answer"] = eval_formula(template.answer_expr, values)
                else:
                    values["answer"] = template.answer_expr
                stem = _render(template.stem, values)
                if not _constraints_ok(template, values, stem):
                    index += 1
                    continue
                assigned = _tier_for(template, values)
                if assigned is None:
                    index += 1
                    continue
                tier, _diff = assigned
                need_tier = counts[tier] < TIER_TARGETS[tier]
                remaining = per_skill - sum(counts.values())
                missing_hard = [
                    name for name, want in TIER_TARGETS.items() if counts[name] < MIN_PER_TIER
                ]
                if (
                    not need_tier
                    and missing_hard
                    and tier not in missing_hard
                    and remaining <= len(missing_hard)
                ):
                    index += 1
                    continue
                item = instantiate(template, params, seed=seed, index=index)
            except (ValueError, ParseError, ZeroDivisionError, KeyError):
                index += 1
                continue
            key = re.sub(r"\s+", " ", item.stem.en.strip()).lower()
            if key in seen:
                index += 1
                continue
            if (
                counts[item_tier(item.difficulty)] >= TIER_TARGETS[item_tier(item.difficulty)]
                and sum(counts.values()) < per_skill
            ):
                if all(counts[name] >= MIN_PER_TIER for name in TIER_TARGETS):
                    pass
                elif counts[item_tier(item.difficulty)] >= TIER_TARGETS[item_tier(item.difficulty)]:
                    index += 1
                    continue
            seen.add(key)
            out.append(item)
            counts[item_tier(item.difficulty)] += 1
            index += 1
        if sum(counts.values()) < per_skill or any(counts[t] < MIN_PER_TIER for t in TIER_TARGETS):
            raise RuntimeError(
                f"{skill_id} generated {counts} (need {per_skill}, {MIN_PER_TIER}/tier)"
            )
    return out


def write_instances(root: Path, items: list[Item]) -> None:
    folder = root / "items" / "math" / "practice" / "generated"
    if folder.exists():
        for path in folder.glob("*.yaml"):
            path.unlink()
    folder.mkdir(parents=True, exist_ok=True)
    for item in items:
        path = folder / f"{item.id}.yaml"
        data = item.model_dump(mode="json", by_alias=True, exclude_none=True)
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def generate_from_templates(root: Path, *, seed: int) -> list[Item]:
    from app.content.template_catalog import builtin_templates

    for template in builtin_templates():
        write_template(root, template)
    existing = load_templates(root)
    bundle = load_bundle(root)
    stems = {
        re.sub(r"\s+", " ", item.stem.en.strip()).lower()
        for item in bundle.items
        if not item.template_id
    }
    items = generate_instances(existing, seed=seed, existing_stems=stems)
    approved = {tpl.id: tpl for tpl in existing if tpl.status.value == "approved"}
    for item in items:
        tpl = approved.get(item.template_id or "")
        if tpl is None:
            continue
        digest = template_hash(tpl)
        if item.template_hash == digest and item.generator_version == GENERATOR_VERSION:
            item.status = type(item.status)("approved")
            item.reviewed_by = tpl.reviewed_by
    write_instances(root, items)
    report = validate_bundle(load_bundle(root))
    if not report.ok:
        raise RuntimeError("generated content failed validation:\n" + "\n".join(report.errors))
    return items


def sample_instances(template: ItemTemplate, *, seed: int, n: int = 10) -> list[Item]:
    items: list[Item] = []
    rng = random.Random(seed)
    index = 0
    seen: set[str] = set()
    while len(items) < n and index < 2000:
        params = {name: _sample_value(spec, rng) for name, spec in template.parameters.items()}
        try:
            item = instantiate(template, params, seed=seed, index=index)
        except (ValueError, ParseError, ZeroDivisionError, KeyError):
            index += 1
            continue
        key = item.stem.en
        if key in seen:
            index += 1
            continue
        seen.add(key)
        items.append(item)
        index += 1
    return items
