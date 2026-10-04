from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.content.language import lint_item_texts
from app.content.leak import hint_leaks_answer
from app.content.math_parse import ParseError, expressions_equivalent, normalize, parse_math
from app.content.schema import (
    CheckpointForms,
    ContentBundle,
    GlossaryFile,
    Item,
    ItemPool,
    ItemType,
    Misconception,
    Overlay,
    Skill,
)
from app.content.signatures import has_one_x, item_content_hash, structure_signature
from app.content.stem_solve import check_item_stem_answer
from app.content.templates import GENERATOR_VERSION, load_templates, template_hash

LIVE_MIN_PRACTICE = 5
LIVE_MIN_DIAGNOSTIC = 2
LIVE_MIN_CHECKPOINT = 10
LIVE_WARN_CHECKPOINT = 15
STEM_MIN_PRACTICE = 5
STEM_MIN_DIAGNOSTIC = 3
WORD_ANSWER_MIN = 1
WORD_ANSWER_MAX = 80


def _is_e2e_mini_skill(skill_id: str) -> bool:
    return skill_id.startswith("MATH.E2E.")


def _is_e2e_mini_checkpoint_forms(forms: CheckpointForms) -> bool:
    return forms.checkpoint_id.startswith("CP.E2E.") or forms.id.startswith("CP.E2E.")
MCQ_IMBALANCE = 0.7
HINT_SHARE = 0.25
MIN_HINT1_PRACTICE = 3
MIN_STRUCTURES_PRACTICE = 3
HINT3_OVERLAP = 0.70
_HINT_TOKEN = re.compile(r"[a-z0-9]+")
_LET_X = re.compile(r"\blet\s+x\b", re.IGNORECASE)


def item_tier(difficulty: float) -> str:
    if difficulty < 0.4:
        return "easy"
    if difficulty <= 0.8:
        return "medium"
    return "hard"


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    manual_review: list[str] = field(default_factory=list)
    manual_review_rows: list[tuple[str, str, str]] = field(default_factory=list)
    needs_teacher_check: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    no_misconception_rules: list[str] = field(default_factory=list)
    ab_mismatches: list[str] = field(default_factory=list)
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
        templates=load_templates(root),
    )


def _model(cls, path: Path):  # type: ignore[no-untyped-def]
    return cls.model_validate(_read_yaml(path))


def last_step_matches_answer(
    step_en: str, answer_sympy: str, *, item_type: ItemType | None = None
) -> bool:
    if item_type == ItemType.mcq:
        return normalize(answer_sympy) in normalize(step_en) or normalize(step_en) == normalize(
            answer_sympy
        )
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
    _stem_answers(bundle, report)
    _stem_uniqueness(bundle, report)
    _bkt_params(bundle, report)
    _mcq_and_word_warnings(bundle, report)
    _hint_diversity(bundle, report)
    _structure_and_tiers(bundle, report)
    _one_x_ban(bundle, report)
    _hint_language(bundle, report)
    _language_quality(bundle, report)
    _approval_hashes(bundle, report)
    _template_approval(bundle, report)
    _checkpoint_practice_stems(bundle, report)
    _live_chapter(bundle, report)
    _build_report(bundle, report)
    return report


def validate_path(root: Path) -> ValidationReport:
    try:
        bundle = load_bundle(root)
    except Exception as exc:  # noqa: BLE001
        report = ValidationReport()
        report.errors.append(str(exc))
        return report
    report = validate_bundle(bundle)
    _persist_hash_resets(root, report)
    return report


def _persist_hash_resets(root: Path, report: ValidationReport) -> None:
    if report.bundle is None:
        return
    reset_ids = {
        warning.split(" ", 1)[0]
        for warning in report.warnings
        if "reset to draft" in warning
    }
    if not reset_ids:
        return
    folders = [root / "items"]
    if (root / "templates").exists():
        folders.append(root / "templates")
    for folder in folders:
        for path in folder.rglob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("id") not in reset_ids:
                continue
            data["status"] = "draft"
            data["reviewed_by"] = None
            path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )


