"""Subject lanes. Each lane owns its own module and registers through app.factory.registry."""

from app.factory.lanes import physics  # noqa: F401  (registers the physics lane)
