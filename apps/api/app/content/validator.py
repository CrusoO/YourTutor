from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.content.leak import hint_leaks_answer
from app.content.math_parse import ParseError, expressions_equivalent, parse_math
from app.content.schema import (
    CheckpointForms,
    ContentBundle,
    GlossaryFile,
    Item,
    ItemPool,
    Misconception,
    Overlay,
    Skill,
)

LIVE_MIN_PRACTICE = 5
LIVE_MIN_DIAGNOSTIC = 2
LIVE_MIN_CHECKPOINT = 10
LIVE_WARN_CHECKPOINT = 15


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bundle: ContentBundle | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def _read_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def load_bundle(root: Path) -> ContentBundle:
    skills = [_model(Skill, p) for p in sorted((root / "skills").rglob("*.yaml"))]
    items = [_model(Item, p) for p in sorted((root / "items").rglob("*.yaml"))]
    misconceptions = [
        _model(Misconception, p) for p in sorted((root / "misconceptions").rglob("*.yaml"))
    ]
    overlays = [_model(Overlay, p) for p in sorted((root / "overlays").rglob("*.yaml"))]
    glossaries: list[GlossaryFile] = []
    glossary_dir = root / "glossary"
    if glossary_dir.exists():
        for path in sorted(glossary_dir.rglob("*.yaml")):
            raw = _read_yaml(path)
            glossaries.append(GlossaryFile.model_validate(raw))
    forms: list[CheckpointForms] = []
    cp_dir = root / "checkpoints"
    if cp_dir.exists():
        for path in sorted(cp_dir.rglob("*.yaml")):
            forms.append(_model(CheckpointForms, path))
    return ContentBundle(
        skills=skills,
        items=items,
        misconceptions=misconceptions,
        overlays=overlays,
        glossaries=glossaries,
        checkpoint_forms=forms,
    )


def _model(cls, path: Path):  # type: ignore[no-untyped-def]
    return cls.model_validate(_read_yaml(path))


def last_step_matches_answer(step_en: str, answer_sympy: str) -> bool:
    if expressions_equivalent(step_en, answer_sympy):
        return True
    if "=" in step_en:
        rhs = step_en.rsplit("=", 1)[-1]
        if expressions_equivalent(rhs, answer_sympy):
            return True
    return False


def validate_bundle(bundle: ContentBundle) -> ValidationReport:
    report = ValidationReport(bundle=bundle)
    _unique_ids(bundle, report)
    _refs_and_cycles(bundle, report)
    _items(bundle, report)
    _checkpoint_isolation(bundle, report)
    _checkpoint_forms(bundle, report)
    _live_chapter(bundle, report)
    return report


def validate_path(root: Path) -> ValidationReport:
    try:
        bundle = load_bundle(root)
    except Exception as exc:  # noqa: BLE001
        report = ValidationReport()
        report.errors.append(str(exc))
        return report
    return validate_bundle(bundle)


def _unique_ids(bundle: ContentBundle, report: ValidationReport) -> None:
    seen: dict[str, str] = {}
    for kind, objs in (
        ("skill", bundle.skills),
        ("item", bundle.items),
        ("misconception", bundle.misconceptions),
        ("overlay", bundle.overlays),
        ("checkpoint_forms", bundle.checkpoint_forms),
    ):
        for obj in objs:
            key = obj.id
            if key in seen:
                report.errors.append(f"duplicate id {key} ({seen[key]} and {kind})")
            else:
                seen[key] = kind


def _refs_and_cycles(bundle: ContentBundle, report: ValidationReport) -> None:
    skill_ids = {s.id for s in bundle.skills}
    mc_ids = {m.id for m in bundle.misconceptions}
    for skill in bundle.skills:
        for ref in skill.prerequisites + skill.related:
            if ref not in skill_ids:
                report.errors.append(f"{skill.id} references unknown skill {ref}")
        for ref in skill.misconceptions:
            if ref not in mc_ids:
                report.errors.append(f"{skill.id} references unknown misconception {ref}")
    for mc in bundle.misconceptions:
        if mc.remedial_skill not in skill_ids:
            report.errors.append(f"{mc.id} remedial_skill {mc.remedial_skill} is unknown")
    for item in bundle.items:
        if not item.skill_ids:
            report.errors.append(f"{item.id} missing primary skill")
            continue
        for ref in item.skill_ids:
            if ref not in skill_ids:
                report.errors.append(f"{item.id} references unknown skill {ref}")
        for rule in item.misconception_rules:
            if rule.id not in mc_ids:
                report.errors.append(f"{item.id} references unknown misconception {rule.id}")
    for overlay in bundle.overlays:
        for ref in overlay.skill_ids:
            if ref not in skill_ids:
                report.errors.append(f"{overlay.id} references unknown skill {ref}")

    graph = {s.id: list(s.prerequisites) for s in bundle.skills}
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            report.errors.append("prerequisite cycle: " + " -> ".join(stack + [node]))
            return
        visiting.add(node)
        for nxt in graph.get(node, []):
            dfs(nxt, stack + [node])
        visiting.remove(node)
        visited.add(node)

    for sid in graph:
        dfs(sid, [])


