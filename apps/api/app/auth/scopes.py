"""The consent scopes moved to app.registries.scopes (a registry sits below auth, and
app.registries.loaders needs it). This module re-exports the same objects so every existing
`from app.auth.scopes import ...` keeps working; new code imports app.registries.scopes."""

from __future__ import annotations

from app.registries.scopes import (
    CONSENT_SCOPES,
    DEPRECATED_ALIASES,
    GUARDIAN_ONLY_SCOPES,
    NEW_SCOPES,
    SCOPE_REGISTRY,
    Scope,
    read_scopes,
    scope_error,
)

__all__ = [
    "CONSENT_SCOPES",
    "DEPRECATED_ALIASES",
    "GUARDIAN_ONLY_SCOPES",
    "NEW_SCOPES",
    "SCOPE_REGISTRY",
    "Scope",
    "read_scopes",
    "scope_error",
]
