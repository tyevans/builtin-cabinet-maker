"""Bay alcove layout service for FRD-23 Bay Window Alcove Built-ins.

This service orchestrates cabinet placement within a bay alcove by:
1. Classifying each wall into placement zones (under_window, full_height, filler)
2. Determining cabinet dimensions for each zone
3. Assigning component types (windowseat.storage vs standard)
4. Managing filler panel requirements for narrow walls
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from .radial_ceiling_service import RadialCeilingService

if TYPE_CHECKING:
    from ..value_objects import BayAlcoveConfig


class ZoneType(str, Enum):
    """Types of placement zones in a bay alcove.

    Defines the different types of zones that can exist along bay walls,
    each requiring different treatment during cabinet generation.

    Attributes:
        UNDER_WINDOW: Storage below window sill (typically window seat).
        FULL_HEIGHT: Full height cabinet (no window present).
        ABOVE_WINDOW: Storage above window head (not yet implemented).
        FILLER: Too narrow for cabinet, requires filler panel.
    """

    UNDER_WINDOW = "under_window"
    FULL_HEIGHT = "full_height"
    ABOVE_WINDOW = "above_window"
    FILLER = "filler"


@dataclass
class WallZone:
    """Describes a cabinet/filler zone on a bay wall.

    Contains all information needed to generate a cabinet or filler panel
    for a specific wall segment in the bay alcove.

    Attributes:
        wall_index: Zero-based index of the wall segment.
        zone_type: Type of zone (under_window, full_height, filler).
        height: Cabinet height for this zone in inches.
        width: Wall width in inches.
        depth: Cabinet depth in inches.
        angle: Wall angle relative to start in degrees.
        window_sill: Window sill height if present, None otherwise.
        window_head: Window head height if present, None otherwise.
        use_window_seat: Whether to use windowseat.storage component.
        filler_treatment: Treatment for filler panels ("panel", "trim", "none").
    """

    wall_index: int
    zone_type: ZoneType
    height: float
    width: float
    depth: float
    angle: float
    window_sill: float | None
    window_head: float | None
    use_window_seat: bool
    filler_treatment: str


class BayAlcoveLayoutService:
    """Service for calculating cabinet placement in bay alcoves.

    This service takes a BayAlcoveConfig and determines:
    1. Zone type for each wall (under_window, full_height, filler)
    2. Cabinet dimensions for each zone
    3. Component assignments (windowseat.storage vs standard)
    4. Filler panel requirements for narrow walls

    The service integrates with RadialCeilingService to properly calculate
    ceiling heights and wall positions for non-rectangular bay geometries.

    Example:
        >>> from cabinets.application.config import load_config, config_to_bay_alcove
        >>> config = load_config("bay-window.json")
        >>> bay_config = config_to_bay_alcove(config)
        >>> service = BayAlcoveLayoutService(bay_config)
        >>> zones = service.classify_wall_zones()
        >>> for zone in zones:
        ...     print(f"Wall {zone.wall_index}: {zone.zone_type.value}")
    """

    def __init__(self, bay_config: "BayAlcoveConfig") -> None:
        """Initialize the bay alcove layout service.

        Args:
            bay_config: Bay alcove configuration from config adapter.
        """
        self.bay_config = bay_config
        self.ceiling_service = RadialCeilingService(bay_config)
        self._zones: list[WallZone] | None = None

    def classify_wall_zones(self) -> list[WallZone]:
        """Classify each wall into placement zones.

        Algorithm:
        1. For each wall, check if width < min_cabinet_width -> FILLER
        2. If wall has window -> UNDER_WINDOW zone
        3. If no window -> FULL_HEIGHT zone
        4. Calculate heights based on zone type and ceiling geometry

        Returns:
            List of WallZone objects describing each wall's classification.
        """
        if self._zones is not None:
            return self._zones

        zones: list[WallZone] = []
        wall_segments = self.ceiling_service.compute_wall_positions()

        for i in range(self.bay_config.wall_count):
            wall = self.bay_config.get_wall(i)
            segment = wall_segments[i]

            wall_length = wall.get("length", 0.0)
            window = wall.get("window")

            # Determine zone type and height
            if wall_length < self.bay_config.min_cabinet_width:
                zone_type = ZoneType.FILLER
                height = self._get_filler_height(i)
            elif window is not None:
                zone_type = ZoneType.UNDER_WINDOW
                sill_height = window.get("sill_height", 18.0)
                height = sill_height - self.bay_config.sill_clearance
            else:
                zone_type = ZoneType.FULL_HEIGHT
                height = self.ceiling_service.get_cabinet_height_for_wall(i)

            # Extract window dimensions if present
            window_sill: float | None = None
            window_head: float | None = None
            if window is not None:
                window_sill = window.get("sill_height")
                window_head = window.get("head_height")

            # Determine depth (use bay_depth or default)
            depth = self.bay_config.bay_depth if self.bay_config.bay_depth else 16.0

            zones.append(
                WallZone(
                    wall_index=i,
                    zone_type=zone_type,
                    height=height,
                    width=wall_length,
                    depth=depth,
                    angle=segment.angle,
                    window_sill=window_sill,
                    window_head=window_head,
                    use_window_seat=zone_type == ZoneType.UNDER_WINDOW,
                    filler_treatment=self.bay_config.filler_treatment,
                )
            )

        self._zones = zones
        return zones

    def get_cabinet_zones(self) -> list[WallZone]:
        """Return only zones that get cabinets (not fillers).

        Filters out filler zones, returning only zones where actual
        cabinets (window seats or full-height cabinets) will be placed.

        Returns:
            List of WallZone objects that will receive cabinets.
        """
        return [z for z in self.classify_wall_zones() if z.zone_type != ZoneType.FILLER]

    def get_filler_zones(self) -> list[WallZone]:
        """Return only filler zones.

        Filters to return only zones that are too narrow for cabinets
        and will receive filler panels instead.

        Returns:
            List of WallZone objects that will receive filler panels.
        """
        return [z for z in self.classify_wall_zones() if z.zone_type == ZoneType.FILLER]

    def get_component_config(self, zone: WallZone) -> dict[str, Any]:
        """Get component configuration for a zone.

        Returns a configuration dictionary suitable for passing to
        a component's generate() method.

        Args:
            zone: The WallZone to get configuration for.

        Returns:
            Configuration dictionary with component_type and relevant options.
        """
        if zone.zone_type == ZoneType.FILLER:
            return {
                "component_type": "filler.mullion",
                "style": "flat",
            }
        elif zone.zone_type == ZoneType.UNDER_WINDOW:
            return {
                "component_type": "windowseat.storage",
                "seat_height": zone.height,
                "access_type": "hinged_top",
                "edge_treatment": "eased",
            }
        else:  # FULL_HEIGHT or ABOVE_WINDOW
            return {
                "component_type": "cabinet.basic",
                "height": zone.height,
            }

    def _get_filler_height(self, wall_index: int) -> float:
        """Get height for filler panel based on adjacent zones.

        For filler panels, we want to match the height of adjacent
        cabinets when possible. Falls back to edge_height if no
        adjacent cabinets exist.

        Args:
            wall_index: Index of the filler wall.

        Returns:
            Height in inches for the filler panel.
        """
        # Try to match adjacent cabinet heights
        wall_count = self.bay_config.wall_count

        # Check previous wall
        if wall_index > 0:
            prev_wall = self.bay_config.get_wall(wall_index - 1)
            prev_length = prev_wall.get("length", 0.0)
            if prev_length >= self.bay_config.min_cabinet_width:
                # Previous wall has a cabinet, get its height
                prev_window = prev_wall.get("window")
                if prev_window is not None:
                    return (
                        prev_window.get("sill_height", 18.0)
                        - self.bay_config.sill_clearance
                    )
                return self.ceiling_service.get_cabinet_height_for_wall(wall_index - 1)

        # Check next wall
        if wall_index < wall_count - 1:
            next_wall = self.bay_config.get_wall(wall_index + 1)
            next_length = next_wall.get("length", 0.0)
            if next_length >= self.bay_config.min_cabinet_width:
                # Next wall has a cabinet, get its height
                next_window = next_wall.get("window")
                if next_window is not None:
                    return (
                        next_window.get("sill_height", 18.0)
                        - self.bay_config.sill_clearance
                    )
                return self.ceiling_service.get_cabinet_height_for_wall(wall_index + 1)

        # Fall back to edge height
        return self.bay_config.edge_height

    def generate_layout_summary(self) -> dict[str, Any]:
        """Generate a summary of the bay alcove layout.

        Creates a comprehensive summary suitable for CLI output,
        debugging, or serialization to JSON.

        Returns:
            Dictionary with wall count, zone counts, detailed zone
            information, and apex point coordinates.
        """
        zones = self.classify_wall_zones()
        apex = self.ceiling_service.compute_apex_point()

        return {
            "wall_count": self.bay_config.wall_count,
            "bay_type": self.bay_config.bay_type,
            "cabinet_zones": len(self.get_cabinet_zones()),
            "filler_zones": len(self.get_filler_zones()),
            "zones": [
                {
                    "wall_index": z.wall_index,
                    "zone_type": z.zone_type.value,
                    "height": z.height,
                    "width": z.width,
                    "depth": z.depth,
                    "angle": z.angle,
                    "has_window": z.window_sill is not None,
                    "use_window_seat": z.use_window_seat,
                    "filler_treatment": z.filler_treatment,
                }
                for z in zones
            ],
            "apex": {
                "x": apex.x,
                "y": apex.y,
                "z": apex.z,
            },
            "edge_height": self.bay_config.edge_height,
            "min_cabinet_width": self.bay_config.min_cabinet_width,
        }

    def invalidate_cache(self) -> None:
        """Invalidate cached zone classifications.

        Call this method if the bay configuration has been modified
        and zones need to be reclassified.
        """
        self._zones = None
        self.ceiling_service.invalidate_cache()
