from __future__ import annotations

from sqlalchemy import JSON, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY


class TextArray(TypeDecorator):
    """Postgres text[]; JSON list on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Text()))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return list(value)
