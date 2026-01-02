"""Layout generation strategies for cabinet creation.

This package implements the Strategy pattern for layout generation,
allowing different layout approaches to be selected at runtime.

Available Strategies:
    - UniformLayoutStrategy: Equal-width sections with uniform shelves
    - SectionSpecLayoutStrategy: Custom section widths and shelf counts
    - RowSpecLayoutStrategy: Multi-row cabinets with vertical stacking

Factory:
    - LayoutStrategyFactory: Creates the appropriate strategy based on input

Protocol:
    - LayoutStrategy: Protocol defining the strategy interface (from contracts)

Example:
    ```python
    from cabinets.application.strategies import LayoutStrategyFactory

    factory = LayoutStrategyFactory(layout_calculator)

    # Create strategy based on what specs are provided
    strategy = factory.create_strategy(section_specs=my_specs)

    # Execute the strategy
    cabinet, hardware = strategy.execute(wall, params, zone_configs)
    ```
"""

from .base import LayoutResult, LayoutStrategy
from .factory import LayoutStrategyFactory
from .row_spec import RowSpecLayoutStrategy
from .section_spec import SectionSpecLayoutStrategy
from .uniform import UniformLayoutStrategy

__all__ = [
    # Protocol and types
    "LayoutResult",
    "LayoutStrategy",
    # Factory
    "LayoutStrategyFactory",
    # Strategies
    "RowSpecLayoutStrategy",
    "SectionSpecLayoutStrategy",
    "UniformLayoutStrategy",
]
