from __future__ import annotations

from dataclasses import asdict, dataclass

from app.registries.loaders import CurriculumSpec, book_for_grade


@dataclass(frozen=True)
class ContextKey:
    curriculum_id: str
    book_id: str
    chapter_id: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def context_key_for_student(
    *,
    curriculum_id: str,
    book_id: str | None,
    grade: int,
    current_chapter_id: str | None,
    spec: CurriculumSpec,
) -> ContextKey:
    book = None
    if book_id:
        book = next((b for b in spec.books if b.id == book_id), None)
    if book is None:
        book = book_for_grade(spec, grade)
    if book is None:
        raise ValueError(f"no book for curriculum {curriculum_id} grade {grade}")
    chapter_id = current_chapter_id or book.default_chapter_id
    return ContextKey(curriculum_id=curriculum_id, book_id=book.id, chapter_id=chapter_id)
