"""Panel geometry service for bay alcove angle cuts and tapers (FRD-23 Phase 6).

This service calculates panel geometry requirements for bay alcove configurations:
1. Angle cuts at bay wall junctions (side panels)
2. Tapered tops under radial ceiling slopes
3. Compound cuts (angle + taper combined)
4. Back panel sizing for angled walls
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..value_objects import AngleCut, PanelCutMetadata, TaperSpec

if TYPE_CHECKING:
    from .radial_ceiling_service import RadialCeilingService, WallSegmentGeometry


@dataclass
class PanelAngleSpec:
    """Specification for angled panel cuts at wall junctions.

    When two walls meet at an angle (common in bay window configurations),
    the cabinet panels at the junction need miter cuts to fit properly.

    Attributes:
        wall_index: Index of the wall this spec applies to.
        left_angle: Angle cut for left edge (degrees from perpendicular).
        right_angle: Angle cut for right edge (degrees from perpendicular).
        is_compound: True if panel requires both angle and taper cuts.
    """

    wall_index: int
    left_angle: float  # Angle cut for left edge (degrees)
    right_angle: float  # Angle cut for right edge (degrees)
    is_compound: bool  # Has both angle and taper cuts


@dataclass
class PanelTaperSpec:
    """Specification for tapered panels under sloped ceiling.

    When a ceiling slopes (common with radial bay ceilings), top panels
    and sometimes side panels need to taper to follow the ceiling line.

    Attributes:
        wall_index: Index of the wall this spec applies to.
        front_height: Height at front of panel (inches).
        back_height: Height at back of panel (inches).
        taper_direction: Direction of taper - "front_to_back" or "left_to_right".
    """

    wall_index: int
    front_height: float  # Height at front of panel
    back_height: float  # Height at back of panel
    taper_direction: str  # "front_to_back" or "left_to_right"


class PanelGeometryService:
    """Service for calculating panel geometry in bay alcoves.

    This service analyzes bay alcove configurations and determines the
    special cuts needed for panels:

    1. **Junction angles**: At bay wall junctions, side panels need
       miter cuts. For a junction angle of theta, each panel gets
       a cut of theta/2.

    2. **Ceiling tapers**: Under radial ceilings, panels may need to
       taper from front to back to follow the ceiling slope.

    3. **Compound cuts**: Some panels need both angle and taper cuts.

    Example:
        >>> from cabinets.domain.services import RadialCeilingService, PanelGeometryService
        >>> ceiling_service = RadialCeilingService(bay_config)
        >>> panel_service = PanelGeometryService(ceiling_service)
        >>> angles = panel_service.calculate_junction_angles()
        >>> for spec in angles:
        ...     print(f"Wall {spec.wall_index}: left={spec.left_angle:.1f}, right={spec.right_angle:.1f}")
    """

    def __init__(self, ceiling_service: "RadialCeilingService") -> None:
        """Initialize the panel geometry service.

        Args:
            ceiling_service: RadialCeilingService instance for the bay configuration.
        """
        self.ceiling_service = ceiling_service
        self._angle_specs: list[PanelAngleSpec] | None = None
        self._taper_specs: list[PanelTaperSpec] | None = None

    def calculate_junction_angles(self) -> list[PanelAngleSpec]:
        """Calculate angle cuts needed at each wall junction.

        For a bay wall at angle theta from the previous wall, the side
        panels need an angle cut of theta/2 on each mating edge.

        Example: 45-degree bay angle -> 22.5-degree cut on each side

        The algorithm:
        1. Get wall segment geometries from ceiling service
        2. For each wall, calculate the angle difference to adjacent walls
        3. Divide by 2 for the panel edge cut angle

        Returns:
            List of PanelAngleSpec objects, one per wall.
        """
        if self._angle_specs is not None:
            return self._angle_specs

        segments = self.ceiling_service.compute_wall_positions()
        angles: list[PanelAngleSpec] = []

        for i, seg in enumerate(segments):
            # Calculate angle to previous and next walls
            prev_idx = (i - 1) % len(segments)
            next_idx = (i + 1) % len(segments)

            # Angle between this wall and previous
            angle_from_prev = self._calculate_wall_junction_angle(
                segments[prev_idx], seg
            )
            # Angle between this wall and next
            angle_to_next = self._calculate_wall_junction_angle(seg, segments[next_idx])

            # Panel edge cuts are half the junction angle
            left_cut = angle_from_prev / 2
            right_cut = angle_to_next / 2

            angles.append(
                PanelAngleSpec(
                    wall_index=i,
                    left_angle=left_cut,
                    right_angle=right_cut,
                    is_compound=False,  # Updated later if taper also needed
                )
            )

        self._angle_specs = angles
        return angles

    def calculate_ceiling_tapers(self) -> list[PanelTaperSpec]:
        """Calculate taper needed for panels under radial ceiling.

        For each wall, determines if the ceiling slope requires
        a tapered top panel by comparing heights at front and back
        positions relative to the wall.

        Returns:
            List of PanelTaperSpec objects for walls that need tapers.
            Walls without significant taper requirements are excluded.
        """
        if self._taper_specs is not None:
            return self._taper_specs

        segments = self.ceiling_service.compute_wall_positions()
        geometry = self.ceiling_service.build_radial_ceiling_geometry()
        tapers: list[PanelTaperSpec] = []

        for seg in segments:
            # Get ceiling height at wall midpoint (front of cabinet)
            front_height = geometry.height_at_point(seg.midpoint.x, seg.midpoint.y)

            # Use edge_height as back reference (where cabinet meets wall)
            back_height = geometry.edge_height

            # Only create taper spec if there's a meaningful height difference
            # (> 0.5" to avoid floating point noise)
            if front_height is not None and abs(front_height - back_height) > 0.5:
                tapers.append(
                    PanelTaperSpec(
                        wall_index=seg.index,
                        front_height=front_height,
                        back_height=back_height,
                        taper_direction="front_to_back",
                    )
                )

        self._taper_specs = tapers
        return tapers

    def get_panel_cut_metadata(
        self, wall_index: int, panel_type: str
    ) -> PanelCutMetadata | None:
        """Get cut metadata for a specific panel.

        Combines angle and taper specifications into a PanelCutMetadata
        object that can be attached to cut list entries.

        Args:
            wall_index: Index of the bay wall (0-based).
            panel_type: Type of panel - "left_side", "right_side", "top", "back".

        Returns:
            PanelCutMetadata with angle/taper specifications, or None if
            no special cuts are needed for this panel.
        """
        angle_specs = self.calculate_junction_angles()
        taper_specs = self.calculate_ceiling_tapers()

        angle_spec = next((a for a in angle_specs if a.wall_index == wall_index), None)
        taper_spec = next((t for t in taper_specs if t.wall_index == wall_index), None)

        angle_cuts: list[AngleCut] = []
        taper: TaperSpec | None = None

        if panel_type == "left_side" and angle_spec:
            if abs(angle_spec.left_angle) > 0.5:  # Meaningful angle (> 0.5 degrees)
                angle_cuts.append(
                    AngleCut(
                        edge="left",
                        angle=angle_spec.left_angle,
                        bevel=False,  # Standard miter cut, not bevel
                    )
                )
        elif panel_type == "right_side" and angle_spec:
            if abs(angle_spec.right_angle) > 0.5:
                angle_cuts.append(
                    AngleCut(
                        edge="right",
                        angle=angle_spec.right_angle,
                        bevel=False,
                    )
                )
        elif panel_type == "top" and taper_spec:
            # TaperSpec uses start_height/end_height, direction is left_to_right or right_to_left
            # For front_to_back tapers, we map to left_to_right as a convention
            taper = TaperSpec(
                start_height=taper_spec.front_height,
                end_height=taper_spec.back_height,
                direction="left_to_right",  # Convention: left=front, right=back
            )

        if angle_cuts or taper:
            return PanelCutMetadata(
                angle_cuts=tuple(angle_cuts) if angle_cuts else (),
                taper=taper,
                notches=(),
            )

        return None

    def get_compound_cut_walls(self) -> list[int]:
        """Identify walls that require compound cuts.

        A compound cut is when a panel needs both an angle cut (for wall
        junction) and a taper cut (for ceiling slope) simultaneously.

        Returns:
            List of wall indices that require compound cuts.
        """
        angle_specs = self.calculate_junction_angles()
        taper_specs = self.calculate_ceiling_tapers()

        # Walls with meaningful angle cuts
        angled_walls = {
            spec.wall_index
            for spec in angle_specs
            if abs(spec.left_angle) > 0.5 or abs(spec.right_angle) > 0.5
        }

        # Walls with taper requirements
        tapered_walls = {spec.wall_index for spec in taper_specs}

        # Intersection = compound cuts needed
        return sorted(angled_walls & tapered_walls)

    def _calculate_wall_junction_angle(
        self, wall1: "WallSegmentGeometry", wall2: "WallSegmentGeometry"
    ) -> float:
        """Calculate the angle between two adjacent walls.

        The junction angle is the difference between wall directions.
        This angle determines how much each panel edge needs to be cut.

        Args:
            wall1: First wall segment (previous in sequence).
            wall2: Second wall segment (current in sequence).

        Returns:
            Absolute angle difference in degrees (0-180).
        """
        # Angle is the difference in wall directions
        angle_diff = wall2.angle - wall1.angle
        # Normalize to -180 to 180
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360
        return abs(angle_diff)

    def generate_cut_notes(self, wall_index: int, panel_type: str) -> str:
        """Generate human-readable notes for cut list documentation.

        Creates a description of the special cuts needed for a panel,
        suitable for inclusion in cut lists or assembly instructions.

        Args:
            wall_index: Index of the bay wall.
            panel_type: Type of panel - "left_side", "right_side", "top", "back".

        Returns:
            Human-readable description of cuts, or empty string if no special cuts.
        """
        metadata = self.get_panel_cut_metadata(wall_index, panel_type)
        if metadata is None:
            return ""

        notes: list[str] = []

        for cut in metadata.angle_cuts:
            cut_type = "bevel" if cut.bevel else "miter"
            notes.append(f"{cut.angle:.1f} deg {cut_type} on {cut.edge} edge")

        if metadata.taper:
            notes.append(
                f'Taper: {metadata.taper.start_height:.1f}" to '
                f'{metadata.taper.end_height:.1f}"'
            )

        return "; ".join(notes)

    def invalidate_cache(self) -> None:
        """Invalidate cached calculations.

        Call this method if the ceiling service configuration has changed
        and panel geometry needs to be recalculated.
        """
        self._angle_specs = None
        self._taper_specs = None
