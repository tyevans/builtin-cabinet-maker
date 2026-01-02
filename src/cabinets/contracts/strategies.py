"""Strategy protocols for layout generation.

This module defines protocol classes that establish contracts for layout
generation strategies. The Strategy pattern allows different layout generation
approaches (uniform, section specs, row specs) to be selected at runtime
without modifying the command layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cabinets.domain.components.results import HardwareItem
    from cabinets.domain.entities import Cabinet, Wall
    from cabinets.domain.services.layout_calculator import LayoutParameters


@runtime_checkable
class LayoutStrategy(Protocol):
    """Protocol for cabinet layout generation strategies.

    Implementations encapsulate specific layout generation approaches:
    - UniformLayoutStrategy: Equal-width sections with uniform shelves
    - SectionSpecLayoutStrategy: Custom section widths and shelf counts
    - RowSpecLayoutStrategy: Multi-row cabinets with vertical stacking

    Each strategy produces a Cabinet entity and associated hardware items.

    Example:
        ```python
        class RowSpecLayoutStrategy:
            def execute(
                self,
                wall: Wall,
                layout_params: LayoutParameters,
                zone_configs: dict[str, dict | None] | None = None,
            ) -> tuple[Cabinet, list[HardwareItem]]:
                # Implementation using row_specs
                ...
        ```
    """

    def execute(
        self,
        wall: "Wall",
        layout_params: "LayoutParameters",
        zone_configs: dict[str, dict | None] | None = None,
    ) -> tuple["Cabinet", list["HardwareItem"]]:
        """Execute the layout generation strategy.

        Args:
            wall: Wall dimensions constraining the cabinet.
            layout_params: Layout parameters including material specs.
            zone_configs: Optional dict with zone configurations:
                - base_zone: Toe kick zone config
                - crown_molding: Crown molding zone config
                - light_rail: Light rail zone config

        Returns:
            A tuple of (Cabinet, list[HardwareItem]) containing the cabinet
            entity with the generated layout and hardware items needed.
        """
        ...


__all__ = [
    "LayoutStrategy",
]
