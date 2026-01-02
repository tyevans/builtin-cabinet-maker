"""Section spec layout strategy for custom section configurations.

This strategy generates cabinets with explicitly specified section widths
and per-section shelf counts using generate_cabinet_from_specs().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cabinets.domain.components.results import HardwareItem
    from cabinets.domain.entities import Cabinet, Wall
    from cabinets.domain.section_resolver import SectionSpec
    from cabinets.domain.services.layout_calculator import LayoutParameters

# Type alias - we need Any at runtime to avoid protocol mismatches
LayoutCalculatorType = Any


class SectionSpecLayoutStrategy:
    """Strategy for generating cabinets with custom section specifications.

    Uses generate_cabinet_from_specs() which allows:
    - Fixed or "fill" widths for each section
    - Different shelf counts per section
    - Per-section depth overrides
    - Zone configurations for decorative elements

    This strategy is selected when section_specs are provided.
    """

    def __init__(
        self,
        layout_calculator: LayoutCalculatorType,
        section_specs: list["SectionSpec"],
    ) -> None:
        """Initialize with a layout calculator and section specifications.

        Args:
            layout_calculator: Service for generating cabinet layouts.
            section_specs: List of section specifications with widths and shelf counts.
        """
        self._layout_calculator = layout_calculator
        self._section_specs = section_specs

    def execute(
        self,
        wall: "Wall",
        layout_params: "LayoutParameters",
        zone_configs: dict[str, dict | None] | None = None,
    ) -> tuple["Cabinet", list["HardwareItem"]]:
        """Execute the section spec layout generation.

        Generates a cabinet with sections according to the provided specifications.

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
        return self._layout_calculator.generate_cabinet_from_specs(
            wall=wall,
            params=layout_params,
            section_specs=self._section_specs,
            zone_configs=zone_configs,
        )


__all__ = [
    "SectionSpecLayoutStrategy",
]
