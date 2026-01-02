"""Uniform layout strategy for equal-width sections.

This strategy generates cabinets with equal-width sections and uniform
shelf counts, matching the original generate_cabinet() behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cabinets.domain.components.results import HardwareItem
    from cabinets.domain.entities import Cabinet, Wall
    from cabinets.domain.services.layout_calculator import LayoutParameters

# Type alias - we need Any at runtime to avoid protocol mismatches
# The concrete LayoutCalculator type is used but has methods not on protocol
LayoutCalculatorType = Any


class UniformLayoutStrategy:
    """Strategy for generating cabinets with uniform sections.

    Uses the legacy generate_cabinet() method which creates equal-width
    sections with the same number of shelves in each section.

    This is the simplest layout approach and is used when neither
    section_specs nor row_specs are provided.
    """

    def __init__(self, layout_calculator: LayoutCalculatorType) -> None:
        """Initialize with a layout calculator.

        Args:
            layout_calculator: Service for generating cabinet layouts.
        """
        self._layout_calculator = layout_calculator

    def execute(
        self,
        wall: "Wall",
        layout_params: "LayoutParameters",
        zone_configs: dict[str, dict | None] | None = None,
    ) -> tuple["Cabinet", list["HardwareItem"]]:
        """Execute the uniform layout generation.

        Generates a cabinet with equal-width sections and uniform shelf counts.
        Note: The uniform layout does not support zone configurations.

        Args:
            wall: Wall dimensions constraining the cabinet.
            layout_params: Layout parameters including section count and shelves.
            zone_configs: Zone configurations (not used by uniform layout).

        Returns:
            A tuple of (Cabinet, list[HardwareItem]). Hardware list is always
            empty for uniform layouts as this uses the legacy generation path.
        """
        cabinet = self._layout_calculator.generate_cabinet(wall, layout_params)
        # Uniform layout does not generate hardware items
        hardware: list["HardwareItem"] = []
        return cabinet, hardware


__all__ = [
    "UniformLayoutStrategy",
]
