"""All Class 12 physics models of the lane, by id (importing the part files registers them)."""

from __future__ import annotations

from app.factory.lanes.physics.model import Model
from app.factory.lanes.physics_c12 import (
    m_electric,  # noqa: F401
    m_magnetic,  # noqa: F401
    m_optics_modern,  # noqa: F401
)
from app.factory.lanes.physics_c12.kit import REGISTRY

ALL_MODELS: dict[str, Model] = REGISTRY
