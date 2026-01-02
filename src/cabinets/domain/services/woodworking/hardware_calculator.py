"""Hardware calculation service.

This module provides HardwareCalculator for aggregating hardware
requirements for cabinet construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.components.results import HardwareItem
from cabinets.domain.value_objects import JointType, MaterialType

from .constants import (
    BACK_PANEL_SCREW_SPACING,
    BACK_PANEL_SCREW_SPEC,
    BISCUIT_SPEC_20,
    CASE_SCREW_SPACING,
    CASE_SCREW_SPEC,
    DOWEL_SPEC,
    POCKET_SCREW_COARSE_NOTE,
    POCKET_SCREW_FINE_NOTE,
    POCKET_SCREW_SPEC,
)
from .models import ConnectionJoinery, HardwareList

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet


class HardwareCalculator:
    """Service for calculating hardware requirements.

    Aggregates fastener requirements for case assembly, back panel
    attachment, and joinery-specific hardware.
    """

    def calculate_hardware(
        self,
        cabinet: "Cabinet",
        joinery: list[ConnectionJoinery],
        include_overage: bool = True,
        overage_percent: float = 10.0,
    ) -> HardwareList:
        """Calculate all hardware needed for cabinet construction.

        Aggregates fastener requirements for case assembly, back panel
        attachment, and joinery-specific hardware. Optionally adds
        overage for waste and mistakes.

        Args:
            cabinet: Cabinet to analyze.
            joinery: List of ConnectionJoinery from joinery calculation.
            include_overage: Whether to add overage percentage.
            overage_percent: Percentage of overage to add (default 10%).

        Returns:
            HardwareList with all hardware items and quantities.
        """
        items: list[HardwareItem] = []

        # Case assembly screws
        items.extend(self._case_screws(cabinet))

        # Back panel attachment
        items.extend(self._back_panel_screws(cabinet))

        # Joinery-specific fasteners
        items.extend(self._joinery_fasteners(cabinet, joinery))

        # Shelf-related fasteners (placeholder for future component integration)
        items.extend(self._shelf_fasteners(cabinet))

        # Aggregate all items by name
        hardware_list = HardwareList(items=tuple(items))
        aggregated = HardwareList.aggregate(hardware_list)

        if include_overage:
            aggregated = aggregated.with_overage(overage_percent)

        return aggregated

    def _case_screws(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Calculate screws for case assembly.

        Screws are used to attach top and bottom panels to side panels,
        and to attach dividers. Uses standard spacing of 8" between screws.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of HardwareItem for case screws.
        """
        items: list[HardwareItem] = []

        # Calculate perimeter of case (where sides meet top/bottom)
        # Top and bottom each connect to both sides
        cabinet_depth = cabinet.depth

        # Screws for top-to-sides (2 sides x screws along depth)
        top_screws_per_side = max(2, int(cabinet_depth / CASE_SCREW_SPACING) + 1)
        top_screws = top_screws_per_side * 2  # Both sides

        # Screws for bottom-to-sides (same as top)
        bottom_screws = top_screws_per_side * 2

        # Screws for dividers (each divider connects to top and bottom)
        num_dividers = max(0, len(cabinet.sections) - 1)
        divider_screws = 0
        if num_dividers > 0:
            screws_per_divider_edge = max(
                2, int(cabinet_depth / CASE_SCREW_SPACING) + 1
            )
            divider_screws = (
                num_dividers * screws_per_divider_edge * 2
            )  # Top and bottom

        total_case_screws = top_screws + bottom_screws + divider_screws

        if total_case_screws > 0:
            items.append(
                HardwareItem(
                    name=CASE_SCREW_SPEC,
                    quantity=total_case_screws,
                    sku=None,
                    notes="Case assembly",
                )
            )

        return items

    def _back_panel_screws(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Calculate screws for back panel attachment.

        Back panel is attached around the perimeter with standard spacing
        of 6" between screws.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of HardwareItem for back panel screws.
        """
        items: list[HardwareItem] = []

        # Calculate perimeter of back panel
        width = cabinet.width
        height = cabinet.height

        # Screws along top and bottom edges
        horizontal_screws = max(2, int(width / BACK_PANEL_SCREW_SPACING) + 1) * 2

        # Screws along left and right edges (excluding corners already counted)
        vertical_screws = max(0, int(height / BACK_PANEL_SCREW_SPACING) - 1) * 2

        # Add screws along dividers if any
        num_dividers = max(0, len(cabinet.sections) - 1)
        divider_screws = 0
        if num_dividers > 0:
            screws_per_divider = max(2, int(height / BACK_PANEL_SCREW_SPACING))
            divider_screws = num_dividers * screws_per_divider

        total_back_screws = horizontal_screws + vertical_screws + divider_screws

        if total_back_screws > 0:
            items.append(
                HardwareItem(
                    name=BACK_PANEL_SCREW_SPEC,
                    quantity=total_back_screws,
                    sku=None,
                    notes="Back panel attachment",
                )
            )

        return items

    def _joinery_fasteners(
        self,
        cabinet: "Cabinet",
        joinery: list[ConnectionJoinery],
    ) -> list[HardwareItem]:
        """Calculate fasteners for joinery connections.

        Different joint types require different fasteners:
        - Pocket screw: Pocket screws
        - Dowel: Dowel pins
        - Biscuit: Biscuits
        - Dado/Rabbet: No additional fasteners (glued joints)

        Args:
            cabinet: Cabinet to analyze.
            joinery: List of ConnectionJoinery from joinery calculation.

        Returns:
            List of HardwareItem for joinery-specific fasteners.
        """
        items: list[HardwareItem] = []

        # Count fasteners by type
        pocket_screw_count = 0
        dowel_count = 0
        biscuit_count = 0

        for connection in joinery:
            joint = connection.joint

            if joint.joint_type == JointType.POCKET_SCREW:
                # Count based on positions
                pocket_screw_count += len(joint.positions)

            elif joint.joint_type == JointType.DOWEL:
                # Count based on positions
                dowel_count += len(joint.positions)

            elif joint.joint_type == JointType.BISCUIT:
                # Count based on positions
                biscuit_count += len(joint.positions)

            # Dado and rabbet joints don't need additional fasteners

        # Add pocket screws if any
        if pocket_screw_count > 0:
            # Determine thread type based on material
            is_hardwood = cabinet.material.material_type == MaterialType.SOLID_WOOD
            notes = POCKET_SCREW_FINE_NOTE if is_hardwood else POCKET_SCREW_COARSE_NOTE

            items.append(
                HardwareItem(
                    name=POCKET_SCREW_SPEC,
                    quantity=pocket_screw_count,
                    sku=None,
                    notes=notes,
                )
            )

        # Add dowels if any
        if dowel_count > 0:
            items.append(
                HardwareItem(
                    name=DOWEL_SPEC,
                    quantity=dowel_count,
                    sku=None,
                    notes="Joinery alignment",
                )
            )

        # Add biscuits if any
        if biscuit_count > 0:
            # Use #20 for panels, #10 for narrow pieces
            items.append(
                HardwareItem(
                    name=BISCUIT_SPEC_20,
                    quantity=biscuit_count,
                    sku=None,
                    notes="Panel joinery",
                )
            )

        return items

    def _shelf_fasteners(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Calculate hardware for shelf support.

        For adjustable shelves, this includes shelf pins.
        For fixed shelves with dado joints, no additional hardware is needed.

        Note: This is called separately from calculate_hardware() since
        shelf components already generate their own hardware via the
        component registry pattern.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of HardwareItem for shelf support.
        """
        # Currently, shelf components generate their own hardware
        # This method is a placeholder for future centralization
        return []
