"""Subject lanes. Each lane owns its own module and registers through app.factory.registry."""

from app.factory.lanes import (
    chemistry,  # noqa: F401  (registers the chemistry lane)
    maths,  # noqa: F401  (registers lane maths_c10)
    physics,  # noqa: F401  (registers the physics lane)
)
