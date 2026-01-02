"""Section width resolver service for room layouts.

Handles "fill" width calculation for sections that should expand
to fill remaining wall space, accounting for other sections on
the same wall.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cabinets.domain.entities import Room, WallSegment
    from cabinets.domain.section_resolver import SectionSpec


class SectionWidthResolverService:
    """Service for resolving section widths in room context.

    Handles "fill" width calculation for sections that should expand
    to fill remaining wall space, accounting for other sections on
    the same wall.

    This service was extracted from GenerateLayoutCommand._resolve_section_width()
    and _get_wall_index_for_spec() methods to enable easier testing and reuse.
    """

    def resolve_width(
        self,
        section_spec: "SectionSpec",
        wall_segment: "WallSegment",
        all_specs: "list[SectionSpec]",
        room: "Room",
    ) -> float:
        """Resolve the width for a section spec on a given wall.

        For fixed widths, returns the width directly.
        For fill widths, calculates based on remaining space on the wall.

        Args:
            section_spec: Section specification to resolve.
            wall_segment: Wall segment this section is on.
            all_specs: All section specifications (for fill calculation).
            room: Room containing the walls.

        Returns:
            Resolved section width in inches.
        """
        if not section_spec.is_fill:
            return section_spec.fixed_width or 0.0

        # Find wall index for this spec
        wall_index = self.get_wall_index(section_spec, room)

        # Find all sections on the same wall
        sections_on_wall = [
            s for s in all_specs if self.get_wall_index(s, room) == wall_index
        ]

        # Calculate fixed widths and fill count
        fixed_widths = sum(
            s.fixed_width or 0.0 for s in sections_on_wall if not s.is_fill
        )
        fill_count = sum(1 for s in sections_on_wall if s.is_fill)

        # Calculate fill width
        remaining = wall_segment.length - fixed_widths
        return remaining / fill_count if fill_count > 0 else 0.0

    def get_wall_index(self, spec: "SectionSpec", room: "Room") -> int:
        """Get the wall index for a section spec.

        Resolves wall specification (None → 0, int → direct, str → lookup by name)
        to a numeric wall index.

        Args:
            spec: Section specification.
            room: Room containing the walls.

        Returns:
            Wall index (0-based).
        """
        if spec.wall is None:
            return 0

        if isinstance(spec.wall, int):
            return spec.wall

        # Look up by name
        for i, wall in enumerate(room.walls):
            if wall.name == spec.wall:
                return i

        return 0  # Default to first wall if not found
