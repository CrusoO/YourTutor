"""Pure checks that overlay `section_map` entries resolve against curriculum sections."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol

from app.registries.loaders import CurriculumSpec


class OverlayLike(Protocol):
    id: str
    curriculum_id: str
    skill_ids: list[str]
    section_map: dict[str, list[str]]


def overlay_curriculum_errors(
    overlays: Iterable[OverlayLike],
    curricula: Mapping[str, CurriculumSpec],
) -> list[str]:
    return [
        f"overlay {overlay.id} names unknown curriculum {overlay.curriculum_id!r}"
        for overlay in overlays
        if overlay.curriculum_id not in curricula
    ]


def section_map_errors(
    overlays: Iterable[OverlayLike],
    curricula: Mapping[str, CurriculumSpec],
) -> list[str]:
    """Errors for unresolved section keys, unknown skills, and chapters missing a mapping.

    Section ids are `{chapter_id}.{key}`; an overlay's `section_map` is keyed by `key` and is
    shared by every chapter that uses the overlay.
    """
    errors: list[str] = []
    chapters_by_overlay: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    seen_ids: set[str] = set()
    for curriculum in curricula.values():
        for book in curriculum.books:
            for chapter in book.chapters:
                keys = tuple(section.key for section in chapter.sections)
                chapters_by_overlay.setdefault(chapter.overlay_id, []).append((chapter.id, keys))
                orders = [section.order for section in chapter.sections]
                if len(set(orders)) != len(orders):
                    errors.append(f"chapter {chapter.id}: duplicate section order")
                if len(set(keys)) != len(keys):
                    errors.append(f"chapter {chapter.id}: duplicate section key")
                for section in chapter.sections:
                    if section.id in seen_ids:
                        errors.append(f"duplicate section id {section.id}")
                    seen_ids.add(section.id)
    for overlay in overlays:
        used_by = chapters_by_overlay.get(overlay.id, [])
        for key, skills in overlay.section_map.items():
            for skill_id in skills:
                if skill_id not in overlay.skill_ids:
                    errors.append(
                        f"overlay {overlay.id} section {key}: skill {skill_id} "
                        "is not in the overlay"
                    )
            for chapter_id, keys in used_by:
                if key not in keys:
                    errors.append(
                        f"overlay {overlay.id} section_map key {key!r} has no section in "
                        f"chapter {chapter_id}"
                    )
        for chapter_id, keys in used_by:
            for key in keys:
                if key not in overlay.section_map:
                    errors.append(
                        f"chapter {chapter_id} section {key!r} is missing from overlay "
                        f"{overlay.id} section_map"
                    )
    return errors
