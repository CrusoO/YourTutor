"""Subject lanes. Each lane owns its own module and registers through app.factory.registry."""

from app.factory.lanes import (
    maths,  # noqa: F401  (registers lane maths_c10)
    maths_c12,  # noqa: F401  (registers lane maths_c12)
    physics,  # noqa: F401  (registers the physics lane)
)
