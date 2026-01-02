"""Panel generation service for cabinet construction.

This module provides a service that generates panels from Cabinet entities,
extracting the panel generation logic from the Cabinet entity to maintain
Single Responsibility Principle.

The PanelGenerationService handles:
- Generating all structural panels (top, bottom, sides, back)
- Generating dividers (vertical and horizontal)
- Generating shelves from sections
- Generating zone panels (toe kick, crown nailer, light rail)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..value_objects import (
    CutPiece,
    PanelType,
    Position,
)

if TYPE_CHECKING:
    from ..entities import Cabinet, Panel

__all__ = ["PanelGenerationService"]


class PanelGenerationService:
    """Service for generating panels from a Cabinet entity.

    This service extracts the panel generation logic that was previously
    in the Cabinet entity, providing a cleaner separation of concerns.

    The service generates:
    - Structural panels (top, bottom, left side, right side, back)
    - Vertical dividers between sections
    - Horizontal dividers between rows (for multi-row cabinets)
    - Shelves from all sections
    - Additional panels from sections (doors, drawer fronts, etc.)
    - Zone panels (toe kick, crown nailer, light rail)

    Example:
        >>> from cabinets.domain.services import PanelGenerationService
        >>> from cabinets.domain.entities import Cabinet
        >>> from cabinets.domain.value_objects import MaterialSpec
        >>> cabinet = Cabinet(
        ...     width=48.0, height=84.0, depth=12.0,
        ...     material=MaterialSpec.standard_3_4()
        ... )
        >>> service = PanelGenerationService()
        >>> panels = service.get_all_panels(cabinet)
    """

    def get_all_panels(self, cabinet: Cabinet) -> list[Panel]:
        """Get all panels that make up the given cabinet.

        Generates the complete list of panels for a cabinet including:
        - Top and bottom panels
        - Left and right side panels
        - Back panel
        - Vertical dividers between sections
        - Horizontal dividers between rows
        - Shelves from all sections
        - Additional section panels (doors, drawers)
        - Zone panels (toe kick, crown, light rail)

        Args:
            cabinet: The cabinet to generate panels for.

        Returns:
            List of Panel objects representing all parts of the cabinet.
        """
        # Import here to avoid circular imports at module load time
        from ..entities import Panel

        panels: list[Panel] = []

        # Top panel - spans full width, depth is interior depth
        panels.append(
            Panel(
                panel_type=PanelType.TOP,
                width=cabinet.width,
                height=cabinet.interior_depth,
                material=cabinet.material,
                position=Position(0, cabinet.height - cabinet.material.thickness),
            )
        )

        # Bottom panel - shortened if there's a toe kick zone
        # With a toe kick, the bottom stops at the setback, leaving room for the toe kick panel
        bottom_depth = cabinet.interior_depth
        if cabinet.base_zone and cabinet.base_zone.get("zone_type") == "toe_kick":
            toe_kick_setback = cabinet.base_zone.get("setback", 3.0)
            bottom_depth = cabinet.interior_depth - toe_kick_setback
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=cabinet.width,
                height=bottom_depth,
                material=cabinet.material,
                position=Position(0, 0),
            )
        )

        # Left side panel - extends from floor to top (full height minus top panel)
        # Side panels provide structural support and extend into toe kick area
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=cabinet.interior_depth,
                height=cabinet.side_panel_height,
                material=cabinet.material,
                position=Position(0, 0),  # Starts at floor
            )
        )

        # Right side panel - same as left
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=cabinet.interior_depth,
                height=cabinet.side_panel_height,
                material=cabinet.material,
                position=Position(cabinet.width - cabinet.material.thickness, 0),
            )
        )

        # Back panel - full width and height, thinner material
        assert cabinet.back_material is not None
        panels.append(
            Panel(
                panel_type=PanelType.BACK,
                width=cabinet.width,
                height=cabinet.height,
                material=cabinet.back_material,
                position=Position(0, 0),
            )
        )

        # Vertical dividers between sections (within each row)
        # For multi-row cabinets, dividers only span the row height, not full cabinet
        for i in range(len(cabinet.sections) - 1):
            section = cabinet.sections[i]
            next_section = cabinet.sections[i + 1]
            # Only add divider if adjacent sections are in the same row
            # (they would have the same y position)
            if abs(section.position.y - next_section.position.y) < 0.001:
                panels.append(
                    Panel(
                        panel_type=PanelType.DIVIDER,
                        width=cabinet.interior_depth,
                        height=section.height,  # Use section height, not interior_height
                        material=cabinet.material,
                        position=Position(
                            section.position.x + section.width, section.position.y
                        ),
                    )
                )

        # Horizontal dividers between rows (for multi-row cabinets)
        if cabinet.row_heights:
            # Start above toe kick (if present) and bottom panel
            current_y = cabinet.base_zone_height + cabinet.material.thickness
            for i, row_height in enumerate(cabinet.row_heights[:-1]):  # Skip last row
                current_y += row_height  # Move to top of current row
                panels.append(
                    Panel(
                        panel_type=PanelType.HORIZONTAL_DIVIDER,
                        width=cabinet.interior_width,
                        height=cabinet.interior_depth,
                        material=cabinet.material,
                        position=Position(cabinet.material.thickness, current_y),
                    )
                )
                current_y += cabinet.material.thickness  # Account for divider thickness

        # Shelves from all sections
        for section in cabinet.sections:
            for shelf in section.shelves:
                panels.append(shelf.to_panel())

        # Additional panels from sections (doors, drawer fronts, etc.)
        for section in cabinet.sections:
            for panel in section.panels:
                panels.append(panel)

        # Zone panels (toe kick, crown nailer, light rail)
        panels.extend(self.get_zone_panels(cabinet))

        return panels

    def get_zone_panels(self, cabinet: Cabinet) -> list[Panel]:
        """Generate panels for decorative zones (toe kick, crown, light rail).

        Zone panels are special panels that serve specific purposes:
        - Toe kick: Recessed panel at the bottom front for foot clearance
        - Crown nailer: Strip at top back for mounting crown molding
        - Light rail: Strip at bottom front for concealing under-cabinet lights

        Args:
            cabinet: The cabinet to generate zone panels for.

        Returns:
            List of Panel objects for the configured zones.
        """
        # Import here to avoid circular imports at module load time
        from ..entities import Panel

        zone_panels: list[Panel] = []

        # Toe kick panel - recessed panel at bottom front
        if cabinet.base_zone and cabinet.base_zone.get("zone_type") == "toe_kick":
            toe_kick_height = cabinet.base_zone.get("height", 3.5)
            toe_kick_setback = cabinet.base_zone.get("setback", 3.0)
            # Toe kick is positioned at the front, recessed by setback
            zone_panels.append(
                Panel(
                    panel_type=PanelType.TOE_KICK,
                    width=cabinet.width,
                    height=toe_kick_height,
                    material=cabinet.material,
                    position=Position(0, 0),
                    metadata={
                        "zone_type": "toe_kick",
                        "setback": toe_kick_setback,
                        "location": "bottom_front_recessed",
                    },
                )
            )

        # Crown molding nailer - strip at top back for mounting crown molding
        if cabinet.crown_molding:
            crown_height = cabinet.crown_molding.get("height", 3.0)
            nailer_width = cabinet.crown_molding.get("nailer_width", 2.0)
            zone_panels.append(
                Panel(
                    panel_type=PanelType.NAILER,
                    width=cabinet.width,
                    height=nailer_width,  # Nailer depth
                    material=cabinet.material,
                    position=Position(0, cabinet.height - nailer_width),
                    metadata={
                        "zone_type": "crown_molding",
                        "zone_height": crown_height,
                        "setback": cabinet.crown_molding.get("setback", 0.75),
                        "location": "top_back",
                    },
                )
            )

        # Light rail strip - at bottom front for concealing under-cabinet lights
        if cabinet.light_rail:
            rail_height = cabinet.light_rail.get("height", 1.5)
            zone_panels.append(
                Panel(
                    panel_type=PanelType.LIGHT_RAIL,
                    width=cabinet.width,
                    height=rail_height,
                    material=cabinet.material,
                    position=Position(0, 0),
                    metadata={
                        "zone_type": "light_rail",
                        "setback": cabinet.light_rail.get("setback", 0.25),
                        "location": "bottom_front",
                    },
                )
            )

        return zone_panels

    def get_cut_list(self, cabinet: Cabinet) -> list[CutPiece]:
        """Generate a consolidated cut list for a cabinet.

        Groups identical panels together and returns a list of cut pieces
        with quantities, suitable for manufacturing.

        Args:
            cabinet: The cabinet to generate a cut list for.

        Returns:
            List of CutPiece objects with consolidated quantities.
        """
        panels = self.get_all_panels(cabinet)

        # Group identical panels together
        piece_key_to_panels: dict[tuple, list[Panel]] = {}
        for panel in panels:
            key = (
                panel.panel_type,
                round(panel.width, 3),
                round(panel.height, 3),
                panel.material.thickness,
                panel.material.material_type,
            )
            if key not in piece_key_to_panels:
                piece_key_to_panels[key] = []
            piece_key_to_panels[key].append(panel)

        # Convert to cut pieces with quantities
        cut_pieces: list[CutPiece] = []
        for panels_group in piece_key_to_panels.values():
            first_panel = panels_group[0]
            cut_pieces.append(first_panel.to_cut_piece(quantity=len(panels_group)))

        return cut_pieces
