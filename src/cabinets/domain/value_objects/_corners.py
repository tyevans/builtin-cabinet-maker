"""Corner cabinet handling value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CornerType(str, Enum):
    """Types of corner cabinets.

    Each corner type has different footprint characteristics on the two
    walls that meet at the corner.

    Attributes:
        LAZY_SUSAN: Rotating shelf system, symmetric footprint.
        DIAGONAL: 45-degree angled face, symmetric footprint.
        BLIND: One accessible side, one blind side, asymmetric footprint.
    """

    LAZY_SUSAN = "lazy_susan"
    DIAGONAL = "diagonal"
    BLIND = "blind"


@dataclass(frozen=True)
class CornerSectionAssignment:
    """Assignment of a corner section to two adjacent walls.

    Corner cabinets occupy space on two walls that meet at a corner.
    This dataclass tracks which section is a corner, which walls it
    spans, and how much space it consumes on each wall.

    Attributes:
        section_index: Index of the section in the specs list.
        left_wall_index: Index of the wall on the left (when facing corner).
        right_wall_index: Index of the wall on the right (when facing corner).
        left_wall_footprint: Space consumed on left wall in inches.
        right_wall_footprint: Space consumed on right wall in inches.
        corner_type: Type of corner cabinet (lazy_susan, diagonal, blind).
        at_wall_end: If True, corner is at the END of left wall / START of right wall.
                     If False, it's at a custom position specified by offsets.
        left_wall_offset: Offset from left wall start (typically wall length - footprint).
        right_wall_offset: Offset from right wall start (typically 0).
    """

    section_index: int
    left_wall_index: int
    right_wall_index: int
    left_wall_footprint: float
    right_wall_footprint: float
    corner_type: CornerType
    at_wall_end: bool = True
    left_wall_offset: float = 0.0
    right_wall_offset: float = 0.0

    def __post_init__(self) -> None:
        if self.section_index < 0:
            raise ValueError("Section index must be non-negative")
        if self.left_wall_index < 0:
            raise ValueError("Left wall index must be non-negative")
        if self.right_wall_index < 0:
            raise ValueError("Right wall index must be non-negative")
        if self.left_wall_footprint <= 0:
            raise ValueError("Left wall footprint must be positive")
        if self.right_wall_footprint <= 0:
            raise ValueError("Right wall footprint must be positive")
        if self.left_wall_offset < 0:
            raise ValueError("Left wall offset must be non-negative")
        if self.right_wall_offset < 0:
            raise ValueError("Right wall offset must be non-negative")

    @property
    def total_footprint(self) -> float:
        """Total linear space consumed across both walls."""
        return self.left_wall_footprint + self.right_wall_footprint


@dataclass(frozen=True)
class WallSpaceReservation:
    """Space reserved on a wall by a corner cabinet.

    Used to track which portions of a wall are consumed by corner
    cabinets so that regular sections can be positioned correctly.

    Attributes:
        wall_index: Index of the wall.
        start_offset: Starting position of reserved space on wall.
        end_offset: Ending position of reserved space on wall.
        reserved_by_section: Index of the corner section that reserved this space.
        is_corner_start: True if this is at the start of the wall (from prev corner).
        is_corner_end: True if this is at the end of the wall (to next corner).
    """

    wall_index: int
    start_offset: float
    end_offset: float
    reserved_by_section: int
    is_corner_start: bool = False
    is_corner_end: bool = False

    def __post_init__(self) -> None:
        if self.wall_index < 0:
            raise ValueError("Wall index must be non-negative")
        if self.start_offset < 0:
            raise ValueError("Start offset must be non-negative")
        if self.end_offset < self.start_offset:
            raise ValueError("End offset must be >= start offset")
        if self.reserved_by_section < 0:
            raise ValueError("Reserved by section must be non-negative")

    @property
    def length(self) -> float:
        """Length of the reserved space."""
        return self.end_offset - self.start_offset
