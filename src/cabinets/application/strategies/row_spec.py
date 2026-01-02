"""Row spec layout strategy for multi-row cabinet configurations.

This strategy generates cabinets with vertically stacked rows using
generate_cabinet_from_row_specs().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cabinets.domain.components.results import HardwareItem
    from cabinets.domain.entities import Cabinet, Wall
    from cabinets.domain.section_resolver import RowSpec
    from cabinets.domain.services.layout_calculator import LayoutParameters

# Type alias - we need Any at runtime to avoid protocol mismatches
LayoutCalculatorType = Any


class RowSpecLayoutStrategy:
    """Strategy for generating cabinets with vertically stacked rows.

    Uses generate_cabinet_from_row_specs() which supports:
    - Multiple rows stacked from bottom to top
    - Fixed or "fill" heights for each row
    - Horizontal sections within each row
    - Zone configurations for decorative elements
    - Horizontal dividers between rows

    This strategy is selected when row_specs are provided.
    """

    def __init__(
        self,
        layout_calculator: LayoutCalculatorType,
        row_specs: list["RowSpec"],
    ) -> None:
        """Initialize with a layout calculator and row specifications.

        Args:
            layout_calculator: Service for generating cabinet layouts.
            row_specs: List of row specifications with heights and section specs.
        """
        self._layout_calculator = layout_calculator
        self._row_specs = row_specs

    def execute(
        self,
        wall: "Wall",
        layout_params: "LayoutParameters",
        zone_configs: dict[str, dict | None] | None = None,
    ) -> tuple["Cabinet", list["HardwareItem"]]:
        """Execute the row spec layout generation.

        Generates a cabinet with rows according to the provided specifications.

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
        return self._layout_calculator.generate_cabinet_from_row_specs(
            wall=wall,
            params=layout_params,
            row_specs=self._row_specs,
            zone_configs=zone_configs,
        )


__all__ = [
    "RowSpecLayoutStrategy",
]
