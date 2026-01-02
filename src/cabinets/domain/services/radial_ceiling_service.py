"""Radial ceiling service for FRD-23 Bay Window Alcove Built-ins.

This service computes radial/pyramidal ceiling geometry from bay alcove
configurations. It calculates wall segment positions, ceiling facet
geometry, and height values at any point within the bay.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from typing import TYPE_CHECKING

from ..value_objects import ApexPoint, CeilingFacet, Point2D, RadialCeilingGeometry

if TYPE_CHECKING:
    from ..value_objects import BayAlcoveConfig


@dataclass
class WallSegmentGeometry:
    """Computed geometry for a wall segment.

    Represents the calculated position and orientation of a wall segment
    within the bay alcove, derived from the configuration's length and
    angle specifications.

    Attributes:
        index: Zero-based index of the wall segment.
        start_point: Starting point of the wall in 2D room coordinates.
        end_point: Ending point of the wall in 2D room coordinates.
        length: Length of the wall segment in inches.
        angle: Cumulative angle from start in degrees.
        midpoint: Center point of the wall segment.
    """

    index: int
    start_point: Point2D
    end_point: Point2D
    length: float
    angle: float  # Cumulative angle from start
    midpoint: Point2D


class RadialCeilingService:
    """Service for computing radial/pyramidal ceiling geometry.

    This service takes a bay alcove configuration and computes:
    1. Wall segment positions and angles
    2. Ceiling facet geometry for each wall
    3. Height calculations at any point within the bay

    The service caches computed geometry for performance, so multiple
    calls to accessor methods are efficient.

    Example:
        >>> from cabinets.application.config import load_config, config_to_bay_alcove
        >>> config = load_config("bay-window.json")
        >>> bay_config = config_to_bay_alcove(config)
        >>> service = RadialCeilingService(bay_config)
        >>> geometry = service.build_radial_ceiling_geometry()
        >>> height = service.get_ceiling_height_at(24.0, 12.0)
    """

    def __init__(self, bay_config: "BayAlcoveConfig") -> None:
        """Initialize the radial ceiling service.

        Args:
            bay_config: Bay alcove configuration from config adapter.
        """
        self.bay_config = bay_config
        self._wall_segments: list[WallSegmentGeometry] | None = None
        self._radial_ceiling: RadialCeilingGeometry | None = None

    def compute_wall_positions(self) -> list[WallSegmentGeometry]:
        """Compute the positions of all wall segments.

        Starting from origin (0, 0), traces each wall segment using
        its length and angle to determine start/end points.

        For symmetric bays (angle=None), calculates angle as:
        exterior turn angle = 180 - (360 / wall_count)

        This formula produces the correct angles for regular polygons:
        - 3 walls: 60 degrees (equilateral triangle exterior)
        - 5 walls: 108 degrees (regular pentagon exterior)

        Returns:
            List of WallSegmentGeometry objects for each wall.
        """
        if self._wall_segments is not None:
            return self._wall_segments

        segments: list[WallSegmentGeometry] = []
        current_x, current_y = 0.0, 0.0
        cumulative_angle = 0.0

        for i in range(self.bay_config.wall_count):
            wall = self.bay_config.get_wall(i)
            wall_length = wall["length"]
            wall_angle = wall.get("angle")

            # Calculate wall angle
            if wall_angle is not None:
                turn_angle = wall_angle
            else:
                # Symmetric bay: exterior turn angle for regular polygon
                turn_angle = 180 - (360 / self.bay_config.wall_count)

            if i > 0:
                cumulative_angle += turn_angle

            # Calculate end point using current angle
            rad = radians(cumulative_angle)
            end_x = current_x + wall_length * cos(rad)
            end_y = current_y + wall_length * sin(rad)

            segments.append(
                WallSegmentGeometry(
                    index=i,
                    start_point=Point2D(current_x, current_y),
                    end_point=Point2D(end_x, end_y),
                    length=wall_length,
                    angle=cumulative_angle,
                    midpoint=Point2D((current_x + end_x) / 2, (current_y + end_y) / 2),
                )
            )

            current_x, current_y = end_x, end_y

        self._wall_segments = segments
        return segments

    def compute_apex_point(self) -> ApexPoint:
        """Compute or return the apex point for the ceiling.

        The apex is the highest point of the radial ceiling where all
        facets converge.

        Behavior:
        - If apex is "auto" (apex_mode="auto"): Calculate centroid of wall positions.
        - If apex is None: Use default (center of walls, edge_height + 12").
        - Otherwise: Use the specified apex coordinates.

        Returns:
            ApexPoint with x, y, z coordinates.
        """
        if self.bay_config.apex_mode == "auto" or self.bay_config.apex is None:
            # Calculate centroid of wall midpoints
            segments = self.compute_wall_positions()
            xs = [s.midpoint.x for s in segments]
            ys = [s.midpoint.y for s in segments]
            center_x = sum(xs) / len(xs)
            center_y = sum(ys) / len(ys)
            apex_z = self.bay_config.edge_height + 12.0  # Default: 12" above walls
            return ApexPoint(center_x, center_y, apex_z)
        else:
            # Use specified apex from configuration
            apex = self.bay_config.apex
            return ApexPoint(apex.x, apex.y, apex.z)

    def compute_ceiling_facets(self, apex: ApexPoint) -> tuple[CeilingFacet, ...]:
        """Compute ceiling facets from wall segments and apex.

        Each wall segment defines one triangular facet:
        - Two vertices at wall ends (at edge_height)
        - One vertex at apex point

        The facets form a pyramidal or conical ceiling structure
        typical of bay window alcoves.

        Args:
            apex: The apex point where all facets converge.

        Returns:
            Tuple of CeilingFacet objects, one per wall segment.
        """
        segments = self.compute_wall_positions()
        facets: list[CeilingFacet] = []

        for seg in segments:
            facet = CeilingFacet(
                wall_index=seg.index,
                edge_start=seg.start_point,
                edge_end=seg.end_point,
                edge_height=self.bay_config.edge_height,
                apex=apex,
            )
            facets.append(facet)

        return tuple(facets)

    def build_radial_ceiling_geometry(self) -> RadialCeilingGeometry:
        """Build the complete radial ceiling geometry.

        Constructs a RadialCeilingGeometry containing the apex point
        and all ceiling facets. This method caches the result for
        subsequent calls.

        Returns:
            RadialCeilingGeometry with apex and facet data.
        """
        if self._radial_ceiling is not None:
            return self._radial_ceiling

        apex = self.compute_apex_point()
        facets = self.compute_ceiling_facets(apex)

        self._radial_ceiling = RadialCeilingGeometry(
            apex=apex,
            facets=facets,
            edge_height=self.bay_config.edge_height,
        )
        return self._radial_ceiling

    def get_ceiling_height_at(self, x: float, y: float) -> float | None:
        """Get ceiling height at a specific point.

        Calculates the interpolated ceiling height at the given x, y
        coordinates within the bay alcove.

        Args:
            x: X coordinate in room space (inches).
            y: Y coordinate in room space (inches).

        Returns:
            Ceiling height in inches at the point, or None if the
            point is outside all facets.
        """
        geometry = self.build_radial_ceiling_geometry()
        return geometry.height_at_point(x, y)

    def get_cabinet_height_for_wall(self, wall_index: int) -> float:
        """Get the maximum cabinet height for a wall segment.

        Determines the usable cabinet height for a given wall, taking
        into account windows and ceiling geometry:

        - For walls with windows: Returns sill_height - sill_clearance.
        - For walls without windows: Returns ceiling height at wall midpoint.

        Args:
            wall_index: Zero-based index of the wall segment.

        Returns:
            Maximum cabinet height in inches for the wall.

        Raises:
            ValueError: If wall_index is out of range.
        """
        if wall_index < 0 or wall_index >= self.bay_config.wall_count:
            raise ValueError(f"Invalid wall index: {wall_index}")

        wall = self.bay_config.get_wall(wall_index)

        # Check for window configuration
        window = wall.get("window")
        if window is not None:
            # Cabinet height limited by window sill minus clearance
            return window["sill_height"] - self.bay_config.sill_clearance

        # Full height to ceiling at wall midpoint
        segments = self.compute_wall_positions()
        seg = segments[wall_index]
        ceiling_height = self.get_ceiling_height_at(seg.midpoint.x, seg.midpoint.y)
        return (
            ceiling_height
            if ceiling_height is not None
            else self.bay_config.edge_height
        )

    def invalidate_cache(self) -> None:
        """Invalidate cached geometry data.

        Call this method if the bay configuration has been modified
        and geometry needs to be recomputed.
        """
        self._wall_segments = None
        self._radial_ceiling = None
