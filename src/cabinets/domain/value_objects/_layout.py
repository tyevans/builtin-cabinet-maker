"""Layout and spatial arrangement value objects."""

from __future__ import annotations

from dataclasses import dataclass

from ._core_geometry import Point2D, Position3D
from ._obstacles import SectionBounds


@dataclass(frozen=True)
class WallPosition:
    """Computed position and orientation of a wall segment.

    Represents the calculated geometry of a wall based on the room's
    wall length definitions and layout.
    """

    wall_index: int
    start: Point2D
    end: Point2D
    direction: float  # Angle in degrees from positive X axis

    def __post_init__(self) -> None:
        if self.wall_index < 0:
            raise ValueError("Wall index must be non-negative")


@dataclass(frozen=True)
class GeometryError:
    """Geometry validation error.

    Represents an error detected during room geometry validation,
    such as wall intersections, closure gaps, or invalid angles.
    """

    wall_indices: tuple[int, ...]
    message: str
    error_type: str  # One of: "intersection", "closure", "invalid_angle"

    def __post_init__(self) -> None:
        valid_error_types = {"intersection", "closure", "invalid_angle"}
        if self.error_type not in valid_error_types:
            raise ValueError(
                f"error_type must be one of {valid_error_types}, got '{self.error_type}'"
            )


@dataclass(frozen=True)
class SectionTransform:
    """3D transform for positioning a cabinet section in room coordinates.

    Represents the final computed position and rotation of a cabinet section
    after it has been placed against a wall in the room.
    """

    section_index: int
    wall_index: int
    position: Position3D  # Origin point in room coordinates
    rotation_z: float  # Rotation around Z axis (degrees)

    def __post_init__(self) -> None:
        if self.section_index < 0:
            raise ValueError("Section index must be non-negative")
        if self.wall_index < 0:
            raise ValueError("Wall index must be non-negative")


@dataclass(frozen=True)
class WallSectionAssignment:
    """Assignment of a cabinet section to a wall segment.

    Represents the logical assignment of a section to a specific wall,
    including the offset distance from the wall's start point.
    """

    section_index: int
    wall_index: int
    offset_along_wall: float  # Distance from wall start

    def __post_init__(self) -> None:
        if self.section_index < 0:
            raise ValueError("Section index must be non-negative")
        if self.wall_index < 0:
            raise ValueError("Wall index must be non-negative")
        if self.offset_along_wall < 0:
            raise ValueError("Offset along wall must be non-negative")


@dataclass(frozen=True)
class FitError:
    """Fit validation error for cabinet section placement.

    Represents an error detected when validating whether cabinet sections
    fit properly on their assigned walls.
    """

    section_index: int
    wall_index: int | None  # None if wall reference invalid
    message: str
    error_type: str  # One of: "exceeds_length", "invalid_wall_reference", "overlap"

    def __post_init__(self) -> None:
        if self.section_index < 0:
            raise ValueError("Section index must be non-negative")
        if self.wall_index is not None and self.wall_index < 0:
            raise ValueError("Wall index must be non-negative when provided")
        valid_error_types = {"exceeds_length", "invalid_wall_reference", "overlap"}
        if self.error_type not in valid_error_types:
            raise ValueError(
                f"error_type must be one of {valid_error_types}, got '{self.error_type}'"
            )


@dataclass(frozen=True)
class ValidRegion:
    """A region on wall where sections can be placed.

    Represents a rectangular area on a wall that is free from obstacles
    and available for cabinet placement.

    Attributes:
        left: Left edge of the valid region.
        right: Right edge of the valid region.
        bottom: Bottom edge of the valid region.
        top: Top edge of the valid region.
        region_type: Type of region - "full", "lower", "upper", or "gap".
    """

    left: float
    right: float
    bottom: float
    top: float
    region_type: str  # "full", "lower", "upper", "gap"

    def __post_init__(self) -> None:
        if self.right <= self.left:
            raise ValueError("right must be greater than left")
        if self.top <= self.bottom:
            raise ValueError("top must be greater than bottom")
        valid_region_types = {"full", "lower", "upper", "gap"}
        if self.region_type not in valid_region_types:
            raise ValueError(
                f"region_type must be one of {valid_region_types}, got '{self.region_type}'"
            )

    @property
    def width(self) -> float:
        """Width of the valid region."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Height of the valid region."""
        return self.top - self.bottom


