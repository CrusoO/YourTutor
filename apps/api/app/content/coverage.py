"""Template and item coverage by role (apply / transfer), so authors can see what is missing.

A skill that has templates should have at least one `apply` and one `transfer` template, because
the ladder asks for those roles at levels 4 and 5 and hand-authored items alone do not scale.
Gaps are warnings (content grows gradually), shown by `content validate` and
`python -m app.content coverage <root>`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.content.schema import Item, ItemTemplate

SCALED_ROLES = ("apply", "transfer")


@dataclass(frozen=True)
class RoleCount:
    templates: int = 0
    items: int = 0


def role_coverage(
    templates: list[ItemTemplate], items: list[Item]
) -> dict[str, dict[str, RoleCount]]:
    """skill id -> role -> how many templates and items exist (generated items included)."""
    table: dict[str, dict[str, list[int]]] = {}
    for template in templates:
        counts = table.setdefault(template.skill_id, {}).setdefault(template.role.value, [0, 0])
        counts[0] += 1
    for item in items:
        for skill in item.skill_ids[:1]:
            counts = table.setdefault(skill, {}).setdefault(item.role.value, [0, 0])
            counts[1] += 1
    return {
        skill: {role: RoleCount(*pair) for role, pair in roles.items()}
        for skill, roles in table.items()
    }


def coverage_gaps(templates: list[ItemTemplate], items: list[Item]) -> list[str]:
    """One line per skill that has templates but none for an apply or transfer role."""
    table = role_coverage(templates, items)
    skills = sorted({t.skill_id for t in templates})
    gaps: list[str] = []
    for skill in skills:
        roles = table.get(skill, {})
        missing = [r for r in SCALED_ROLES if roles.get(r, RoleCount()).templates == 0]
        if missing:
            gaps.append(f"{skill} has no {' or '.join(missing)} template")
    return gaps


def format_coverage(templates: list[ItemTemplate], items: list[Item]) -> str:
    table = role_coverage(templates, items)
    roles = ("procedure", "recall", "explain", "apply", "transfer")
    lines = ["skill".ljust(44) + "".join(r[:9].ljust(11) for r in roles) + "(templates/items)"]
    for skill in sorted(table):
        cells = ""
        for role in roles:
            count = table[skill].get(role, RoleCount())
            cells += f"{count.templates}/{count.items}".ljust(11)
        lines.append(skill.ljust(44) + cells)
    gaps = coverage_gaps(templates, items)
    lines.append("")
    lines.extend(f"GAP: {gap}" for gap in gaps)
    lines.append(f"{len(gaps)} skill(s) with a template-role gap")
    return "\n".join(lines)
