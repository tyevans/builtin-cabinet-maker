"""Room-aware cabinet layout service.

This module provides the RoomLayoutService for calculating cabinet positions
within room geometry, including wall assignments and 3D transforms for STL
generation.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..components.corner import (
    CornerFootprint,
    calculate_blind_corner_footprint,
    calculate_diagonal_footprint,
    calculate_lazy_susan_footprint,
)
from ..section_resolver import SectionSpec
from ..value_objects import (
    CornerSectionAssignment,
    CornerType,
    FitError,
    Position3D,
    SectionTransform,
    WallSectionAssignment,
    WallSpaceReservation,
)

if TYPE_CHECKING:
    from ..entities import Room

__all__ = ["RoomLayoutService"]


class RoomLayoutService:
    """Calculates cabinet positions within room geometry.

    This service handles the assignment of cabinet sections to walls
    within a room and computes the 3D transforms needed for STL generation.
    """

    def assign_sections_to_walls(
        self,
        room: Room,
        section_specs: list[SectionSpec],
    ) -> list[WallSectionAssignment]:
        """Assign cabinet sections to wall segments.

        Each SectionSpec may have an optional 'wall' attribute:
        - If wall is None or not specified, assign to wall index 0
        - If wall is an int, it's the wall index (0-based)
        - If wall is a str, find the wall by name

        For each wall, sections are placed sequentially from the wall's start.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications to assign.

        Returns:
            List of WallSectionAssignment objects with computed positions.

        Raises:
            ValueError: If a wall reference is invalid.
        """
        if not section_specs:
            return []

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # Group sections by wall index
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec in enumerate(section_specs):
            wall_idx = self._resolve_wall_index(
                spec.wall, len(room.walls), wall_name_to_index
            )
            if wall_idx not in wall_sections:
                wall_sections[wall_idx] = []
            wall_sections[wall_idx].append((section_idx, spec))

        # Create assignments with sequential offsets per wall
        assignments: list[WallSectionAssignment] = []

        for wall_idx, sections in wall_sections.items():
            current_offset = 0.0

            for section_idx, spec in sections:
                # For fixed width sections, use the width directly
                # For fill sections, we need to resolve the width
                if spec.is_fill:
                    # Calculate fill width based on remaining space on this wall
                    wall_length = room.walls[wall_idx].length
                    fixed_widths = sum(
                        s.fixed_width or 0.0 for _, s in sections if not s.is_fill
                    )
                    fill_count = sum(1 for _, s in sections if s.is_fill)
                    remaining = wall_length - fixed_widths
                    section_width = remaining / fill_count if fill_count > 0 else 0.0
                else:
                    section_width = spec.fixed_width or 0.0

                assignments.append(
                    WallSectionAssignment(
                        section_index=section_idx,
                        wall_index=wall_idx,
                        offset_along_wall=current_offset,
                    )
                )
                current_offset += section_width

        # Sort by section index to maintain original order
        assignments.sort(key=lambda a: a.section_index)
        return assignments

    def compute_section_transforms(
        self,
        room: Room,
        assignments: list[WallSectionAssignment],
        section_specs: list[SectionSpec],
    ) -> list[SectionTransform]:
        """Compute 3D position and rotation for each section.

        Used for STL generation with correct spatial layout.

        Args:
            room: The room containing wall segments.
            assignments: Wall assignments for each section.
            section_specs: Original section specifications (for width calculation).

        Returns:
            List of SectionTransform objects with 3D positions and rotations.
        """
        if not assignments:
            return []

        wall_positions = room.get_wall_positions()

        # Build wall name to index mapping for width resolution
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # Pre-compute section widths per wall for fill sections
        # (width computation handled per-assignment below)
        _ = self._compute_section_widths_per_wall(
            room, section_specs, wall_name_to_index
        )

        # First pass: compute raw positions (may be negative)
        raw_positions: list[
            tuple[float, float, float, float]
        ] = []  # (x, y, z, rotation)

        for assignment in assignments:
            wall_pos = wall_positions[assignment.wall_index]

            # Calculate position along the wall
            direction_rad = math.radians(wall_pos.direction)

            # Calculate X, Y position based on wall start and offset along wall
            x = wall_pos.start.x + assignment.offset_along_wall * math.cos(
                direction_rad
            )
            y = wall_pos.start.y + assignment.offset_along_wall * math.sin(
                direction_rad
            )

            # Z position starts at floor level
            z = 0.0

            # Rotation is based on wall direction
            # Wall direction is the angle the wall runs along.
            # Cabinet back is at y=0, front at y=depth (facing +Y originally).
            # To face "into the room" (perpendicular to wall, toward interior),
            # we negate the direction so the cabinet rotates the opposite way.
            rotation_z = (-wall_pos.direction) % 360

            raw_positions.append((x, y, z, rotation_z))

        # Second pass: create transforms, mirroring negative coordinates to positive
        # This keeps the origin at (0,0) and flips negative positions to positive space
        transforms: list[SectionTransform] = []
        for assignment, (x, y, z, rotation_z) in zip(assignments, raw_positions):
            # Mirror negative coordinates to positive (abs value)
            final_x = abs(x)
            final_y = abs(y)
            position = Position3D(x=final_x, y=final_y, z=z)

            transforms.append(
                SectionTransform(
                    section_index=assignment.section_index,
                    wall_index=assignment.wall_index,
                    position=position,
                    rotation_z=rotation_z,
                )
            )

        return transforms

    def validate_fit(
        self,
        room: Room,
        section_specs: list[SectionSpec],
    ) -> list[FitError]:
        """Check that sections fit on their assigned walls.

        Validates:
        - invalid_wall_reference: Wall name/index doesn't exist
        - exceeds_length: Total section widths on a wall exceed wall length
        - overlap: Sections overlap on the same wall

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications to validate.

        Returns:
            List of FitError objects describing any issues found.
        """
        errors: list[FitError] = []

        if not section_specs:
            return errors

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # First pass: check for invalid wall references
        valid_sections: list[tuple[int, SectionSpec, int]] = []
        for section_idx, spec in enumerate(section_specs):
            try:
                wall_idx = self._resolve_wall_index(
                    spec.wall, len(room.walls), wall_name_to_index
                )
                valid_sections.append((section_idx, spec, wall_idx))
            except ValueError as e:
                errors.append(
                    FitError(
                        section_index=section_idx,
                        wall_index=None,
                        message=str(e),
                        error_type="invalid_wall_reference",
                    )
                )

        # Group valid sections by wall
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec, wall_idx in valid_sections:
            if wall_idx not in wall_sections:
                wall_sections[wall_idx] = []
            wall_sections[wall_idx].append((section_idx, spec))

        # Check each wall for length and overlap issues
        for wall_idx, sections in wall_sections.items():
            wall_length = room.walls[wall_idx].length

            # Calculate widths for this wall's sections
            fixed_widths = sum(
                s.fixed_width or 0.0 for _, s in sections if not s.is_fill
            )
            fill_count = sum(1 for _, s in sections if s.is_fill)

            # Calculate remaining space for fill sections
            remaining_for_fills = wall_length - fixed_widths

            if remaining_for_fills < 0:
                # Fixed widths alone exceed wall length
                errors.append(
                    FitError(
                        section_index=sections[0][0],  # First section on this wall
                        wall_index=wall_idx,
                        message=(
                            f'Fixed section widths ({fixed_widths:.2f}") exceed '
                            f'wall length ({wall_length:.2f}") on wall {wall_idx}'
                        ),
                        error_type="exceeds_length",
                    )
                )
                continue

            # If there are fill sections, check if they would have valid width
            if fill_count > 0:
                fill_width = remaining_for_fills / fill_count
                if fill_width <= 0:
                    errors.append(
                        FitError(
                            section_index=sections[0][0],
                            wall_index=wall_idx,
                            message=(
                                f"Fill sections would have zero or negative width on wall {wall_idx}"
                            ),
                            error_type="exceeds_length",
                        )
                    )
                    continue

            # Calculate total width (all sections)
            total_width = fixed_widths
            if fill_count > 0:
                total_width += fill_count * (remaining_for_fills / fill_count)

            # Check if total exceeds wall length (with tolerance)
            if total_width > wall_length + 0.001:
                errors.append(
                    FitError(
                        section_index=sections[0][0],
                        wall_index=wall_idx,
                        message=(
                            f'Total section width ({total_width:.2f}") exceeds '
                            f'wall length ({wall_length:.2f}") on wall {wall_idx}'
                        ),
                        error_type="exceeds_length",
                    )
                )

        return errors

    def detect_corner_sections(
        self,
        section_specs: list[SectionSpec],
    ) -> list[tuple[int, str]]:
        """Detect which sections are corner components.

        A section is a corner component if its component_config contains a
        'component' key that starts with 'corner.' (e.g., 'corner.lazy_susan',
        'corner.diagonal', 'corner.blind').

        Args:
            section_specs: List of section specifications.

        Returns:
            List of tuples (section_index, corner_component_id) for each
            corner section detected.
        """
        corners: list[tuple[int, str]] = []
        for idx, spec in enumerate(section_specs):
            component_id = spec.component_config.get("component", "")
            if isinstance(component_id, str) and component_id.startswith("corner."):
                corners.append((idx, component_id))
        return corners

    def find_wall_corners(
        self,
        room: Room,
    ) -> list[tuple[int, int, int]]:
        """Find corners between adjacent walls.

        A corner exists when one wall's angle is 90 (right turn) or -90 (left turn).
        The corner is at the junction between that wall and the previous wall.

        For a right turn (angle=90), when facing the corner:
        - Left wall is the wall before the turn (current wall index - 1)
        - Right wall is the wall at the turn (current wall index)

        For a left turn (angle=-90), the orientation is reversed.

        Args:
            room: The room containing wall segments.

        Returns:
            List of tuples (left_wall_index, right_wall_index, angle) for each
            corner detected. The angle is 90 or -90 indicating turn direction.
        """
        corners: list[tuple[int, int, int]] = []

        for i, wall in enumerate(room.walls):
            if wall.angle in (90, -90):
                # Wall with angle != 0 creates a corner with the previous wall
                # For wall[i] with angle 90 or -90, the corner is between
                # wall[i-1] (ends at corner) and wall[i] (starts at corner)
                left_wall_idx = (i - 1) % len(room.walls)
                right_wall_idx = i
                corners.append((left_wall_idx, right_wall_idx, int(wall.angle)))

        return corners

    def calculate_corner_footprint(
        self,
        component_id: str,
        component_config: dict,
        depth: float,
    ) -> CornerFootprint:
        """Calculate the footprint for a corner component.

        Uses the appropriate footprint calculation function based on the
        corner type extracted from the component_id.

        Args:
            component_id: The component ID (e.g., 'corner.lazy_susan').
            component_config: The component configuration dictionary.
            depth: The cabinet depth in inches.

        Returns:
            CornerFootprint with left and right wall consumption.

        Raises:
            ValueError: If the corner type is unknown.
        """
        if component_id == "corner.lazy_susan":
            door_clearance = component_config.get("door_clearance", 2.0)
            return calculate_lazy_susan_footprint(depth, door_clearance)

        elif component_id == "corner.diagonal":
            return calculate_diagonal_footprint(depth)

        elif component_id == "corner.blind":
            accessible_width = component_config.get("accessible_width", 24.0)
            filler_width = component_config.get("filler_width", 3.0)
            blind_side = component_config.get("blind_side", "left")
            return calculate_blind_corner_footprint(
                depth, accessible_width, filler_width, blind_side
            )

        else:
            raise ValueError(f"Unknown corner component type: {component_id}")

    def get_corner_type(self, component_id: str) -> CornerType:
        """Map component ID to CornerType enum.

        Args:
            component_id: The component ID (e.g., 'corner.lazy_susan').

        Returns:
            The corresponding CornerType enum value.

        Raises:
            ValueError: If the corner type is unknown.
        """
        mapping = {
            "corner.lazy_susan": CornerType.LAZY_SUSAN,
            "corner.diagonal": CornerType.DIAGONAL,
            "corner.blind": CornerType.BLIND,
        }
        if component_id not in mapping:
            raise ValueError(f"Unknown corner component type: {component_id}")
        return mapping[component_id]

    def assign_corner_sections(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        default_depth: float = 24.0,
    ) -> tuple[list[CornerSectionAssignment], list[WallSpaceReservation]]:
        """Assign corner sections to wall junctions and calculate reservations.

        This method:
        1. Detects which sections are corner components
        2. Finds corners between walls in the room
        3. Matches corner sections to wall corners based on the 'wall' attribute
        4. Calculates footprints and creates space reservations

        For corner placement, the section's 'wall' attribute indicates which wall
        junction to use. If a section specifies wall N, and wall N has a corner
        (angle 90 or -90), the corner cabinet is placed at that junction.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications.
            default_depth: Default cabinet depth if not specified.

        Returns:
            A tuple of:
            - List of CornerSectionAssignment for corner sections
            - List of WallSpaceReservation for space consumed on each wall
        """
        corner_sections = self.detect_corner_sections(section_specs)
        if not corner_sections:
            return [], []

        wall_corners = self.find_wall_corners(room)
        if not wall_corners:
            return [], []

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        assignments: list[CornerSectionAssignment] = []
        reservations: list[WallSpaceReservation] = []

        for section_idx, component_id in corner_sections:
            spec = section_specs[section_idx]

            # Resolve which wall the section is assigned to
            try:
                wall_idx = self._resolve_wall_index(
                    spec.wall, len(room.walls), wall_name_to_index
                )
            except ValueError:
                continue

            # Find if this wall has a corner (is the right wall of a corner)
            corner_info = None
            for left_wall, right_wall, angle in wall_corners:
                if right_wall == wall_idx:
                    corner_info = (left_wall, right_wall, angle)
                    break

            if corner_info is None:
                # No corner at this wall junction, skip
                continue

            left_wall_idx, right_wall_idx, angle = corner_info

            # Get depth from spec or default
            depth = spec.depth if spec.depth is not None else default_depth

            # Calculate footprint
            footprint = self.calculate_corner_footprint(
                component_id, spec.component_config, depth
            )

            # Determine left/right wall footprint based on angle
            # For angle 90 (right turn), the standard orientation applies
            # For angle -90 (left turn), swap left and right
            if angle == 90:
                left_fp = footprint.left_wall
                right_fp = footprint.right_wall
            else:  # angle == -90
                left_fp = footprint.right_wall
                right_fp = footprint.left_wall

            # Get wall lengths for offset calculation
            left_wall_length = room.walls[left_wall_idx].length

            # Corner is at the END of left wall and START of right wall
            left_wall_offset = left_wall_length - left_fp
            right_wall_offset = 0.0

            # Create assignment
            assignment = CornerSectionAssignment(
                section_index=section_idx,
                left_wall_index=left_wall_idx,
                right_wall_index=right_wall_idx,
                left_wall_footprint=left_fp,
                right_wall_footprint=right_fp,
                corner_type=self.get_corner_type(component_id),
                at_wall_end=True,
                left_wall_offset=left_wall_offset,
                right_wall_offset=right_wall_offset,
            )
            assignments.append(assignment)

            # Create reservations for both walls
            # Left wall: reserved space at the end
            reservations.append(
                WallSpaceReservation(
                    wall_index=left_wall_idx,
                    start_offset=left_wall_offset,
                    end_offset=left_wall_length,
                    reserved_by_section=section_idx,
                    is_corner_start=False,
                    is_corner_end=True,
                )
            )

            # Right wall: reserved space at the start
            reservations.append(
                WallSpaceReservation(
                    wall_index=right_wall_idx,
                    start_offset=0.0,
                    end_offset=right_fp,
                    reserved_by_section=section_idx,
                    is_corner_start=True,
                    is_corner_end=False,
                )
            )

        return assignments, reservations

    def assign_sections_to_walls_with_corners(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        default_depth: float = 24.0,
    ) -> tuple[
        list[WallSectionAssignment],
        list[CornerSectionAssignment],
        list[WallSpaceReservation],
    ]:
        """Assign sections to walls, handling corner cabinets specially.

        This method extends assign_sections_to_walls to handle corner cabinets
        that span two walls. Corner sections are assigned first, reserving space
        on both walls they occupy. Regular sections are then assigned to the
        remaining available space.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications.
            default_depth: Default cabinet depth for corner calculations.

        Returns:
            A tuple of:
            - List of WallSectionAssignment for regular sections
            - List of CornerSectionAssignment for corner sections
            - List of WallSpaceReservation for corner-reserved space
        """
        if not section_specs:
            return [], [], []

        # First, handle corner sections
        corner_assignments, reservations = self.assign_corner_sections(
            room, section_specs, default_depth
        )

        # Build a set of section indices that are corners
        corner_section_indices = {ca.section_index for ca in corner_assignments}

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # Build reservation lookup: wall_index -> list of reservations
        wall_reservations: dict[int, list[WallSpaceReservation]] = {}
        for res in reservations:
            if res.wall_index not in wall_reservations:
                wall_reservations[res.wall_index] = []
            wall_reservations[res.wall_index].append(res)

        # Group non-corner sections by wall index
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec in enumerate(section_specs):
            if section_idx in corner_section_indices:
                continue  # Skip corner sections

            wall_idx = self._resolve_wall_index(
                spec.wall, len(room.walls), wall_name_to_index
            )
            if wall_idx not in wall_sections:
                wall_sections[wall_idx] = []
            wall_sections[wall_idx].append((section_idx, spec))

        # Calculate available space per wall after corner reservations
        def get_available_start(wall_idx: int) -> float:
            """Get the starting offset after any corner-start reservations."""
            if wall_idx not in wall_reservations:
                return 0.0
            for res in wall_reservations[wall_idx]:
                if res.is_corner_start:
                    return res.end_offset
            return 0.0

        def get_available_end(wall_idx: int) -> float:
            """Get the ending offset before any corner-end reservations."""
            wall_length = room.walls[wall_idx].length
            if wall_idx not in wall_reservations:
                return wall_length
            for res in wall_reservations[wall_idx]:
                if res.is_corner_end:
                    return res.start_offset
            return wall_length

        # Create assignments with sequential offsets per wall, respecting reservations
        assignments: list[WallSectionAssignment] = []

        for wall_idx, sections in wall_sections.items():
            available_start = get_available_start(wall_idx)
            available_end = get_available_end(wall_idx)
            available_length = available_end - available_start

            current_offset = available_start

            for section_idx, spec in sections:
                # For fixed width sections, use the width directly
                # For fill sections, calculate based on available space
                if spec.is_fill:
                    fixed_widths = sum(
                        s.fixed_width or 0.0 for _, s in sections if not s.is_fill
                    )
                    fill_count = sum(1 for _, s in sections if s.is_fill)
                    remaining = available_length - fixed_widths
                    section_width = remaining / fill_count if fill_count > 0 else 0.0
                else:
                    section_width = spec.fixed_width or 0.0

                assignments.append(
                    WallSectionAssignment(
                        section_index=section_idx,
                        wall_index=wall_idx,
                        offset_along_wall=current_offset,
                    )
                )
                current_offset += section_width

        # Sort by section index to maintain original order
        assignments.sort(key=lambda a: a.section_index)

        return assignments, corner_assignments, reservations

    def _resolve_wall_index(
        self,
        wall_ref: str | int | None,
        num_walls: int,
        wall_name_to_index: dict[str, int],
    ) -> int:
        """Resolve a wall reference to a wall index.

        Args:
            wall_ref: Wall reference (None, int index, or string name).
            num_walls: Total number of walls in the room.
            wall_name_to_index: Mapping from wall names to indices.

        Returns:
            Wall index (0-based).

        Raises:
            ValueError: If the wall reference is invalid.
        """
        if wall_ref is None:
            return 0

        if isinstance(wall_ref, int):
            if wall_ref < 0 or wall_ref >= num_walls:
                raise ValueError(
                    f"Wall index {wall_ref} is out of range (0-{num_walls - 1})"
                )
            return wall_ref

        if isinstance(wall_ref, str):
            if wall_ref not in wall_name_to_index:
                raise ValueError(f"Wall name '{wall_ref}' not found")
            return wall_name_to_index[wall_ref]

        raise ValueError(f"Invalid wall reference type: {type(wall_ref)}")

    def _compute_section_widths_per_wall(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        wall_name_to_index: dict[str, int],
    ) -> dict[int, list[float]]:
        """Compute resolved section widths grouped by wall.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications.
            wall_name_to_index: Mapping from wall names to indices.

        Returns:
            Dictionary mapping wall index to list of section widths.
        """
        # Group sections by wall
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec in enumerate(section_specs):
            try:
                wall_idx = self._resolve_wall_index(
                    spec.wall, len(room.walls), wall_name_to_index
                )
                if wall_idx not in wall_sections:
                    wall_sections[wall_idx] = []
                wall_sections[wall_idx].append((section_idx, spec))
            except ValueError:
                continue

        # Compute widths per wall
        result: dict[int, list[float]] = {}
        for wall_idx, sections in wall_sections.items():
            wall_length = room.walls[wall_idx].length
            fixed_widths = sum(
                s.fixed_width or 0.0 for _, s in sections if not s.is_fill
            )
            fill_count = sum(1 for _, s in sections if s.is_fill)
            remaining = wall_length - fixed_widths
            fill_width = remaining / fill_count if fill_count > 0 else 0.0

            widths: list[float] = []
            for _, spec in sections:
                if spec.is_fill:
                    widths.append(fill_width)
                else:
                    widths.append(spec.fixed_width or 0.0)

            result[wall_idx] = widths

        return result
