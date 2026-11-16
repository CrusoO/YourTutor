"""Subject lanes. Each lane owns its own module and registers through app.factory.registry."""

from app.factory.lanes import maths  # noqa: F401  (registers lane maths_c10)
from app.factory.lanes import physics  # noqa: F401  (registers the physics lane)
