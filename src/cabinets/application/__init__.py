"""Application layer - use cases and orchestration."""

from .commands import GenerateLayoutCommand
from .dtos import (
    CoreLayoutOutput,
    InstallationOutput,
    LayoutOutput,
    LayoutParametersInput,
    PackingOutput,
    WallInput,
    WoodworkingOutput,
)
from .factory import ServiceFactory, get_factory, reset_factory, set_factory

# Strategy exports for advanced usage
from .strategies import (
    LayoutStrategyFactory,
    RowSpecLayoutStrategy,
    SectionSpecLayoutStrategy,
    UniformLayoutStrategy,
)

__all__ = [
    "CoreLayoutOutput",
    "GenerateLayoutCommand",
    "InstallationOutput",
    "LayoutOutput",
    "LayoutParametersInput",
    "LayoutStrategyFactory",
    "PackingOutput",
    "RowSpecLayoutStrategy",
    "SectionSpecLayoutStrategy",
    "ServiceFactory",
    "UniformLayoutStrategy",
    "WallInput",
    "WoodworkingOutput",
    "get_factory",
    "reset_factory",
    "set_factory",
]
