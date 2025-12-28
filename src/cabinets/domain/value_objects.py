"""Value objects for the cabinet domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import Obstacle


class MaterialType(Enum):
    """Types of materials used in cabinet construction."""

    PLYWOOD = "plywood"
    MDF = "mdf"
    PARTICLE_BOARD = "particle_board"
    SOLID_WOOD = "solid_wood"


class ObstacleType(Enum):
    """Types of obstacles that cabinets must avoid."""

    WINDOW = "window"
    DOOR = "door"
    OUTLET = "outlet"
    SWITCH = "switch"
    VENT = "vent"
    SKYLIGHT = "skylight"
    CUSTOM = "custom"


class PanelType(Enum):
    """Types of panels in a cabinet."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT_SIDE = "left_side"
    RIGHT_SIDE = "right_side"
    BACK = "back"
    SHELF = "shelf"
    DIVIDER = "divider"


@dataclass(frozen=True)
class Dimensions:
    """Immutable dimensions in inches."""

    width: float
    height: float
    depth: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.depth <= 0:
            raise ValueError("All dimensions must be positive")

    @property
    def area(self) -> float:
        """Calculate surface area (width x height) in square inches."""
        return self.width * self.height

    @property
    def volume(self) -> float:
        """Calculate volume in cubic inches."""
        return self.width * self.height * self.depth


@dataclass(frozen=True)
class Position:
    """Position within the cabinet, from bottom-left corner."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("Position coordinates must be non-negative")


@dataclass(frozen=True)
class MaterialSpec:
    """Material specification for cabinet construction."""

    thickness: float
    material_type: MaterialType = MaterialType.PLYWOOD

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise ValueError("Material thickness must be positive")

    @classmethod
    def standard_3_4(cls) -> "MaterialSpec":
        """Standard 3/4 inch plywood."""
        return cls(thickness=0.75, material_type=MaterialType.PLYWOOD)

    @classmethod
    def standard_1_2(cls) -> "MaterialSpec":
        """Standard 1/2 inch plywood (often used for backs)."""
        return cls(thickness=0.5, material_type=MaterialType.PLYWOOD)


@dataclass(frozen=True)
class CutPiece:
    """A piece to be cut from sheet material."""

    width: float
    height: float
    quantity: int
    label: str
    panel_type: PanelType
    material: MaterialSpec

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Cut piece dimensions must be positive")
        if self.quantity < 1:
            raise ValueError("Quantity must be at least 1")

    @property
    def area(self) -> float:
        """Total area for all pieces of this type in square inches."""
        return self.width * self.height * self.quantity


@dataclass(frozen=True)
class Position3D:
    """3D position in space (origin at front-bottom-left of cabinet)."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0 or self.z < 0:
            raise ValueError("Position coordinates must be non-negative")


@dataclass(frozen=True)
class BoundingBox3D:
    """Axis-aligned 3D bounding box representing a panel in space."""

    origin: Position3D
    size_x: float  # Width (left to right)
    size_y: float  # Depth (front to back)
    size_z: float  # Height (bottom to top)

    def __post_init__(self) -> None:
        if self.size_x <= 0 or self.size_y <= 0 or self.size_z <= 0:
            raise ValueError("Bounding box dimensions must be positive")

    def get_vertices(self) -> list[tuple[float, float, float]]:
        """Return 8 corner vertices of the box."""
        x0, y0, z0 = self.origin.x, self.origin.y, self.origin.z
        x1, y1, z1 = x0 + self.size_x, y0 + self.size_y, z0 + self.size_z
        return [
            (x0, y0, z0),  # 0: front-bottom-left
            (x1, y0, z0),  # 1: front-bottom-right
            (x1, y1, z0),  # 2: back-bottom-right
            (x0, y1, z0),  # 3: back-bottom-left
            (x0, y0, z1),  # 4: front-top-left
            (x1, y0, z1),  # 5: front-top-right
            (x1, y1, z1),  # 6: back-top-right
            (x0, y1, z1),  # 7: back-top-left
        ]

    def get_triangles(self) -> list[tuple[int, int, int]]:
        """Return 12 triangles (as vertex indices) forming the 6 box faces.

        Winding order is counter-clockwise when viewed from outside (for correct normals).
        """
        return [
            # Bottom face (z=min)
            (0, 2, 1),
            (0, 3, 2),
            # Top face (z=max)
            (4, 5, 6),
            (4, 6, 7),
            # Front face (y=min)
            (0, 1, 5),
            (0, 5, 4),
            # Back face (y=max)
            (2, 3, 7),
            (2, 7, 6),
            # Left face (x=min)
            (0, 4, 7),
            (0, 7, 3),
            # Right face (x=max)
            (1, 2, 6),
            (1, 6, 5),
        ]


