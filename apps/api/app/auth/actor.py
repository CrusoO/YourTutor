from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    role: str
    user_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    email: str | None = None
    checkpoint_id: str | None = None
    checkpoint_form: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_parent(self) -> bool:
        return self.role == "parent"

    @property
    def is_teacher(self) -> bool:
        return self.role == "teacher"

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_comparison(self) -> bool:
        return self.role == "comparison"
