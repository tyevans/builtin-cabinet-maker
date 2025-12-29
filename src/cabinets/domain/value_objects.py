"""Value objects for the cabinet domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import radians, tan
from typing import TYPE_CHECKING, Any, Literal

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

    # Structural panels
    TOP = "top"
    BOTTOM = "bottom"
    LEFT_SIDE = "left_side"
    RIGHT_SIDE = "right_side"
    BACK = "back"
    SHELF = "shelf"
    DIVIDER = "divider"
    HORIZONTAL_DIVIDER = "horizontal_divider"
    DOOR = "door"
    DRAWER_FRONT = "drawer_front"
    DRAWER_SIDE = "drawer_side"
    DRAWER_BOX_FRONT = "drawer_box_front"
    DRAWER_BOTTOM = "drawer_bottom"
    DIAGONAL_FACE = "diagonal_face"
    FILLER = "filler"

    # Decorative panels (FRD-12)
    ARCH_HEADER = "arch_header"
    FACE_FRAME_RAIL = "face_frame_rail"
    FACE_FRAME_STILE = "face_frame_stile"
    LIGHT_RAIL = "light_rail"
    NAILER = "nailer"
    TOE_KICK = "toe_kick"
    VALANCE = "valance"

    # Desk panels (FRD-18)
    DESKTOP = "desktop"
    WATERFALL_EDGE = "waterfall_edge"
    KEYBOARD_TRAY = "keyboard_tray"
    KEYBOARD_ENCLOSURE = "keyboard_enclosure"
    MODESTY_PANEL = "modesty_panel"
    WIRE_CHASE = "wire_chase"

    # Cable routing (shared FRD-18/FRD-19)
    CABLE_CHASE = "cable_chase"


class SectionType(Enum):
    """Types of cabinet sections.

    Defines the different types of cabinet sections that can be created,
    each with its own visual and functional characteristics.

    Attributes:
        OPEN: Open shelving without doors or drawers.
        DOORED: Section with cabinet doors.
        DRAWERS: Section containing drawers.
        CUBBY: Small open compartment, typically square.
    """

    OPEN = "open"
    DOORED = "doored"
    DRAWERS = "drawers"
    CUBBY = "cubby"


class GrainDirection(str, Enum):
    """Grain direction constraint for cut pieces.

    Controls whether a piece can be rotated during bin packing optimization.

    Attributes:
        NONE: No grain constraint, piece can rotate freely.
        LENGTH: Grain runs parallel to piece length (longest dimension).
        WIDTH: Grain runs parallel to piece width (shortest dimension).
    """

    NONE = "none"
    LENGTH = "length"
    WIDTH = "width"


class JointType(str, Enum):
    """Types of woodworking joints for panel connections.

    Defines the different joinery methods that can be used to connect
    cabinet panels. Each type has specific dimension calculations and
    hardware requirements.

    Attributes:
        DADO: Groove cut into one panel to receive another (shelf-to-side).
        RABBET: L-shaped cut along panel edge (back panel-to-case).
        POCKET_SCREW: Angled screw holes for face frame assembly.
        DOWEL: Cylindrical pins for alignment and strength.
        BISCUIT: Football-shaped spline for alignment.
        BUTT: Simple butt joint with mechanical fasteners.
    """

    DADO = "dado"
    RABBET = "rabbet"
    POCKET_SCREW = "pocket_screw"
    DOWEL = "dowel"
    BISCUIT = "biscuit"
    BUTT = "butt"


# --- FRD-15 Infrastructure Integration Value Objects ---


class LightingType(str, Enum):
    """Types of cabinet lighting fixtures.

    Defines the different lighting options that can be integrated
    into cabinet infrastructure.

    Attributes:
        LED_STRIP: Linear LED strip lighting, typically for under-cabinet use.
        PUCK_LIGHT: Circular puck-style lights for focused illumination.
        ACCENT: Accent lighting for display or decorative purposes.
    """

    LED_STRIP = "led_strip"
    PUCK_LIGHT = "puck_light"
    ACCENT = "accent"


class LightingLocation(str, Enum):
    """Locations for cabinet lighting installation.

    Specifies where lighting can be mounted relative to the cabinet.

    Attributes:
        UNDER_CABINET: Mounted underneath the cabinet bottom panel.
        IN_CABINET: Mounted inside the cabinet for interior illumination.
        ABOVE_CABINET: Mounted above the cabinet for uplighting.
    """

    UNDER_CABINET = "under_cabinet"
    IN_CABINET = "in_cabinet"
    ABOVE_CABINET = "above_cabinet"


class OutletType(str, Enum):
    """Types of electrical outlets for cabinet integration.

    Defines the different outlet configurations that may require
    cutouts in cabinet panels.

    Attributes:
        SINGLE: Single electrical outlet.
        DOUBLE: Double (duplex) electrical outlet.
        GFI: Ground fault interrupter outlet (required near water sources).
    """

    SINGLE = "single"
    DOUBLE = "double"
    GFI = "gfi"


class GrommetSize(float, Enum):
    """Standard grommet sizes for cable management.

    Defines the standard diameters for cable pass-through grommets
    in inches.

    Attributes:
        SMALL: 2.0 inch diameter, for single cables.
        MEDIUM: 2.5 inch diameter, for multiple cables.
        LARGE: 3.0 inch diameter, for cable bundles.
    """

    SMALL = 2.0
    MEDIUM = 2.5
    LARGE = 3.0


class CutoutShape(str, Enum):
    """Shape of panel cutouts.

    Defines the geometric shape of cutouts in cabinet panels.

    Attributes:
        RECTANGULAR: Rectangular cutout (outlets, vents).
        CIRCULAR: Circular cutout (grommets, wire holes).
    """

    RECTANGULAR = "rectangular"
    CIRCULAR = "circular"


class VentilationPattern(str, Enum):
    """Patterns for ventilation cutouts.

    Defines the different patterns that can be used for
    ventilation panels or cutouts.

    Attributes:
        GRID: Grid pattern of holes for maximum airflow.
        SLOT: Horizontal or vertical slots for directed airflow.
        CIRCULAR: Array of circular holes for aesthetic ventilation.
    """

    GRID = "grid"
    SLOT = "slot"
    CIRCULAR = "circular"


# --- FRD-17 Installation Support Value Objects ---


class WallType(str, Enum):
    """Wall construction type for installation planning.

    Defines the different wall types that affect fastener selection
    and mounting hardware recommendations.

    Attributes:
        DRYWALL: Standard drywall/gypsum board over wood studs.
        PLASTER: Traditional plaster over lath construction.
        CONCRETE: Solid poured concrete walls.
        CMU: Concrete masonry unit (cinder block) walls.
        BRICK: Solid or veneer brick walls.
    """

    DRYWALL = "drywall"
    PLASTER = "plaster"
    CONCRETE = "concrete"
    CMU = "cmu"
    BRICK = "brick"


class MountingSystem(str, Enum):
    """Cabinet mounting method.

    Defines the different mounting systems that can be used
    to secure cabinets to walls.

    Attributes:
        DIRECT_TO_STUD: Direct mounting through cabinet back into wall studs.
        FRENCH_CLEAT: 45-degree beveled cleat system for secure mounting.
        HANGING_RAIL: Metal rail system for cabinet suspension and adjustment.
        TOGGLE_BOLT: Heavy-duty toggle bolt anchors for non-stud locations.
    """

    DIRECT_TO_STUD = "direct_to_stud"
    FRENCH_CLEAT = "french_cleat"
    HANGING_RAIL = "hanging_rail"
    TOGGLE_BOLT = "toggle_bolt"


class LoadCategory(str, Enum):
    """Expected load category for capacity calculations.

    Defines the expected load per linear foot for cabinets,
    which affects mounting hardware requirements.

    Attributes:
        LIGHT: Light loads, approximately 15 lbs per linear foot.
        MEDIUM: Medium loads, approximately 30 lbs per linear foot.
        HEAVY: Heavy loads, approximately 50 lbs per linear foot.
    """

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


@dataclass(frozen=True)
class MountingPoint:
    """A single mounting point on the cabinet.

    Represents a specific location where the cabinet will be
    fastened to the wall, including stud alignment information
    and fastener specifications.

    Attributes:
        x_position: Distance from cabinet left edge in inches.
        y_position: Distance from cabinet bottom in inches.
        hits_stud: True if this mounting point aligns with a wall stud.
        fastener_type: Type of fastener (e.g., screw, lag_bolt, toggle_bolt, tapcon).
        fastener_spec: Specific fastener specification (e.g., "#10 x 3\" cabinet screw").
    """

    x_position: float
    y_position: float
    hits_stud: bool
    fastener_type: str
    fastener_spec: str

    def __post_init__(self) -> None:
        if self.x_position < 0:
            raise ValueError("x_position must be non-negative")
        if self.y_position < 0:
            raise ValueError("y_position must be non-negative")
        if not self.fastener_type:
            raise ValueError("fastener_type must not be empty")
        if not self.fastener_spec:
            raise ValueError("fastener_spec must not be empty")


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
        """Standard 1/2 inch plywood."""
        return cls(thickness=0.5, material_type=MaterialType.PLYWOOD)

    @classmethod
    def standard_1_4(cls) -> "MaterialSpec":
        """Standard 1/4 inch plywood (typically used for cabinet backs)."""
        return cls(thickness=0.25, material_type=MaterialType.PLYWOOD)


@dataclass(frozen=True)
class CutPiece:
    """A piece to be cut from sheet material."""

    width: float
    height: float
    quantity: int
    label: str
    panel_type: PanelType
    material: MaterialSpec
    cut_metadata: dict[str, Any] | None = None

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


class CornerType(Enum):
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


# --- FRD-18 Built-in Desk Value Objects ---


class DeskType(str, Enum):
    """Types of desk configurations.

    Defines the different desk layout options that can be generated.

    Attributes:
        SINGLE: Standard single-surface desk.
        L_SHAPED: Two perpendicular desk surfaces forming an L.
        CORNER: Corner desk with diagonal or 90-degree connection.
        STANDING: Standing-height desk (38-48").
    """

    SINGLE = "single"
    L_SHAPED = "l_shaped"
    CORNER = "corner"
    STANDING = "standing"


class EdgeTreatment(str, Enum):
    """Desktop edge treatment types.

    Defines the different edge finishing options for desktop surfaces.

    Attributes:
        SQUARE: Standard square edge (default).
        BULLNOSE: Rounded/bullnose edge profile.
        WATERFALL: Edge continues down as vertical front panel.
        EASED: Slightly rounded/softened edge.
    """

    SQUARE = "square"
    BULLNOSE = "bullnose"
    WATERFALL = "waterfall"
    EASED = "eased"


class PedestalType(str, Enum):
    """Types of desk pedestals.

    Defines the different pedestal configurations that support desk surfaces.

    Attributes:
        FILE: File drawer pedestal with pencil drawer above file drawer.
        STORAGE: Multiple storage drawers pedestal.
        OPEN: Open shelving pedestal without drawers.
    """

    FILE = "file"
    STORAGE = "storage"
    OPEN = "open"


@dataclass(frozen=True)
class DeskDimensions:
    """Ergonomic desk dimension constants.

    Provides standard ergonomic measurements for desk components.
    All values are in inches.

    Attributes:
        standard_desk_height: Standard seated desk height (29-30").
        standing_desk_min_height: Minimum standing desk height (38").
        standing_desk_max_height: Maximum standing desk height (48").
        min_knee_clearance_height: Minimum knee clearance height (24").
        min_knee_clearance_width: Minimum knee clearance width (20").
        min_knee_clearance_depth: Minimum knee clearance depth (15").
        keyboard_tray_height: Height for keyboard tray below desktop (3").
        keyboard_tray_depth: Standard keyboard tray depth (10").
    """

    standard_desk_height: float = 29.5
    standing_desk_min_height: float = 38.0
    standing_desk_max_height: float = 48.0
    min_knee_clearance_height: float = 24.0
    min_knee_clearance_width: float = 20.0
    min_knee_clearance_depth: float = 15.0
    keyboard_tray_height: float = 3.0
    keyboard_tray_depth: float = 10.0

    def __post_init__(self) -> None:
        if self.standard_desk_height <= 0:
            raise ValueError("Standard desk height must be positive")
        if self.standing_desk_min_height <= 0:
            raise ValueError("Standing desk min height must be positive")
        if self.standing_desk_max_height <= self.standing_desk_min_height:
            raise ValueError(
                "Standing desk max height must be greater than min height"
            )
        if self.min_knee_clearance_height <= 0:
            raise ValueError("Minimum knee clearance height must be positive")
        if self.min_knee_clearance_width <= 0:
            raise ValueError("Minimum knee clearance width must be positive")
        if self.min_knee_clearance_depth <= 0:
            raise ValueError("Minimum knee clearance depth must be positive")
        if self.keyboard_tray_height <= 0:
            raise ValueError("Keyboard tray height must be positive")
        if self.keyboard_tray_depth <= 0:
            raise ValueError("Keyboard tray depth must be positive")


# --- FRD-19 Entertainment Center Value Objects ---


class EquipmentType(str, Enum):
    """Types of media equipment with standard dimensions.

    Defines the common media equipment types that can be accommodated
    in entertainment center sections. Each type has default dimensions
    and heat generation characteristics.

    Attributes:
        RECEIVER: A/V receiver (17.5"W x 7"H x 18"D, generates heat).
        CONSOLE_HORIZONTAL: Gaming console in horizontal position (generates heat).
        CONSOLE_VERTICAL: Gaming console in vertical position (generates heat).
        STREAMING: Small streaming device (Apple TV, Roku, etc.).
        CABLE_BOX: Cable or satellite box (generates heat).
        BLU_RAY: Blu-ray or DVD player.
        TURNTABLE: Record turntable.
        CUSTOM: User-specified custom equipment dimensions.
    """

    RECEIVER = "receiver"
    CONSOLE_HORIZONTAL = "console_horizontal"
    CONSOLE_VERTICAL = "console_vertical"
    STREAMING = "streaming"
    CABLE_BOX = "cable_box"
    BLU_RAY = "blu_ray"
    TURNTABLE = "turntable"
    CUSTOM = "custom"


class SoundbarType(str, Enum):
    """Soundbar size categories.

    Defines the standard soundbar sizes for entertainment center
    integration. Soundbars require open shelves (not enclosed)
    for proper sound projection.

    Attributes:
        COMPACT: Small soundbar, approximately 24" width.
        STANDARD: Medium soundbar, approximately 36" width.
        PREMIUM: Large soundbar, 48"+ width.
        CUSTOM: User-specified custom soundbar dimensions.
    """

    COMPACT = "compact"
    STANDARD = "standard"
    PREMIUM = "premium"
    CUSTOM = "custom"


class SpeakerType(str, Enum):
    """Types of speakers for built-in alcoves.

    Defines the common speaker types that can be accommodated
    in entertainment center alcoves. Each type has different
    dimensional and acoustic requirements.

    Attributes:
        CENTER_CHANNEL: Horizontal center channel speaker (ear level placement).
        BOOKSHELF: Standard bookshelf speaker (vertical orientation).
        SUBWOOFER: Subwoofer with port clearance requirements.
    """

    CENTER_CHANNEL = "center_channel"
    BOOKSHELF = "bookshelf"
    SUBWOOFER = "subwoofer"


# --- FRD-11 Advanced Room Geometry Value Objects ---


@dataclass(frozen=True)
class CeilingSlope:
    """Ceiling slope definition.

    Represents a sloped ceiling that affects cabinet height along a wall.
    Used for attic spaces, vaulted ceilings, or other non-flat ceiling conditions.

    Attributes:
        angle: Degrees from horizontal (0-60). Higher values mean steeper slopes.
        start_height: Height at slope start in inches.
        direction: Direction of slope - which way the ceiling descends.
        min_height: Minimum usable height in inches (default 24.0).
    """

    angle: float
    start_height: float
    direction: Literal["left_to_right", "right_to_left", "front_to_back"]
    min_height: float = 24.0

    def __post_init__(self) -> None:
        if not 0 <= self.angle <= 60:
            raise ValueError("Slope angle must be between 0 and 60 degrees")
        if self.start_height <= 0:
            raise ValueError("Start height must be positive")
        if self.min_height < 0:
            raise ValueError("Minimum height cannot be negative")

    def height_at_position(self, position: float) -> float:
        """Calculate ceiling height at given position along slope.

        Args:
            position: Distance along the slope direction in inches.

        Returns:
            Ceiling height at that position in inches.
        """
        return self.start_height - (position * tan(radians(self.angle)))


@dataclass(frozen=True)
class Skylight:
    """Skylight definition with projection into cabinet space.

    Represents a skylight that may project down into the cabinet area,
    creating a void that panels must avoid.

    Attributes:
        x_position: Position along wall in inches (from left edge).
        width: Skylight width in inches.
        projection_depth: How far the skylight projects down in inches.
        projection_angle: Angle from ceiling in degrees (90 = vertical projection).
    """

    x_position: float
    width: float
    projection_depth: float
    projection_angle: float = 90.0

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Skylight width must be positive")
        if self.projection_depth <= 0:
            raise ValueError("Projection depth must be positive")
        if not 0 < self.projection_angle <= 180:
            raise ValueError("Projection angle must be between 0 and 180 degrees")

    def void_at_depth(self, cabinet_depth: float) -> tuple[float, float]:
        """Calculate void dimensions at cabinet top level.

        For angled projections, the void expands as it projects down.
        This method calculates the void dimensions at the cabinet's depth.

        Args:
            cabinet_depth: Depth of the cabinet in inches.

        Returns:
            Tuple of (void_start_x, void_width) at cabinet depth.
        """
        if self.projection_angle == 90:
            return (self.x_position, self.width)
        # Angled projection expands the void
        expansion = cabinet_depth * tan(radians(90 - self.projection_angle))
        return (self.x_position - expansion / 2, self.width + expansion)


@dataclass(frozen=True)
class OutsideCornerConfig:
    """Configuration for outside (convex) corner treatment.

    Outside corners occur when cabinet runs wrap around a projecting wall
    or column. This configuration specifies how to handle the corner transition.

    Attributes:
        treatment: Type of corner treatment to apply.
            - "angled_face": 45-degree angled face panel
            - "butted_filler": Filler strip between perpendicular runs
            - "wrap_around": Continuous face around corner
        filler_width: Width of filler strip for butted_filler treatment (inches).
        face_angle: Angle of face panel for angled_face treatment (degrees).
    """

    treatment: Literal["angled_face", "butted_filler", "wrap_around"] = "angled_face"
    filler_width: float = 3.0
    face_angle: float = 45.0

    def __post_init__(self) -> None:
        if self.filler_width <= 0:
            raise ValueError("Filler width must be positive")
        if not 0 < self.face_angle < 90:
            raise ValueError("Face angle must be between 0 and 90 degrees")


@dataclass(frozen=True)
class AngleCut:
    """Specification for angled cut on panel edge.

    Represents a non-perpendicular cut on one edge of a panel,
    used for corner cabinets or sloped ceiling conditions.

    Attributes:
        edge: Which edge of the panel has the angled cut.
        angle: Degrees from perpendicular (0-90).
        bevel: True for beveled edge (angled through thickness),
               False for straight cut (angled in plane).
    """

    edge: Literal["left", "right", "top", "bottom"]
    angle: float
    bevel: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.angle <= 90:
            raise ValueError("Cut angle must be between 0 and 90 degrees")


@dataclass(frozen=True)
class TaperSpec:
    """Specification for tapered panel (sloped ceiling).

    Represents a panel that tapers from one height to another,
    typically used for side panels under sloped ceilings.

    Attributes:
        start_height: Height at the start of the taper in inches.
        end_height: Height at the end of the taper in inches.
        direction: Direction of the taper along the panel.
    """

    start_height: float
    end_height: float
    direction: Literal["left_to_right", "right_to_left"]

    def __post_init__(self) -> None:
        if self.start_height <= 0 or self.end_height <= 0:
            raise ValueError("Heights must be positive")


@dataclass(frozen=True)
class NotchSpec:
    """Specification for notched panel (skylight void).

    Represents a rectangular notch cut from a panel edge,
    typically used to accommodate skylight projections or other obstructions.

    Attributes:
        x_offset: Distance from left edge of panel to notch start in inches.
        width: Width of the notch in inches.
        depth: Depth of notch from the edge in inches.
        edge: Which edge of the panel the notch is cut from.
    """

    x_offset: float
    width: float
    depth: float
    edge: Literal["top", "bottom", "left", "right"]

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Notch width must be positive")
        if self.depth <= 0:
            raise ValueError("Notch depth must be positive")
        if self.x_offset < 0:
            raise ValueError("Notch x_offset cannot be negative")


@dataclass(frozen=True)
class PanelCutMetadata:
    """Extended cut metadata for non-rectangular panels.

    Aggregates all special cutting instructions for a panel that
    is not a simple rectangle. Used to communicate cutting requirements
    to the cut list and manufacturing systems.

    Attributes:
        angle_cuts: Tuple of angle cuts to apply to panel edges.
        taper: Optional taper specification for tapered panels.
        notches: Tuple of notch specifications for notched panels.
    """

    angle_cuts: tuple[AngleCut, ...] = field(default_factory=tuple)
    taper: TaperSpec | None = None
    notches: tuple[NotchSpec, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PanelCutout:
    """Specification for a cutout in a cabinet panel.

    Represents a hole or opening cut into a panel for infrastructure
    integration such as electrical outlets, cable grommets, wire routing
    holes, or ventilation.

    Attributes:
        cutout_type: Type of cutout (e.g., "outlet", "grommet", "wire_hole", "vent").
        panel: The panel type where this cutout is located.
        position: 2D position of the cutout center on the panel.
        width: Width of the cutout in inches (for rectangular cutouts).
        height: Height of the cutout in inches (for rectangular cutouts).
        shape: Shape of the cutout (rectangular or circular).
        notes: Optional notes or instructions for the cutout.
        diameter: Diameter in inches for circular cutouts (optional).
    """

    cutout_type: str
    panel: PanelType
    position: Point2D
    width: float
    height: float
    shape: CutoutShape = CutoutShape.RECTANGULAR
    notes: str = ""
    diameter: float | None = None

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Cutout width must be positive")
        if self.height <= 0:
            raise ValueError("Cutout height must be positive")
        if self.shape == CutoutShape.CIRCULAR and self.diameter is None:
            raise ValueError("Diameter is required for circular cutouts")
        if self.diameter is not None and self.diameter <= 0:
            raise ValueError("Diameter must be positive")

    @property
    def area(self) -> float:
        """Calculate the area of the cutout in square inches."""
        if self.shape == CutoutShape.CIRCULAR and self.diameter is not None:
            import math

            return math.pi * (self.diameter / 2) ** 2
        return self.width * self.height