@dataclass(frozen=True)
class PlacedSection:
    """A section with its calculated placement on a wall.

    Represents a cabinet section that has been successfully placed on a wall,
    including its position, height mode, and shelf count.

    Attributes:
        section_index: Original section index from config.
        bounds: The 2D bounds of the section on the wall.
        height_mode: How the section uses wall height - "full", "lower", or "upper".
        shelves: Number of shelves in this section.
    """

    section_index: int
    bounds: SectionBounds
    height_mode: str
    shelves: int

    def __post_init__(self) -> None:
        if self.section_index < 0:
            raise ValueError("section_index must be non-negative")
        valid_height_modes = {"full", "lower", "upper", "gap"}
        if self.height_mode not in valid_height_modes:
            raise ValueError(
                f"height_mode must be one of {valid_height_modes}, got '{self.height_mode}'"
            )
        if self.shelves < 0:
            raise ValueError("shelves must be non-negative")


@dataclass(frozen=True)
class LayoutWarning:
    """Warning generated during layout calculation.

    Represents a non-fatal issue encountered during layout calculation,
    along with an optional suggestion for addressing it.

    Attributes:
        message: Description of the warning condition.
        suggestion: Optional suggestion for resolving the warning.
    """

    message: str
    suggestion: str | None = None


@dataclass(frozen=True)
class SkippedArea:
    """An area that couldn't accommodate a section.

    Represents an area where a cabinet section was requested but could not
    be placed, typically due to obstacles or space constraints.

    Attributes:
        bounds: The bounds of the area that was skipped.
        reason: Explanation of why the area was skipped.
    """

    bounds: SectionBounds
    reason: str


@dataclass(frozen=True)
class LayoutResult:
    """Result of obstacle-aware layout calculation.

    Contains the complete result of laying out cabinet sections on a wall,
    including successfully placed sections, any warnings generated, and
    areas that were skipped.

    Attributes:
        placed_sections: Tuple of sections that were successfully placed.
        warnings: Tuple of warnings generated during layout.
        skipped_areas: Tuple of areas where sections couldn't be placed.
    """

    placed_sections: tuple[PlacedSection, ...] = ()
    warnings: tuple[LayoutWarning, ...] = ()
    skipped_areas: tuple[SkippedArea, ...] = ()

    @classmethod
    def create(
        cls,
        placed_sections: list[PlacedSection] | None = None,
        warnings: list[LayoutWarning] | None = None,
        skipped_areas: list[SkippedArea] | None = None,
    ) -> "LayoutResult":
        """Factory method for creating LayoutResult with defaults.

        Accepts lists for convenience and converts them to tuples internally.

        Args:
            placed_sections: List of sections that were successfully placed.
            warnings: List of warnings generated during layout.
            skipped_areas: List of areas where sections couldn't be placed.

        Returns:
            A new immutable LayoutResult instance.
        """
        return cls(
            placed_sections=tuple(placed_sections or []),
            warnings=tuple(warnings or []),
            skipped_areas=tuple(skipped_areas or []),
        )

    @property
    def has_warnings(self) -> bool:
        """Check if layout produced any warnings."""
        return len(self.warnings) > 0

    @property
    def has_skipped_areas(self) -> bool:
        """Check if any areas were skipped."""
        return len(self.skipped_areas) > 0

    @property
    def total_placed_width(self) -> float:
        """Calculate total width of all placed sections."""
        return sum(s.bounds.width for s in self.placed_sections)

    @property
    def section_count(self) -> int:
        """Number of sections successfully placed."""
        return len(self.placed_sections)