def _items(bundle: ContentBundle, report: ValidationReport) -> None:
    for item in bundle.items:
        if not item.skill_ids:
            report.errors.append(f"{item.id} must have a primary skill (skill_ids[0])")
        try:
            parse_math(item.answer.sympy)
        except ParseError as exc:
            report.errors.append(f"{item.id} answer.sympy failed allowlist parse: {exc}")
            continue
        last = item.solution_steps[-1].en
        if not last_step_matches_answer(last, item.answer.sympy):
            report.errors.append(
                f"{item.id} final solution step is not equivalent to answer {item.answer.sympy!r}"
            )
        for hint in item.hints:
            if hint.level >= 3:
                continue
            if hint_leaks_answer(hint.en, item.answer.sympy):
                report.errors.append(f"{item.id} hint level {hint.level} leaks the answer")
            for accept in item.answer.accept:
                if hint_leaks_answer(hint.en, accept):
                    report.errors.append(
                        f"{item.id} hint level {hint.level} leaks accept value {accept!r}"
                    )
                    break


def _checkpoint_isolation(bundle: ContentBundle, report: ValidationReport) -> None:
    checkpoint_ids = {i.id for i in bundle.items if i.pool == ItemPool.checkpoint}
    practice_ids = {i.id for i in bundle.items if i.pool == ItemPool.practice}
    overlap = checkpoint_ids & practice_ids
    if overlap:
        report.errors.append(f"checkpoint ids reused as practice: {sorted(overlap)}")
    for item in bundle.items:
        if item.pool == ItemPool.practice and item.id in checkpoint_ids:
            report.errors.append(f"practice item {item.id} is also a checkpoint")


def _checkpoint_forms(bundle: ContentBundle, report: ValidationReport) -> None:
    items = {i.id: i for i in bundle.items}
    checkpoint_ids = {i.id for i in bundle.items if i.pool == ItemPool.checkpoint}
    for forms in bundle.checkpoint_forms:
        for label, ids in (("A", forms.form_a), ("B", forms.form_b)):
            if len(ids) < LIVE_MIN_CHECKPOINT:
                report.errors.append(
                    f"{forms.id} form {label} has {len(ids)} items; "
                    f"hard minimum is {LIVE_MIN_CHECKPOINT}"
                )
            elif len(ids) < LIVE_WARN_CHECKPOINT:
                report.warnings.append(
                    f"{forms.id} form {label} has {len(ids)} items; trials should use 15–20"
                )
            for item_id in ids:
                if item_id not in items:
                    report.errors.append(f"{forms.id} form {label} unknown item {item_id}")
                elif item_id not in checkpoint_ids:
                    report.errors.append(
                        f"{forms.id} form {label} lists non-checkpoint item {item_id}"
                    )
        for src, dst in forms.match_map.items():
            if src not in forms.form_a:
                report.errors.append(f"{forms.id} match_map key {src} is not in form A")
            if dst not in forms.form_b:
                report.errors.append(f"{forms.id} match_map value {dst} is not in form B")
        if set(forms.match_map) != set(forms.form_a):
            report.errors.append(f"{forms.id} match_map must cover every form A item")
        if set(forms.match_map.values()) != set(forms.form_b):
            report.errors.append(f"{forms.id} match_map must cover every form B item")


def _live_chapter(bundle: ContentBundle, report: ValidationReport) -> None:
    by_skill_pool: dict[tuple[str, ItemPool], int] = defaultdict(int)
    for item in bundle.items:
        if item.status.value != "approved":
            continue
        by_skill_pool[(item.primary_skill, item.pool)] += 1
    for overlay in bundle.overlays:
        missing: list[str] = []
        for skill_id in overlay.skill_ids:
            practice = by_skill_pool[(skill_id, ItemPool.practice)]
            diagnostic = by_skill_pool[(skill_id, ItemPool.diagnostic)]
            if practice < LIVE_MIN_PRACTICE:
                missing.append(f"{skill_id} practice {practice}/{LIVE_MIN_PRACTICE}")
            if diagnostic < LIVE_MIN_DIAGNOSTIC:
                missing.append(f"{skill_id} diagnostic {diagnostic}/{LIVE_MIN_DIAGNOSTIC}")
        if overlay.live:
            if missing:
                report.errors.append(
                    f"{overlay.id} is live but below threshold: " + "; ".join(missing)
                )
            if not bundle.checkpoint_forms:
                report.errors.append(f"{overlay.id} is live but missing matched checkpoint forms")
        elif missing:
            report.warnings.append(
                f"{overlay.id} is not live (approved counts below threshold)"
            )