def _unique_ids(bundle: ContentBundle, report: ValidationReport) -> None:
    seen: dict[str, str] = {}
    for kind, objs in (
        ("skill", bundle.skills),
        ("item", bundle.items),
        ("misconception", bundle.misconceptions),
        ("overlay", bundle.overlays),
        ("checkpoint_forms", bundle.checkpoint_forms),
        ("template", bundle.templates),
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
        if item.type != ItemType.mcq:
            try:
                parse_math(item.answer.sympy)
            except ParseError as exc:
                report.errors.append(f"{item.id} answer.sympy failed allowlist parse: {exc}")
                continue
        last = item.solution_steps[-1].en
        if not last_step_matches_answer(last, item.answer.sympy, item_type=item.type):
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
        relax_checkpoint = _is_e2e_mini_checkpoint_forms(forms)
        for label, ids in (("A", forms.form_a), ("B", forms.form_b)):
            if relax_checkpoint:
                continue
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
        unchecked = [
            item.id
            for item in bundle.items
            if item.id in report.needs_teacher_check
            and item.status.value != "approved"
            and item.primary_skill in overlay.skill_ids
        ]
        if overlay.live:
            if missing:
                report.errors.append(
                    f"{overlay.id} is live but below threshold: " + "; ".join(missing)
                )
            if not bundle.checkpoint_forms:
                report.errors.append(f"{overlay.id} is live but missing matched checkpoint forms")
            if unchecked:
                report.errors.append(
                    f"{overlay.id} is live but has needs_teacher_check "
                    f"unapproved items: {', '.join(unchecked)}"
                )
        elif missing:
            report.warnings.append(
                f"{overlay.id} is not live (approved counts below threshold)"
            )


def _hint_diversity(bundle: ContentBundle, report: ValidationReport) -> None:
    by_skill: dict[str, list[Item]] = defaultdict(list)
    practice: dict[str, list[Item]] = defaultdict(list)
    for item in bundle.items:
        by_skill[item.primary_skill].append(item)
        if item.pool == ItemPool.practice:
            practice[item.primary_skill].append(item)
    for skill_id, items in by_skill.items():
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            for hint in item.hints:
                if hint.level <= 2:
                    counts[normalize(hint.en)] += 1
        for text, n in counts.items():
            if n / len(items) > HINT_SHARE:
                report.warnings.append(
                    f"{skill_id} hint reused on {n}/{len(items)} items (>25%): {text[:60]}"
                )
    for skill_id, items in practice.items():
        if len(items) < 5:
            continue
        distinct = {next(h.en for h in item.hints if h.level == 1) for item in items}
        if len(distinct) < MIN_HINT1_PRACTICE:
            report.errors.append(
                f"{skill_id} has {len(distinct)} distinct hint-1 strings; "
                f"minimum is {MIN_HINT1_PRACTICE}"
            )


def _structure_and_tiers(bundle: ContentBundle, report: ValidationReport) -> None:
    structs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    tiers: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in bundle.items:
        structs[item.primary_skill][item.pool.value].add(structure_signature(item.stem.en))
        if item.pool == ItemPool.practice:
            tiers[item.primary_skill][item_tier(item.difficulty)] += 1
    report.stats.setdefault("structures_by_skill_pool", {})
    report.stats["structures_by_skill_pool"] = {
        skill: {pool: len(sigs) for pool, sigs in sorted(pools.items())}
        for skill, pools in sorted(structs.items())
    }
    report.stats["practice_by_skill_tier"] = {
        skill: dict(sorted(counts.items())) for skill, counts in sorted(tiers.items())
    }
    missing: list[str] = []
    for skill_id, counts in tiers.items():
        if sum(counts.values()) < 5:
            continue
        n_struct = len(structs[skill_id].get("practice", set()))
        if n_struct < MIN_STRUCTURES_PRACTICE:
            report.errors.append(
                f"{skill_id} practice has {n_struct} stem structures; "
                f"minimum is {MIN_STRUCTURES_PRACTICE}"
            )
        for tier in ("easy", "medium", "hard"):
            if counts.get(tier, 0) == 0:
                missing.append(f"{skill_id} missing practice {tier}")
    report.stats["tier_gaps"] = missing
    for row in missing:
        report.warnings.append(row + " (selection falls back to nearest tier)")


def _hint_tokens(text: str) -> set[str]:
    return set(_HINT_TOKEN.findall(normalize(text).lower()))


def hint3_overlap_ratio(hint2: str, hint3: str) -> float:
    left = _hint_tokens(hint3)
    right = _hint_tokens(hint2)
    if not left:
        return 0.0
    return len(left & right) / len(left)


def _hint_language(bundle: ContentBundle, report: ValidationReport) -> None:
    for item in bundle.items:
        stem = item.stem.en
        has_equals = "=" in stem
        hints = {h.level: h.en for h in item.hints}
        if not has_equals:
            for hint in item.hints:
                lower = hint.en.lower()
                if "equation" in lower or "both sides" in lower:
                    report.errors.append(
                        f"{item.id} hint {hint.level} uses 'equation' or 'both sides' "
                        f"but the stem has no '='"
                    )
        if "WORD_PROBLEMS" in item.primary_skill:
            h1 = hints.get(1, "")
            if not _LET_X.search(h1):
                report.errors.append(
                    f"{item.id} word-problem hint 1 must define the unknown (Let x ...)"
                )
        h2, h3 = hints.get(2, ""), hints.get(3, "")
        if h2 and h3:
            overlap = hint3_overlap_ratio(h2, h3)
            if overlap > HINT3_OVERLAP:
                report.warnings.append(
                    f"{item.id} hint 3 overlaps hint 2 by {overlap:.0%} (>70%)"
                )


def _language_quality(bundle: ContentBundle, report: ValidationReport) -> None:
    for item in bundle.items:
        errors, warnings = lint_item_texts(
            stem=item.stem.en,
            hints=[hint.en for hint in item.hints],
            extras=[item.prediction_prompt.en],
        )
        for error in errors:
            report.errors.append(f"{item.id} {error}")
        for warning in warnings:
            report.warnings.append(f"{item.id} {warning}")


def _one_x_ban(bundle: ContentBundle, report: ValidationReport) -> None:
    for item in bundle.items:
        if has_one_x(item.stem.en):
            report.errors.append(f"{item.id} stem uses '1x'; write 'x'")


def _approval_hashes(bundle: ContentBundle, report: ValidationReport) -> None:
    for item in bundle.items:
        if item.status.value != "approved":
            continue
        digest = item_content_hash(item)
        if item.content_hash != digest and item.template_id is None:
            item.status = type(item.status)("draft")
            item.reviewed_by = None
            report.warnings.append(
                f"{item.id} approved content changed; reset to draft (hash mismatch)"
            )


def _template_approval(bundle: ContentBundle, report: ValidationReport) -> None:
    for tpl in bundle.templates:
        digest = template_hash(tpl)
        if tpl.status.value == "approved" and tpl.content_hash and tpl.content_hash != digest:
            tpl.status = type(tpl.status)("draft")
            tpl.reviewed_by = None
            report.warnings.append(
                f"{tpl.id} approved template changed; reset to draft"
            )
    templates = {tpl.id: tpl for tpl in bundle.templates}
    for item in bundle.items:
        if not item.template_id:
            continue
        tpl = templates.get(item.template_id)
        if tpl is None:
            report.errors.append(f"{item.id} references unknown template {item.template_id}")
            continue
        digest = template_hash(tpl)
        stale = item.template_hash != digest or item.generator_version != GENERATOR_VERSION
        if stale:
            if item.status.value == "approved":
                item.status = type(item.status)("draft")
                item.reviewed_by = None
                report.warnings.append(
                    f"{item.id} template hash or generator changed; reset to draft"
                )
        elif tpl.status.value == "approved":
            item.status = type(item.status)("approved")
            item.reviewed_by = tpl.reviewed_by
            if not item.content_hash:
                item.content_hash = item_content_hash(item)


def _checkpoint_practice_stems(bundle: ContentBundle, report: ValidationReport) -> None:
    practice = {_stem_text(item) for item in bundle.items if item.pool == ItemPool.practice}
    for item in bundle.items:
        if item.pool == ItemPool.checkpoint and _stem_text(item) in practice:
            report.errors.append(f"{item.id} checkpoint stem collides with a practice stem")


def _stem_answers(bundle: ContentBundle, report: ValidationReport) -> None:
    for item in bundle.items:
        result = check_item_stem_answer(item)
        if result is None:
            continue
        if result in {"manual", "teacher"}:
            report.manual_review.append(item.id)
            report.manual_review_rows.append((item.id, item.primary_skill, item.stem.en))
            if result == "teacher":
                report.needs_teacher_check.append(item.id)
        else:
            report.errors.append(result)


def _stem_text(item: Item) -> str:
    return normalize(item.stem.en)


def _stem_uniqueness(bundle: ContentBundle, report: ValidationReport) -> None:
    by_pool: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    by_skill_pool: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in bundle.items:
        key = _stem_text(item)
        by_pool[item.pool.value][key].append(item.id)
        by_skill_pool[(item.primary_skill, item.pool.value)].add(key)
    for pool, stems in by_pool.items():
        for _stem, ids in stems.items():
            if len(ids) > 1:
                report.errors.append(
                    f"duplicate stem in {pool} pool: {', '.join(sorted(ids))}"
                )
    items = {i.id: i for i in bundle.items}
    for forms in bundle.checkpoint_forms:
        for src, dst in forms.match_map.items():
            left, right = items.get(src), items.get(dst)
            if left is None or right is None:
                continue
            if _stem_text(left) == _stem_text(right):
                report.errors.append(
                    f"{forms.id} matched A/B items {src} and {dst} have identical stems"
                )
    practice_skills = {i.primary_skill for i in bundle.items if i.pool == ItemPool.practice}
    diagnostic_skills = {
        i.primary_skill for i in bundle.items if i.pool == ItemPool.diagnostic
    }
    for skill_id in sorted(practice_skills):
        if _is_e2e_mini_skill(skill_id):
            continue
        count = len(by_skill_pool[(skill_id, ItemPool.practice.value)])
        if count < STEM_MIN_PRACTICE:
            report.errors.append(
                f"{skill_id} practice has {count} distinct stems; "
                f"minimum is {STEM_MIN_PRACTICE}"
            )
    for skill_id in sorted(diagnostic_skills):
        if _is_e2e_mini_skill(skill_id):
            continue
        count = len(by_skill_pool[(skill_id, ItemPool.diagnostic.value)])
        if count < STEM_MIN_DIAGNOSTIC:
            report.errors.append(
                f"{skill_id} diagnostic has {count} distinct stems; "
                f"minimum is {STEM_MIN_DIAGNOSTIC}"
            )


def _bkt_params(bundle: ContentBundle, report: ValidationReport) -> None:
    for skill in bundle.skills:
        params = skill.bkt
        for name, value in (
            ("p_init", params.p_init),
            ("p_learn", params.p_learn),
            ("p_slip", params.p_slip),
            ("p_guess", params.p_guess),
        ):
            if not 0 < value < 1:
                report.errors.append(f"{skill.id} BKT {name}={value} must be in (0, 1)")
        if params.p_slip + params.p_guess >= 1:
            report.errors.append(f"{skill.id} BKT p_slip + p_guess must be < 1")


def _mcq_and_word_warnings(bundle: ContentBundle, report: ValidationReport) -> None:
    by_skill: dict[str, list[str]] = defaultdict(list)
    for item in bundle.items:
        if item.type == ItemType.mcq:
            by_skill[item.primary_skill].append(item.answer.sympy)
        if "WORD_PROBLEMS" not in item.primary_skill:
            continue
        try:
            value = float(normalize(item.answer.sympy))
        except ValueError:
            continue
        if value < WORD_ANSWER_MIN or value > WORD_ANSWER_MAX:
            report.warnings.append(
                f"{item.id} word-problem answer {value} outside plausible range "
                f"[{WORD_ANSWER_MIN}, {WORD_ANSWER_MAX}]"
            )
    for skill_id, answers in by_skill.items():
        if len(answers) < 2:
            continue
        counts: dict[str, int] = defaultdict(int)
        for answer in answers:
            counts[answer] += 1
        top, n = max(counts.items(), key=lambda row: row[1])
        if n / len(answers) > MCQ_IMBALANCE:
            report.warnings.append(
                f"{skill_id} MCQ answers more than {int(MCQ_IMBALANCE * 100)}% "
                f"{top!r} ({n}/{len(answers)})"
            )


def _build_report(bundle: ContentBundle, report: ValidationReport) -> None:
    by_pool: dict[str, int] = defaultdict(int)
    by_tier: dict[str, int] = defaultdict(int)
    by_skill: dict[str, int] = defaultdict(int)
    stems_by_pool: dict[str, set[str]] = defaultdict(set)
    stems_by_skill: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    no_rules: list[str] = []
    for item in bundle.items:
        by_pool[item.pool.value] += 1
        by_tier[item_tier(item.difficulty)] += 1
        by_skill[item.primary_skill] += 1
        key = _stem_text(item)
        stems_by_pool[item.pool.value].add(key)
        stems_by_skill[item.primary_skill][item.pool.value].add(key)
        if not item.misconception_rules:
            no_rules.append(item.id)
    report.stats = {
        "by_pool": dict(by_pool),
        "by_tier": dict(by_tier),
        "by_skill": dict(sorted(by_skill.items())),
        "item_count": len(bundle.items),
        "distinct_stems_by_pool": {
            pool: len(stems) for pool, stems in sorted(stems_by_pool.items())
        },
        "distinct_stems_by_skill": {
            skill_id: {pool: len(stems) for pool, stems in sorted(pools.items())}
            for skill_id, pools in sorted(stems_by_skill.items())
        },
        "needs_teacher_check_count": len(report.needs_teacher_check),
        "imbalance_warnings": [
            warning
            for warning in report.warnings
            if "MCQ answers" in warning or "word-problem answer" in warning
        ],
        "structures_by_skill_pool": report.stats.get("structures_by_skill_pool", {}),
        "practice_by_skill_tier": report.stats.get("practice_by_skill_tier", {}),
        "tier_gaps": report.stats.get("tier_gaps", []),
        "templates_per_skill": _templates_per_skill(bundle),
        "instances_by_skill_tier": _instances_by_skill_tier(bundle),
    }
    report.no_misconception_rules = no_rules
    items = {i.id: i for i in bundle.items}
    mismatches: list[str] = []
    for forms in bundle.checkpoint_forms:
        for src, dst in forms.match_map.items():
            a, b = items.get(src), items.get(dst)
            if a is None or b is None:
                continue
            if a.primary_skill != b.primary_skill or item_tier(a.difficulty) != item_tier(
                b.difficulty
            ):
                mismatches.append(
                    f"{src} ({a.primary_skill}/{item_tier(a.difficulty)}) "
                    f"!= {dst} ({b.primary_skill}/{item_tier(b.difficulty)})"
                )
    report.ab_mismatches = mismatches


def _templates_per_skill(bundle: ContentBundle) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for template in bundle.templates:
        counts[template.skill_id] += 1
    return dict(sorted(counts.items()))


def _instances_by_skill_tier(bundle: ContentBundle) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in bundle.items:
        if not item.template_id or item.pool != ItemPool.practice:
            continue
        counts[item.primary_skill][item_tier(item.difficulty)] += 1
    return {skill: dict(sorted(tiers.items())) for skill, tiers in sorted(counts.items())}


def format_report(report: ValidationReport) -> str:
    lines = [
        "Validator report",
        f"  items: {report.stats.get('item_count', 0)}",
        f"  by pool: {report.stats.get('by_pool', {})}",
        f"  by tier: {report.stats.get('by_tier', {})}",
        "  by skill:",
    ]
    for skill, count in (report.stats.get("by_skill") or {}).items():
        lines.append(f"    {skill}: {count}")
    lines.append("  distinct stems by pool:")
    for pool, count in (report.stats.get("distinct_stems_by_pool") or {}).items():
        lines.append(f"    {pool}: {count}")
    lines.append("  distinct stems by skill:")
    for skill, pools in (report.stats.get("distinct_stems_by_skill") or {}).items():
        parts = ", ".join(f"{pool} {n}" for pool, n in pools.items())
        lines.append(f"    {skill}: {parts}")
    lines.append("  distinct structures by skill/pool:")
    for skill, pools in (report.stats.get("structures_by_skill_pool") or {}).items():
        parts = ", ".join(f"{pool} {n}" for pool, n in pools.items())
        lines.append(f"    {skill}: {parts}")
    lines.append("  practice items by skill/tier:")
    for skill, tiers in (report.stats.get("practice_by_skill_tier") or {}).items():
        parts = ", ".join(f"{tier} {n}" for tier, n in tiers.items())
        lines.append(f"    {skill}: {parts}")
    lines.append("  generated instances by skill/tier:")
    for skill, tiers in (report.stats.get("instances_by_skill_tier") or {}).items():
        parts = ", ".join(f"{tier} {n}" for tier, n in tiers.items())
        lines.append(f"    {skill}: {parts}")
    lines.append("  templates per skill:")
    for skill, count in (report.stats.get("templates_per_skill") or {}).items():
        lines.append(f"    {skill}: {count}")
    gaps = report.stats.get("tier_gaps") or []
    lines.append(f"  practice tier gaps: {len(gaps)}")
    for row in gaps:
        lines.append(f"    {row}")
    lines.append(f"  no misconception_rules: {len(report.no_misconception_rules)}")
    for item_id in report.no_misconception_rules:
        lines.append(f"    {item_id}")
    lines.append(f"  A/B skill-or-tier mismatches: {len(report.ab_mismatches)}")
    for row in report.ab_mismatches:
        lines.append(f"    {row}")
    lines.append(f"  needs_teacher_check: {report.stats.get('needs_teacher_check_count', 0)}")
    for item_id in report.needs_teacher_check:
        lines.append(f"    {item_id}")
    lines.append(f"  imbalance warnings: {len(report.stats.get('imbalance_warnings') or [])}")
    for warning in report.stats.get("imbalance_warnings") or []:
        lines.append(f"    {warning}")
    lines.append(f"  manual review (stem not machine-solvable): {len(report.manual_review)}")
    for item_id, skill, stem in report.manual_review_rows:
        lines.append(f"    {item_id}  {skill}  {stem}")
    return "\n".join(lines)
