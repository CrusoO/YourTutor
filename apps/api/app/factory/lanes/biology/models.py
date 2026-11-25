"""All biology item models of the lane, by id, and the misconception tables per area."""

from __future__ import annotations

from app.factory.lanes.biology import environment, heredity, life, reproduction
from app.factory.lanes.biology.common import Model

ALL_MODELS: dict[str, Model] = {
    **heredity.HEREDITY_MODELS,
    **environment.ENV_MODELS,
    **reproduction.REPRO_MODELS,
    **life.LIFE_MODELS,
}
MISC: dict[str, dict[str, tuple[str, str]]] = {
    "HERED": heredity.MISC,
    "ENV": environment.MISC,
    "REPRO": reproduction.MISC,
    "LIFE": life.MISC,
}
