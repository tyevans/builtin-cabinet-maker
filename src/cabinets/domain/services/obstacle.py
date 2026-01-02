"""Obstacle handling services for cabinet layout.

This module provides services for detecting collisions between cabinet sections
and obstacles (windows, doors, outlets, etc.) and for laying out cabinet sections
while avoiding these obstacles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..section_resolver import SectionSpec
from ..value_objects import (
    Clearance,
    CollisionResult,
    DEFAULT_CLEARANCES,
    LayoutResult,
    LayoutWarning,
    ObstacleType,
    ObstacleZone,
    PlacedSection,
    SectionBounds,
    SkippedArea,
    ValidRegion,
)

if TYPE_CHECKING:
    from ..entities import Obstacle

__all__ = [
    "ObstacleCollisionService",
    "ObstacleAwareLayoutService",
]


class ObstacleCollisionService:
    """Detects collisions between cabinet sections and obstacles.

    This service provides collision detection capabilities for cabinet layout,
    including:
    - Getting obstacle zones for specific walls
    - Checking individual sections against obstacle zones
    - Batch collision checking for multiple sections
    - Finding valid regions on walls where sections can be placed

    Attributes:
        default_clearances: Mapping of obstacle types to their default clearances.
    """

    def __init__(
        self, default_clearances: dict[ObstacleType, Clearance] | None = None
    ) -> None:
        """Initialize the collision service.

        Args:
            default_clearances: Optional custom clearance mapping. If not provided,
                               uses DEFAULT_CLEARANCES from value_objects.
        """
        self.default_clearances = default_clearances or DEFAULT_CLEARANCES

    def get_obstacle_zones(
        self,
        obstacles: list[Obstacle],
        wall_index: int,
    ) -> list[ObstacleZone]:
        """Get all obstacle zones for a specific wall.

        Filters obstacles to those on the specified wall and computes their
        exclusion zones including clearances.

        Args:
            obstacles: List of all obstacles in the room.
            wall_index: Index of the wall to get zones for.

        Returns:
            List of ObstacleZone objects for obstacles on the specified wall.
        """
        return [
            obs.get_zone_bounds(obs.get_clearance(self.default_clearances))
            for obs in obstacles
            if obs.wall_index == wall_index
        ]

    def check_collision(
        self,
        section: SectionBounds,
        zones: list[ObstacleZone],
    ) -> list[CollisionResult]:
        """Check if section collides with any obstacle zones.

        Args:
            section: The cabinet section bounds to check.
            zones: List of obstacle zones to check against.

        Returns:
            List of CollisionResult objects for each collision detected.
            Empty list if no collisions.
        """
        results = []
        for zone in zones:
            if zone.overlaps(section):
                overlap = self._calculate_overlap_area(section, zone)
                results.append(CollisionResult(zone=zone, overlap_area=overlap))
        return results

    def check_collisions_batch(
        self,
        sections: list[SectionBounds],
        zones: list[ObstacleZone],
    ) -> dict[int, list[CollisionResult]]:
        """Check multiple sections against multiple zones.

        Performs collision detection for each section and returns results
        keyed by section index.

        Args:
            sections: List of cabinet section bounds to check.
            zones: List of obstacle zones to check against.

        Returns:
            Dictionary mapping section index to list of CollisionResult objects.
            Sections with no collisions will have empty lists.
        """
        return {
            i: self.check_collision(section, zones)
            for i, section in enumerate(sections)
        }

    def find_valid_regions(
        self,
        wall_length: float,
        wall_height: float,
        zones: list[ObstacleZone],
        min_width: float = 6.0,
        min_height: float = 12.0,
    ) -> list[ValidRegion]:
        """Find regions on wall where sections can be placed.

        Analyzes the wall space considering obstacle zones and finds all
        regions where cabinet sections can be placed.

        Returns regions categorized as:
        - "full": Full height available (no vertical obstruction)
        - "lower": Below obstacles (e.g., under windows)
        - "upper": Above obstacles (e.g., over doors)
        - "gap": Horizontal gap between obstacles

        Args:
            wall_length: Total length of the wall in inches.
            wall_height: Total height of the wall in inches.
            zones: List of obstacle zones on the wall.
            min_width: Minimum region width to include (default 6 inches).
            min_height: Minimum region height to include (default 12 inches).

        Returns:
            List of ValidRegion objects representing available placement areas.
        """
        if not zones:
            return [
                ValidRegion(
                    left=0,
                    right=wall_length,
                    bottom=0,
                    top=wall_height,
                    region_type="full",
                )
            ]

        regions: list[ValidRegion] = []

        # Sort zones by horizontal position
        sorted_zones = sorted(zones, key=lambda z: z.left)

        # Find horizontal regions (gaps between zones and regions above/below zones)
        current_x = 0.0
        for zone in sorted_zones:
            # Gap before this zone (analyze vertical region)
            if zone.left > current_x:
                gap_region = self._analyze_vertical_region(
                    left=current_x,
                    right=zone.left,
                    wall_height=wall_height,
                    zones=zones,
                    min_width=min_width,
                    min_height=min_height,
                )
                regions.extend(gap_region)

            # Region below zone
            if zone.bottom > 0:
                lower = ValidRegion(
                    left=max(0, zone.left),
                    right=min(wall_length, zone.right),
                    bottom=0,
                    top=zone.bottom,
                    region_type="lower",
                )
                if lower.width >= min_width and lower.height >= min_height:
                    regions.append(lower)

            # Region above zone
            if zone.top < wall_height:
                upper = ValidRegion(
                    left=max(0, zone.left),
                    right=min(wall_length, zone.right),
                    bottom=zone.top,
                    top=wall_height,
                    region_type="upper",
                )
                if upper.width >= min_width and upper.height >= min_height:
                    regions.append(upper)

            current_x = max(current_x, zone.right)

        # Gap after last zone
        if current_x < wall_length:
            gap_region = self._analyze_vertical_region(
                left=current_x,
                right=wall_length,
                wall_height=wall_height,
                zones=zones,
                min_width=min_width,
                min_height=min_height,
            )
            regions.extend(gap_region)

        return regions

    def _calculate_overlap_area(
        self,
        section: SectionBounds,
        zone: ObstacleZone,
    ) -> float:
        """Calculate the overlapping area between section and zone.

        Args:
            section: The cabinet section bounds.
            zone: The obstacle zone.

        Returns:
            Overlap area in square inches. Returns 0 if no overlap.
        """
        x_overlap = max(
            0, min(section.right, zone.right) - max(section.left, zone.left)
        )
        y_overlap = max(
            0, min(section.top, zone.top) - max(section.bottom, zone.bottom)
        )
        return x_overlap * y_overlap

    def _analyze_vertical_region(
        self,
        left: float,
        right: float,
        wall_height: float,
        zones: list[ObstacleZone],
        min_width: float,
        min_height: float,
    ) -> list[ValidRegion]:
        """Analyze a vertical slice of wall for valid regions.

        Examines a horizontal range of the wall and determines what vertical
        regions are available, considering any obstacles that block portions
        of that horizontal range.

        Args:
            left: Left edge of the horizontal range.
            right: Right edge of the horizontal range.
            wall_height: Total height of the wall.
            zones: All obstacle zones on the wall.
            min_width: Minimum region width to include.
            min_height: Minimum region height to include.

        Returns:
            List of ValidRegion objects for the analyzed slice.
        """
        if right - left < min_width:
            return []

        # Check if any zones block this horizontal region
        blocking_zones = [z for z in zones if not (z.right <= left or z.left >= right)]

        if not blocking_zones:
            return [
                ValidRegion(
                    left=left,
                    right=right,
                    bottom=0,
                    top=wall_height,
                    region_type="full",
                )
            ]

        # Find unblocked vertical regions
        regions: list[ValidRegion] = []

        # Sort blockers by bottom edge
        sorted_blockers = sorted(blocking_zones, key=lambda z: z.bottom)

        current_y = 0.0
        for blocker in sorted_blockers:
            if blocker.bottom > current_y:
                region = ValidRegion(
                    left=left,
                    right=right,
                    bottom=current_y,
                    top=blocker.bottom,
                    region_type="gap" if current_y > 0 else "lower",
                )
                if region.height >= min_height:
                    regions.append(region)
            current_y = max(current_y, blocker.top)

        # Region above all blockers
        if current_y < wall_height:
            region = ValidRegion(
                left=left,
                right=right,
                bottom=current_y,
                top=wall_height,
                region_type="upper",
            )
            if region.height >= min_height:
                regions.append(region)

        return regions


class ObstacleAwareLayoutService:
    """Lays out cabinet sections while avoiding obstacles.

    This service calculates the placement of cabinet sections on a wall,
    automatically avoiding obstacles and finding the best available regions.
    It supports automatic height mode selection (full, lower, upper) and
    can split sections around obstacles when necessary.

    Attributes:
        collision_service: Service for obstacle collision detection.
        min_section_width: Minimum width for a section in inches (default 6.0).
        min_section_height: Minimum height for a section in inches (default 12.0).
    """

    def __init__(
        self,
        collision_service: ObstacleCollisionService,
        min_section_width: float = 6.0,
        min_section_height: float = 12.0,
    ) -> None:
        """Initialize the layout service.

        Args:
            collision_service: Service for obstacle collision detection.
            min_section_width: Minimum width for a section in inches.
            min_section_height: Minimum height for a section in inches.
        """
        self.collision_service = collision_service
        self.min_section_width = min_section_width
        self.min_section_height = min_section_height

    def layout_sections(
        self,
        wall_length: float,
        wall_height: float,
        wall_index: int,
        obstacles: list[Obstacle],
        requested_sections: list[SectionSpec],
    ) -> LayoutResult:
        """Layout sections on wall, avoiding obstacles.

        Algorithm:
        1. Get obstacle zones for this wall
        2. Find valid regions
        3. For each requested section:
           - If height_mode specified, use that
           - If "auto" or None, try full height first, then lower, then upper
           - Try to fit in available regions
           - If doesn't fit, try splitting
           - If still doesn't fit, add to skipped with warning
        4. Return placed sections, warnings, and skipped areas

        Args:
            wall_length: Total length of the wall in inches.
            wall_height: Total height of the wall in inches.
            wall_index: Index of the wall (0-based).
            obstacles: List of all obstacles in the room.
            requested_sections: List of section specifications to place.

        Returns:
            LayoutResult containing placed sections, warnings, and skipped areas.
        """
        zones = self.collision_service.get_obstacle_zones(obstacles, wall_index)
        valid_regions = self.collision_service.find_valid_regions(
            wall_length,
            wall_height,
            zones,
            min_width=self.min_section_width,
            min_height=self.min_section_height,
        )

        placed_sections: list[PlacedSection] = []
        warnings: list[LayoutWarning] = []
        skipped_areas: list[SkippedArea] = []

        # Track remaining space in each region
        remaining_regions = list(valid_regions)
        current_x = 0.0

        for i, spec in enumerate(requested_sections):
            section_width = self._resolve_width(
                spec, wall_length, current_x, remaining_regions
            )
            height_mode = spec.height_mode or "full"

            if height_mode == "auto":
                # Try full height first, then lower, then upper
                placement = self._try_place_section(
                    i,
                    section_width,
                    spec.shelves,
                    remaining_regions,
                    zones,
                    wall_height,
                    current_x,
                    preferred_modes=["full", "lower", "upper"],
                )
            else:
                placement = self._try_place_section(
                    i,
                    section_width,
                    spec.shelves,
                    remaining_regions,
                    zones,
                    wall_height,
                    current_x,
                    preferred_modes=[height_mode],
                )

            if placement:
                placed_sections.append(placement)
                current_x = placement.bounds.right
                # Update remaining regions
                remaining_regions = self._consume_region(
                    remaining_regions, placement.bounds
                )
            else:
                # Try splitting around obstacles
                split_placements = self._try_split_section(
                    i,
                    section_width,
                    spec.shelves,
                    remaining_regions,
                    zones,
                    wall_height,
                    current_x,
                )
                if split_placements:
                    placed_sections.extend(split_placements)
                    for p in split_placements:
                        current_x = max(current_x, p.bounds.right)
                        remaining_regions = self._consume_region(
                            remaining_regions, p.bounds
                        )
                    warnings.append(
                        LayoutWarning(
                            message=f"Section {i} was split into {len(split_placements)} parts to avoid obstacles",
                            suggestion=None,
                        )
                    )
                else:
                    # Skip this section
                    skipped_areas.append(
                        SkippedArea(
                            bounds=SectionBounds(
                                left=current_x,
                                right=current_x + section_width,
                                bottom=0,
                                top=wall_height,
                            ),
                            reason=f"Section {i} cannot fit: blocked by obstacles",
                        )
                    )
                    warnings.append(
                        LayoutWarning(
                            message=f"Section {i} skipped: cannot fit around obstacles",
                            suggestion="Consider using height_mode='lower' or 'upper' for partial-height sections",
                        )
                    )

        return LayoutResult.create(
            placed_sections=placed_sections,
            warnings=warnings,
            skipped_areas=skipped_areas,
        )

    def _resolve_width(
        self,
        spec: SectionSpec,
        wall_length: float,
        current_x: float,
        remaining_regions: list[ValidRegion],
    ) -> float:
        """Resolve 'fill' width to actual width.

        Args:
            spec: The section specification.
            wall_length: Total wall length.
            current_x: Current x position along the wall.
            remaining_regions: List of available regions.

        Returns:
            The resolved width for the section.
        """
        if spec.width == "fill":
            # Fill remaining space in current full-height regions
            available = wall_length - current_x
            for region in remaining_regions:
                if (
                    region.region_type == "full"
                    and region.left <= current_x < region.right
                ):
                    available = region.right - current_x
                    break
            return max(available, self.min_section_width)
        return float(spec.width)

    def _try_place_section(
        self,
        section_index: int,
        width: float,
        shelves: int,
        regions: list[ValidRegion],
        zones: list[ObstacleZone],
        wall_height: float,
        current_x: float,
        preferred_modes: list[str],
    ) -> PlacedSection | None:
        """Try to place a section in available regions.

        Args:
            section_index: Index of the section being placed.
            width: Requested width of the section.
            shelves: Number of shelves for the section.
            regions: Available regions for placement.
            zones: Obstacle zones to avoid.
            wall_height: Total wall height.
            current_x: Current x position along the wall.
            preferred_modes: List of height modes to try, in order of preference.

        Returns:
            PlacedSection if placement succeeded, None otherwise.
        """
        for mode in preferred_modes:
            # Sort regions to prefer those starting at or after current_x
            sorted_regions = sorted(
                regions, key=lambda r: (0 if r.left >= current_x else 1, r.left)
            )

            for region in sorted_regions:
                if not self._mode_matches_region(mode, region):
                    continue

                if region.width >= width:
                    # Determine the left position for this placement
                    left = (
                        max(region.left, current_x)
                        if region.left < current_x
                        else region.left
                    )

                    # Check if there's enough width from this starting position
                    available_width = region.right - left
                    if available_width < width:
                        continue

                    # Check if this placement would collide
                    bounds = SectionBounds(
                        left=left,
                        right=left + width,
                        bottom=region.bottom,
                        top=region.top,
                    )

                    collisions = self.collision_service.check_collision(bounds, zones)
                    if not collisions:
                        return PlacedSection(
                            section_index=section_index,
                            bounds=bounds,
                            height_mode=mode if mode != "auto" else region.region_type,
                            shelves=shelves,
                        )
        return None

    def _mode_matches_region(self, mode: str, region: ValidRegion) -> bool:
        """Check if height mode matches region type.

        Args:
            mode: The requested height mode.
            region: The region to check.

        Returns:
            True if the mode matches the region type.
        """
        if mode == "full":
            return region.region_type == "full"
        if mode == "lower":
            return region.region_type in ("lower", "gap")
        if mode == "upper":
            return region.region_type in ("upper", "gap")
        return True  # auto matches any

    def _try_split_section(
        self,
        section_index: int,
        original_width: float,
        shelves: int,
        regions: list[ValidRegion],
        zones: list[ObstacleZone],
        wall_height: float,
        current_x: float,
    ) -> list[PlacedSection]:
        """Try to split a section around obstacles.

        Args:
            section_index: Index of the section being split.
            original_width: Original requested width of the section.
            shelves: Number of shelves for the section.
            regions: Available regions for placement.
            zones: Obstacle zones to avoid.
            wall_height: Total wall height.
            current_x: Current x position along the wall.

        Returns:
            List of PlacedSection objects representing the split parts,
            or empty list if splitting is not possible.
        """
        placements: list[PlacedSection] = []
        remaining_width = original_width

        # Sort regions by left position, preferring those at or after current_x
        sorted_regions = sorted(
            [r for r in regions if r.left >= current_x or r.right > current_x],
            key=lambda r: r.left,
        )

        for region in sorted_regions:
            if remaining_width < self.min_section_width:
                break

            # Determine starting position in this region
            start_x = max(region.left, current_x)
            available_in_region = region.right - start_x

            if available_in_region >= self.min_section_width:
                # Take as much as we can from this region
                take_width = min(remaining_width, available_in_region)
                if take_width >= self.min_section_width:
                    bounds = SectionBounds(
                        left=start_x,
                        right=start_x + take_width,
                        bottom=region.bottom,
                        top=region.top,
                    )

                    collisions = self.collision_service.check_collision(bounds, zones)
                    if not collisions:
                        # Distribute shelves proportionally
                        proportion = take_width / original_width
                        section_shelves = max(1, int(shelves * proportion))

                        placements.append(
                            PlacedSection(
                                section_index=section_index,
                                bounds=bounds,
                                height_mode=region.region_type,
                                shelves=section_shelves,
                            )
                        )
                        remaining_width -= take_width

        return placements if placements else []

    def _consume_region(
        self,
        regions: list[ValidRegion],
        consumed: SectionBounds,
    ) -> list[ValidRegion]:
        """Update regions after placing a section.

        Args:
            regions: Current list of available regions.
            consumed: The bounds of the placed section.

        Returns:
            Updated list of regions with the consumed area removed.
        """
        new_regions: list[ValidRegion] = []
        for region in regions:
            # If this region doesn't overlap with consumed, keep it
            if consumed.right <= region.left or consumed.left >= region.right:
                new_regions.append(region)
            elif consumed.bottom >= region.top or consumed.top <= region.bottom:
                # No vertical overlap
                new_regions.append(region)
            else:
                # Split the region if there's remaining space
                if consumed.left > region.left:
                    # Left portion remains
                    left_width = consumed.left - region.left
                    if left_width >= self.min_section_width:
                        new_regions.append(
                            ValidRegion(
                                left=region.left,
                                right=consumed.left,
                                bottom=region.bottom,
                                top=region.top,
                                region_type=region.region_type,
                            )
                        )
                if consumed.right < region.right:
                    # Right portion remains
                    right_width = region.right - consumed.right
                    if right_width >= self.min_section_width:
                        new_regions.append(
                            ValidRegion(
                                left=consumed.right,
                                right=region.right,
                                bottom=region.bottom,
                                top=region.top,
                                region_type=region.region_type,
                            )
                        )
        return new_regions
