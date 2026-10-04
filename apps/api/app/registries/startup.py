"""Fail-fast validation of registry configuration at API startup."""

from __future__ import annotations

import re

from app.config import settings
from app.registries.loaders import (
    JurisdictionProfile,
    RegistryLoadError,
    load_all_curricula,
    load_jurisdiction_profile,
)
from app.registries.paths import config_dir

_PROFILE_ID = re.compile(r"^[a-z0-9_]+$")


def available_jurisdiction_profiles() -> list[str]:
    folder = config_dir() / "jurisdictions"
    return sorted(path.stem for path in folder.glob("*.yaml")) if folder.is_dir() else []


def deployment_jurisdiction_profile(profile_id: str | None = None) -> JurisdictionProfile:
    """The profile selected by `JURISDICTION_PROFILE`; unknown ids raise `RegistryLoadError`."""
    wanted = profile_id if profile_id is not None else settings.jurisdiction_profile
    if not _PROFILE_ID.match(wanted) or wanted not in available_jurisdiction_profiles():
        raise RegistryLoadError(
            f"unknown JURISDICTION_PROFILE {wanted!r}; "
            f"available: {', '.join(available_jurisdiction_profiles()) or 'none'}"
        )
    return load_jurisdiction_profile(wanted)


def validate_startup_config() -> None:
    deployment_jurisdiction_profile()
    known = set(available_jurisdiction_profiles())
    for curriculum in load_all_curricula().values():
        if curriculum.jurisdiction_profile not in known:
            raise RegistryLoadError(
                f"curriculum {curriculum.id!r} names unknown jurisdiction profile "
                f"{curriculum.jurisdiction_profile!r}"
            )
