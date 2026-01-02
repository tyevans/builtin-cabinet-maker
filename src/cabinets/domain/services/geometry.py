"""Geometry services for advanced cabinet calculations.

This module provides services for handling complex geometric scenarios:
- SlopedCeilingService: Handles sloped ceiling calculations
- SkylightVoidService: Handles skylight void calculations
- OutsideCornerService: Handles outside corner panel generation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

from ..entities import Panel
from ..value_objects import (
    AngleCut,
    CeilingSlope,
    MaterialSpec,
    NotchSpec,
    OutsideCornerConfig,
    PanelType,
    Skylight,
    TaperSpec,
)

__all__ = [
    "SlopedCeilingService",
    "SkylightVoidService",
    "OutsideCornerService",
]


@dataclass
class SlopedCeilingService:
    """Calculates section heights and generates tapered panels for sloped ceilings.

    This service handles the geometry calculations needed for cabinets installed
    under sloped ceilings, such as in attic spaces or vaulted ceiling areas.
    It determines the appropriate height for each cabinet section based on its
    position along the slope and generates taper specifications for top panels.
    """

    def calculate_section_heights(
        self,
        section_widths: list[float],
        slope: CeilingSlope,
        wall_length: float,
    ) -> list[float]:
        """Calculate height for each section based on position along slope.

        Uses the midpoint of each section to determine its height along the
        slope. This provides a representative height for the section while
        avoiding edge cases at section boundaries.

        Args:
            section_widths: Width of each section in inches.
            slope: CeilingSlope definition specifying angle, start height, and direction.
            wall_length: Total wall length in inches.

        Returns:
            List of calculated heights for each section in inches.
        """
        heights = []
        current_position = 0.0

        for width in section_widths:
            # Use section midpoint for height calculation
            midpoint = current_position + width / 2

            # Calculate position based on direction
            if slope.direction == "right_to_left":
                position = wall_length - midpoint
            else:
                position = midpoint

            height = slope.height_at_position(position)

            # Clamp to minimum height
            if height < slope.min_height:
                height = slope.min_height

            heights.append(height)
            current_position += width

        return heights

    def calculate_section_edge_heights(
        self,
        section_x: float,
        section_width: float,
        slope: CeilingSlope,
        wall_length: float,
    ) -> tuple[float, float]:
        """Calculate left and right edge heights for a section.

        Determines the ceiling height at both edges of a section, which is
        needed to generate taper specifications for the top panel.

        Args:
            section_x: X position of section left edge in inches.
            section_width: Width of section in inches.
            slope: CeilingSlope definition.
            wall_length: Total wall length in inches.

        Returns:
            Tuple of (left_height, right_height) in inches.
        """
        left_x = section_x
        right_x = section_x + section_width

        if slope.direction == "right_to_left":
            left_pos = wall_length - left_x
            right_pos = wall_length - right_x
        else:
            left_pos = left_x
            right_pos = right_x

        left_height = max(slope.height_at_position(left_pos), slope.min_height)
        right_height = max(slope.height_at_position(right_pos), slope.min_height)

        return (left_height, right_height)

    def generate_taper_spec(
        self,
        section_x: float,
        section_width: float,
        slope: CeilingSlope,
        wall_length: float,
    ) -> TaperSpec | None:
        """Generate TaperSpec for a section under a sloped ceiling.

        Calculates whether a section requires a tapered top panel and, if so,
        generates the specification for that taper including start/end heights
        and direction.

        Args:
            section_x: X position of section left edge in inches.
            section_width: Width of section in inches.
            slope: CeilingSlope definition.
            wall_length: Total wall length in inches.

        Returns:
            TaperSpec if the section has non-uniform height (taper needed),
            None if the section has uniform height (no taper needed).
        """
        left_height, right_height = self.calculate_section_edge_heights(
            section_x, section_width, slope, wall_length
        )

        # No taper needed if heights are equal (within tolerance)
        if abs(left_height - right_height) < 0.001:
            return None

        # Determine taper direction based on which end is higher
        direction: Literal["left_to_right", "right_to_left"]
        if left_height > right_height:
            direction = "left_to_right"
        else:
            direction = "right_to_left"

        return TaperSpec(
            start_height=max(left_height, right_height),
            end_height=min(left_height, right_height),
            direction=direction,
        )

    def check_min_height_violations(
        self,
        section_widths: list[float],
        slope: CeilingSlope,
        wall_length: float,
    ) -> list[tuple[int, float, float]]:
        """Check for sections that violate minimum height.

        Identifies any sections where the calculated height at the midpoint
        falls below the slope's minimum height threshold. This helps detect
        sections that would be too short to be usable.

        Args:
            section_widths: Width of each section in inches.
            slope: CeilingSlope definition.
            wall_length: Total wall length in inches.

        Returns:
            List of (section_index, calculated_height, min_height) tuples
            for each section that violates the minimum height requirement.
            Empty list if no violations are detected.
        """
        violations = []
        current_position = 0.0

        for i, width in enumerate(section_widths):
            midpoint = current_position + width / 2

            if slope.direction == "right_to_left":
                position = wall_length - midpoint
            else:
                position = midpoint

            height = slope.height_at_position(position)

            if height < slope.min_height:
                violations.append((i, height, slope.min_height))

            current_position += width

        return violations


@dataclass
class SkylightVoidService:
    """Calculates skylight void intersections with cabinet sections."""

    def calculate_void_intersection(
        self,
        skylight: Skylight,
        section_x: float,
        section_width: float,
        cabinet_depth: float,
    ) -> NotchSpec | None:
        """Calculate notch needed for skylight void, if any.

        Args:
            skylight: Skylight definition
            section_x: X position of section left edge
            section_width: Width of section
            cabinet_depth: Depth of cabinet (for void projection calculation)

        Returns:
            NotchSpec if skylight intersects section, None otherwise
        """
        void_x, void_width = skylight.void_at_depth(cabinet_depth)
        void_end = void_x + void_width
        section_end = section_x + section_width

        # Check for intersection
        if void_end <= section_x or void_x >= section_end:
            return None  # No intersection

        # Calculate notch dimensions relative to section
        notch_x = max(0.0, void_x - section_x)
        notch_end = min(section_width, void_end - section_x)
        notch_width = notch_end - notch_x

        return NotchSpec(
            x_offset=notch_x,
            width=notch_width,
            depth=skylight.projection_depth,
            edge="top",
        )

    def calculate_all_intersections(
        self,
        skylights: list[Skylight],
        section_x: float,
        section_width: float,
        cabinet_depth: float,
    ) -> list[NotchSpec]:
        """Calculate all notches needed for multiple skylights.

        Args:
            skylights: List of skylight definitions
            section_x: X position of section left edge
            section_width: Width of section
            cabinet_depth: Depth of cabinet

        Returns:
            List of NotchSpecs for all intersecting skylights
        """
        notches = []
        for skylight in skylights:
            notch = self.calculate_void_intersection(
                skylight, section_x, section_width, cabinet_depth
            )
            if notch is not None:
                notches.append(notch)
        return notches

    def get_sections_with_voids(
        self,
        skylights: list[Skylight],
        section_specs: list[tuple[float, float]],  # List of (x_position, width)
        cabinet_depth: float,
    ) -> dict[int, list[NotchSpec]]:
        """Map section indices to their required notches.

        Args:
            skylights: List of skylight definitions
            section_specs: List of (x_position, width) tuples for each section
            cabinet_depth: Depth of cabinet

        Returns:
            Dict mapping section index to list of NotchSpecs
        """
        result = {}
        for i, (section_x, section_width) in enumerate(section_specs):
            notches = self.calculate_all_intersections(
                skylights, section_x, section_width, cabinet_depth
            )
            if notches:
                result[i] = notches
        return result

    def check_void_exceeds_section(
        self,
        skylight: Skylight,
        section_x: float,
        section_width: float,
        cabinet_depth: float,
    ) -> bool:
        """Check if skylight void exceeds section width (warning condition).

        Returns True if the void width at cabinet depth exceeds section width.
        """
        void_x, void_width = skylight.void_at_depth(cabinet_depth)
        void_end = void_x + void_width
        section_end = section_x + section_width

        # Check if void completely contains section
        if void_x <= section_x and void_end >= section_end:
            return True
        return False


@dataclass
class OutsideCornerService:
    """Generates panels for outside (convex) corner treatments."""

    def is_outside_corner(self, wall_angle: float) -> bool:
        """Determine if an angle represents an outside corner.

        Outside corners occur when the absolute angle is greater than 90 degrees.

        Args:
            wall_angle: The wall junction angle in degrees.

        Returns:
            True if the angle represents an outside corner, False otherwise.
        """
        return abs(wall_angle) > 90

    def calculate_angled_face_panel(
        self,
        corner_config: OutsideCornerConfig,
        height: float,
        depth: float,
        material: MaterialSpec,
    ) -> Panel:
        """Generate an angled face panel for outside corner treatment.

        The angled face panel bridges the corner at the specified face_angle.

        Args:
            corner_config: Outside corner configuration with face_angle.
            height: Height of the panel in inches.
            depth: Depth of the cabinet in inches.
            material: Material specification for the panel.

        Returns:
            A Panel with DIAGONAL_FACE type and angle cut metadata.
        """
        from math import radians, tan

        # Calculate panel width based on depth and face angle
        # Width of angled panel is based on the gap created by the corner
        # For a 45-degree face, width = depth * 2 * tan(face_angle/2)
        panel_width = 2 * depth * tan(radians(corner_config.face_angle / 2))

        # Create cut metadata for the angled edges
        cut_metadata = {
            "angle_cuts": [
                {"edge": "left", "angle": corner_config.face_angle, "bevel": True},
                {"edge": "right", "angle": corner_config.face_angle, "bevel": True},
            ],
            "corner_treatment": "angled_face",
        }

        return Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=panel_width,
            height=height,
            material=material,
            cut_metadata=cut_metadata,
        )

    def calculate_filler_panel(
        self,
        corner_config: OutsideCornerConfig,
        height: float,
        material: MaterialSpec,
    ) -> Panel:
        """Generate a filler panel for butted_filler corner treatment.

        The filler panel is a simple rectangular panel with the specified width.

        Args:
            corner_config: Outside corner configuration with filler_width.
            height: Height of the panel in inches.
            material: Material specification for the panel.

        Returns:
            A Panel with FILLER type and butted_filler metadata.
        """
        cut_metadata = {
            "corner_treatment": "butted_filler",
        }

        return Panel(
            panel_type=PanelType.FILLER,
            width=corner_config.filler_width,
            height=height,
            material=material,
            cut_metadata=cut_metadata,
        )

    def generate_corner_panels(
        self,
        corner_config: OutsideCornerConfig,
        height: float,
        depth: float,
        material: MaterialSpec,
    ) -> list[Panel]:
        """Generate all panels needed for the specified corner treatment.

        Args:
            corner_config: Outside corner configuration.
            height: Cabinet height at the corner.
            depth: Cabinet depth.
            material: Material specification for panels.

        Returns:
            List of panels for the corner treatment.
        """
        if corner_config.treatment == "angled_face":
            return [
                self.calculate_angled_face_panel(corner_config, height, depth, material)
            ]
        elif corner_config.treatment == "butted_filler":
            return [self.calculate_filler_panel(corner_config, height, material)]
        elif corner_config.treatment == "wrap_around":
            # Defer wrap_around to future implementation
            # For now, fall back to angled_face
            return [
                self.calculate_angled_face_panel(corner_config, height, depth, material)
            ]
        else:
            return []

    def calculate_side_panel_angle_cut(
        self,
        wall_angle: float,
        side: str,  # "left" or "right"
    ) -> AngleCut | None:
        """Calculate angle cut for side panel at non-90-degree wall junction.

        Args:
            wall_angle: The angle of the wall junction.
            side: Which side of the junction ("left" or "right").

        Returns:
            AngleCut specification if needed, None for 90-degree junctions.
        """
        # Standard 90-degree junction needs no special cut
        if wall_angle in (90, -90, 0):
            return None

        # Calculate the cut angle (half the deviation from 90 degrees)
        deviation = abs(90 - abs(wall_angle))
        cut_angle = deviation / 2

        # Determine edge based on side
        edge: Literal["left", "right", "top", "bottom"] = (
            "right" if side == "right" else "left"
        )

        return AngleCut(
            edge=edge,
            angle=cut_angle,
            bevel=True,
        )
