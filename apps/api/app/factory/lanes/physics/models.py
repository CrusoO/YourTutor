"""All physics models of the lane, by id."""

from __future__ import annotations

from app.factory.lanes.physics.elec_models import ELEC_MODELS
from app.factory.lanes.physics.light_models import LIGHT_MODELS
from app.factory.lanes.physics.model import Model

ALL_MODELS: dict[str, Model] = {**ELEC_MODELS, **LIGHT_MODELS}
