"""Bay window alcove value objects (FRD-23)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import atan2, degrees, sqrt

from ._core_geometry import Point2D


class BayType(str, Enum):
    """Preset bay window configurations.

    Defines the different bay window configurations that can be used
    for alcove built-ins. Each type has different wall angles and
    facet arrangements.

    Attributes:
        THREE_WALL: Classic 3-wall bay with 45-degree angles.
        FIVE_WALL: 5-wall angled bay with 22.5-degree angles.
        BOX_BAY: 3-wall at 90-degree angles (rectangular projection).
        BOW: Curved bay approximated by multiple segments.
        CUSTOM: User-defined angles and wall configuration.
    """

    THREE_WALL = "three_wall"
    FIVE_WALL = "five_wall"
    BOX_BAY = "box_bay"
    BOW = "bow"
    CUSTOM = "custom"


class FillerTreatment(str, Enum):
    """Treatment options for mullion/narrow wall zones.

    Defines how to handle the narrow zones between bay window walls,
    such as the areas around mullions or narrow wall segments.

    Attributes:
        PANEL: Solid panel filler to close the gap.
        TRIM: Decorative trim piece to cover the gap.
        NONE: Leave the gap open/exposed.
    """

    PANEL = "panel"
    TRIM = "trim"
    NONE = "none"


@dataclass(frozen=True)
class ApexPoint:
    """Apex point for pyramidal/conical ceiling.

    Represents the highest point of a radial ceiling where all
    ceiling facets converge. Coordinates are relative to the
    bay alcove origin (typically center of bay at floor level).

    Attributes:
        x: X coordinate relative to bay origin (inches).
        y: Y coordinate relative to bay origin (inches).
        z: Height from floor (inches).
    """

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if self.z <= 0:
            raise ValueError("Apex height must be positive")

    def distance_to(self, point_x: float, point_y: float) -> float:
        """Calculate horizontal distance from apex to a point.

        Args:
            point_x: X coordinate of the target point.
            point_y: Y coordinate of the target point.

        Returns:
            Horizontal distance in inches.
        """
        return sqrt((self.x - point_x) ** 2 + (self.y - point_y) ** 2)


@dataclass(frozen=True)
class CeilingFacet:
    """A triangular ceiling facet in a radial ceiling.

    Each facet connects the apex point to a wall segment's top edge,
    forming one triangular face of the pyramidal/conical ceiling.

    Attributes:
        wall_index: Index of the wall this facet is above.
        edge_start: Point2D for left edge where facet meets wall.
        edge_end: Point2D for right edge where facet meets wall.
        edge_height: Height of wall top edge (where facet starts).
        apex: Reference to the apex point.
    """

    wall_index: int
    edge_start: Point2D
    edge_end: Point2D
    edge_height: float
    apex: ApexPoint

    def __post_init__(self) -> None:
        if self.wall_index < 0:
            raise ValueError("Wall index must be non-negative")
        if self.edge_height <= 0:
            raise ValueError("Edge height must be positive")
        if self.edge_height >= self.apex.z:
            raise ValueError("Edge height must be less than apex height")

    @property
    def slope_angle(self) -> float:
        """Calculate slope angle of this facet in degrees.

        The slope angle is measured from horizontal, representing
        how steeply the ceiling facet rises from the wall edge
        to the apex point.

        Returns:
            Slope angle in degrees (0-90).
        """
        # Calculate center of wall edge
        edge_center_x = (self.edge_start.x + self.edge_end.x) / 2
        edge_center_y = (self.edge_start.y + self.edge_end.y) / 2

        # Horizontal distance from edge center to apex
        horizontal_dist = self.apex.distance_to(edge_center_x, edge_center_y)

        # Vertical rise from edge to apex
        vertical_rise = self.apex.z - self.edge_height

        # Calculate angle from horizontal
        if horizontal_dist == 0:
            return 90.0
        return degrees(atan2(vertical_rise, horizontal_dist))

    def height_at_point(self, x: float, y: float) -> float:
        """Calculate ceiling height at a point under this facet.

        Uses linear interpolation based on radial distance from the apex.
        Points closer to the apex are higher, points closer to the wall
        edge are at the edge height.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.

        Returns:
            Ceiling height at the specified point in inches.
        """
        # Calculate center of wall edge
        edge_center_x = (self.edge_start.x + self.edge_end.x) / 2
        edge_center_y = (self.edge_start.y + self.edge_end.y) / 2

        # Distance from apex to edge center (full run of the facet)
        edge_dist = self.apex.distance_to(edge_center_x, edge_center_y)

        # Distance from apex to the query point
        point_dist = self.apex.distance_to(x, y)

        if edge_dist == 0:
            # Degenerate case: apex directly above edge center
            return self.apex.z

        # Linear interpolation: t=0 at apex (full height), t=1 at edge (edge height)
        t = min(1.0, point_dist / edge_dist)
        return self.apex.z - t * (self.apex.z - self.edge_height)


@dataclass(frozen=True)
class RadialCeilingGeometry:
    """Radial/pyramidal ceiling geometry for bay alcoves.

    Models a ceiling where multiple triangular facets converge
    to a central apex point, typical of bay window alcoves with
    pyramidal or conical ceiling treatments.

    Attributes:
        apex: The apex point where all facets meet.
        facets: Tuple of ceiling facets (one per wall segment).
        edge_height: Default wall top height where facets begin.
    """

    apex: ApexPoint
    facets: tuple[CeilingFacet, ...]
    edge_height: float

    def __post_init__(self) -> None:
        if self.edge_height <= 0:
            raise ValueError("Edge height must be positive")
        if len(self.facets) < 3:
            raise ValueError("Radial ceiling requires at least 3 facets")
        for facet in self.facets:
            if facet.apex != self.apex:
                raise ValueError("All facets must share the same apex point")

    def height_at_point(self, x: float, y: float) -> float | None:
        """Calculate ceiling height at any point.

        Determines which facet contains the point and returns the
        interpolated ceiling height at that location.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.

        Returns:
            Ceiling height at the specified point in inches,
            or None if the point is outside all facets.
        """
        # Find the facet that contains this point using a simple
        # closest-facet approach based on distance to wall edge center
        best_facet = None
        best_distance = float("inf")

        for facet in self.facets:
            # Calculate center of wall edge
            edge_center_x = (facet.edge_start.x + facet.edge_end.x) / 2
            edge_center_y = (facet.edge_start.y + facet.edge_end.y) / 2

            # Distance from point to edge center
            dist = sqrt((x - edge_center_x) ** 2 + (y - edge_center_y) ** 2)

            if dist < best_distance:
                best_distance = dist
                best_facet = facet

        if best_facet is None:
            return None

        return best_facet.height_at_point(x, y)

    @property
    def average_slope_angle(self) -> float:
        """Calculate the average slope angle across all facets.

        Returns:
            Average slope angle in degrees.
        """
        if not self.facets:
            return 0.0
        total = sum(facet.slope_angle for facet in self.facets)
        return total / len(self.facets)


class BayAlcoveConfig:
    """Domain configuration for bay window alcove built-ins.

    This is a lightweight domain representation of the bay alcove configuration
    that can be used by layout calculators and services. It holds the essential
    configuration data in a form suitable for domain logic.

    Attributes:
        bay_type: Type of bay configuration.
        walls: Tuple of wall configuration dictionaries.
        opening_width: Width of bay opening.
        bay_depth: Depth from main wall to furthest point.
        arc_angle: Arc angle for bow windows.
        segment_count: Segment count for bow windows.
        apex: ApexPoint for radial ceiling, or None.
        apex_mode: "auto" or "explicit" for apex calculation.
        edge_height: Height where ceiling meets walls.
        min_cabinet_width: Minimum width for cabinet zones.
        filler_treatment: Treatment for narrow zones.
        sill_clearance: Clearance below window sill.
        head_clearance: Clearance above window head.
        seat_surface_style: Seat surface construction style.
        flank_integration: Flanking cabinet connection style.
        top_style: Global top panel style.
        shelf_alignment: Global shelf alignment strategy.
    """

    def __init__(
        self,
        bay_type: str,
        walls: tuple,
        opening_width: float | None,
        bay_depth: float | None,
        arc_angle: float | None,
        segment_count: int | None,
        apex: "ApexPoint | None",
        apex_mode: str,
        edge_height: float,
        min_cabinet_width: float,
        filler_treatment: str,
        sill_clearance: float,
        head_clearance: float,
        seat_surface_style: str,
        flank_integration: str,
        top_style: str | None,
        shelf_alignment: str,
    ) -> None:
        self.bay_type = bay_type
        self.walls = walls
        self.opening_width = opening_width
        self.bay_depth = bay_depth
        self.arc_angle = arc_angle
        self.segment_count = segment_count
        self.apex = apex
        self.apex_mode = apex_mode
        self.edge_height = edge_height
        self.min_cabinet_width = min_cabinet_width
        self.filler_treatment = filler_treatment
        self.sill_clearance = sill_clearance
        self.head_clearance = head_clearance
        self.seat_surface_style = seat_surface_style
        self.flank_integration = flank_integration
        self.top_style = top_style
        self.shelf_alignment = shelf_alignment

    @property
    def is_bow(self) -> bool:
        """Check if this is a bow window configuration."""
        return self.bay_type == "bow"

    @property
    def wall_count(self) -> int:
        """Get the number of wall segments."""
        return len(self.walls)

    def get_wall(self, index: int) -> dict:
        """Get wall configuration by index.

        Args:
            index: Wall index (0-based).

        Returns:
            Wall configuration dictionary.

        Raises:
            IndexError: If index is out of range.
        """
        return self.walls[index]
