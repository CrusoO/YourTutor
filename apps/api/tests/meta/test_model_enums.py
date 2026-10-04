from __future__ import annotations

import enum
import inspect

import pydantic

from app.db import models


def test_models_do_not_enum_locales_or_curricula() -> None:
    for name, obj in inspect.getmembers(models):
        if not inspect.isclass(obj):
            continue
        if issubclass(obj, enum.Enum) and obj is not enum.Enum:
            members = {m.value for m in obj}
            if members & {"en", "ne", "as", "bhutan", "seba"}:
                raise AssertionError(f"enum {name} enumerates locales or curricula")
        if issubclass(obj, pydantic.BaseModel) and obj is not pydantic.BaseModel:
            for field_name, field in obj.model_fields.items():
                if field_name in {"board", "locale", "home_language", "exam_language", "curriculum_id"}:
                    inner = field.annotation
                    if inspect.isclass(inner) and issubclass(inner, enum.Enum):
                        raise AssertionError(f"{name}.{field_name} uses Enum")