@dataclass(frozen=True)
class Point2D:
    """2D point in room coordinate space.

    Unlike Position (which is for cabinet-internal coordinates and must be
    non-negative), Point2D represents points in a room coordinate system
    where negative values are valid.
    """

    x: float
    y: float


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
class Clearance:
    """Clearance distances around an obstacle.

    Specifies the minimum space that must be kept clear around an obstacle
    in each direction. All values are in inches.

    Attributes:
        top: Clearance above the obstacle.
        bottom: Clearance below the obstacle.
        left: Clearance to the left of the obstacle.
        right: Clearance to the right of the obstacle.
    """

    top: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    right: float = 0.0

    def __post_init__(self) -> None:
        if self.top < 0 or self.bottom < 0 or self.left < 0 or self.right < 0:
            raise ValueError("Clearance values must be non-negative")


@dataclass(frozen=True)
class SectionBounds:
    """2D bounds of a cabinet section on a wall.

    Represents the rectangular area occupied by a cabinet section
    in wall-relative coordinates.

    Attributes:
        left: Horizontal offset from wall start (left edge of section).
        right: Horizontal offset from wall start (right edge of section).
        bottom: Vertical offset from floor (bottom edge of section).
        top: Vertical offset from floor (top edge of section).
    """

    left: float
    right: float
    bottom: float
    top: float

    def __post_init__(self) -> None:
        if self.right <= self.left:
            raise ValueError("right must be greater than left")
        if self.top <= self.bottom:
            raise ValueError("top must be greater than bottom")

    @property
    def width(self) -> float:
        """Width of the section bounds."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Height of the section bounds."""
        return self.top - self.bottom


@dataclass(frozen=True)
class ObstacleZone:
    """Bounding box of obstacle including clearances.

    Represents the total exclusion zone for an obstacle, which includes
    both the obstacle itself and any required clearance around it.

    Attributes:
        left: Left edge of the exclusion zone.
        right: Right edge of the exclusion zone.
        bottom: Bottom edge of the exclusion zone.
        top: Top edge of the exclusion zone.
        obstacle: Reference to the obstacle this zone represents.
    """

    left: float
    right: float
    bottom: float
    top: float
    obstacle: Obstacle

    @property
    def width(self) -> float:
        """Width of the obstacle zone."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Height of the obstacle zone."""
        return self.top - self.bottom

    def overlaps(self, other: SectionBounds) -> bool:
        """Check if this zone overlaps with a section.

        Two rectangles overlap if neither is completely to the left,
        right, above, or below the other.

        Args:
            other: The section bounds to check for overlap.

        Returns:
            True if there is any overlap, False otherwise.
        """
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.top <= other.bottom
            or self.bottom >= other.top
        )


@dataclass(frozen=True)
class CollisionResult:
    """Result of collision detection between section and obstacle zone.

    Represents a detected collision between a cabinet section and an
    obstacle zone, including the area of overlap.

    Attributes:
        zone: The obstacle zone that was collided with.
        overlap_area: Square inches of overlap between section and zone.
    """

    zone: ObstacleZone
    overlap_area: float

    def __post_init__(self) -> None:
        if self.overlap_area < 0:
            raise ValueError("overlap_area must be non-negative")


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


# Default clearances for each obstacle type
DEFAULT_CLEARANCES: dict[ObstacleType, Clearance] = {
    ObstacleType.WINDOW: Clearance(top=2.0, bottom=2.0, left=2.0, right=2.0),
    ObstacleType.DOOR: Clearance(top=0.0, bottom=0.0, left=2.0, right=2.0),
    ObstacleType.OUTLET: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.SWITCH: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.VENT: Clearance(top=4.0, bottom=4.0, left=4.0, right=4.0),
    ObstacleType.SKYLIGHT: Clearance(top=2.0, bottom=2.0, left=2.0, right=2.0),
    ObstacleType.CUSTOM: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
}


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


@dataclass
class LayoutResult:
    """Result of obstacle-aware layout calculation.

    Contains the complete result of laying out cabinet sections on a wall,
    including successfully placed sections, any warnings generated, and
    areas that were skipped.

    Attributes:
        placed_sections: List of sections that were successfully placed.
        warnings: List of warnings generated during layout.
        skipped_areas: List of areas where sections couldn't be placed.
    """

    placed_sections: list[PlacedSection]
    warnings: list[LayoutWarning]
    skipped_areas: list[SkippedArea]

    def __init__(
        self,
        placed_sections: list[PlacedSection] | None = None,
        warnings: list[LayoutWarning] | None = None,
        skipped_areas: list[SkippedArea] | None = None,
    ) -> None:
        self.placed_sections = placed_sections if placed_sections is not None else []
        self.warnings = warnings if warnings is not None else []
        self.skipped_areas = skipped_areas if skipped_areas is not None else []

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
