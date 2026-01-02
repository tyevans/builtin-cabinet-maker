"""French cleat specification service.

This module provides the CleatService class for generating
French cleat cut piece specifications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...value_objects import (
    CutPiece,
    MountingSystem,
    PanelType,
)
from .config import InstallationConfig

if TYPE_CHECKING:
    from ...entities import Cabinet


class CleatService:
    """Service for generating French cleat specifications.

    Creates cut piece specifications for both the wall-mounted
    and cabinet-mounted cleats when using a French cleat mounting system.
    """

    def __init__(self, config: InstallationConfig) -> None:
        """Initialize the cleat service.

        Args:
            config: Installation configuration parameters.
        """
        self.config = config

    def generate_cleats(self, cabinet: "Cabinet") -> list[CutPiece]:
        """Generate French cleat cut pieces.

        Creates cut piece specifications for both the wall-mounted
        and cabinet-mounted cleats if the mounting system is set
        to French cleat.

        Args:
            cabinet: Cabinet to generate cleats for.

        Returns:
            List of CutPiece specifications for cleats.
            Empty list if not using French cleat system.
        """
        # Return empty list if not using French cleat system
        if self.config.mounting_system != MountingSystem.FRENCH_CLEAT:
            return []

        cleats: list[CutPiece] = []

        # Calculate cleat dimensions
        cleat_width = cabinet.width * (self.config.cleat_width_percentage / 100.0)
        cleat_height = 3.0  # Standard cleat height (before bevel)
        # cleat_thickness is same as cabinet material thickness (used for metadata)

        # Wall cleat - mounted to wall with bevel facing up and out
        wall_cleat = CutPiece(
            width=cleat_width,
            height=cleat_height,
            quantity=1,
            label="French Cleat (Wall)",
            panel_type=PanelType.NAILER,
            material=cabinet.material,
            cut_metadata={
                "bevel_angle": self.config.cleat_bevel_angle,
                "bevel_edge": "top",
                "grain_direction": "length",
                "installation_note": (
                    "Mount to wall with bevel facing up and outward. "
                    "Secure into wall studs with lag bolts."
                ),
            },
        )
        cleats.append(wall_cleat)

        # Cabinet cleat - attached to cabinet back with bevel facing down and in
        cabinet_cleat = CutPiece(
            width=cleat_width,
            height=cleat_height,
            quantity=1,
            label="French Cleat (Cabinet)",
            panel_type=PanelType.NAILER,
            material=cabinet.material,
            cut_metadata={
                "bevel_angle": self.config.cleat_bevel_angle,
                "bevel_edge": "bottom",
                "grain_direction": "length",
                "installation_note": (
                    "Attach to cabinet back with bevel facing down and inward. "
                    f'Position {self.config.cleat_position_from_top}" from cabinet top.'
                ),
            },
        )
        cleats.append(cabinet_cleat)

        return cleats
