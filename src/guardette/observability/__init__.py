from fastapi import FastAPI

from guardette.logging import setup_logging
from guardette.observability.config import ObservabilityConfig
from guardette.observability.events import Observability
from guardette.observability.middleware import ObservabilityMiddleware


def configure_observability(app: FastAPI, config: ObservabilityConfig | None = None) -> Observability:
    if hasattr(app.state, "observability"):
        return app.state.observability

    config = config or ObservabilityConfig.from_env()
    setup_logging(config)
    observability = Observability(config)
    app.state.observability = observability

    if config.active:
        app.add_middleware(ObservabilityMiddleware, observability=observability)

    return observability


__all__ = ["ObservabilityConfig", "configure_observability"]
