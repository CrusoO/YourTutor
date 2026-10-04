"""Optional OpenTelemetry spans. Off unless OTEL_ENABLED is true. No PII."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.config import settings

_ALLOWED = frozenset({"component", "rule_id", "skill_id", "item_id", "action_type"})


@contextmanager
def span(name: str, **attrs: object) -> Iterator[None]:
    if not settings.otel_enabled:
        yield
        return
    try:
        from opentelemetry import trace
    except ImportError:
        yield
        return
    tracer = trace.get_tracer("yourtutor")
    safe = {key: value for key, value in attrs.items() if key in _ALLOWED}
    with tracer.start_as_current_span(name) as current:
        for key, value in safe.items():
            current.set_attribute(key, str(value))
        yield
