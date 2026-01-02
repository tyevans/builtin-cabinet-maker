"""Value objects for the cabinet domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import atan2, degrees, radians, sqrt, tan
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .entities import Obstacle


class MaterialType(str, Enum):
    """Types of materials used in cabinet construction."""

    PLYWOOD = "plywood"
    MDF = "mdf"
    PARTICLE_BOARD = "particle_board"
    SOLID_WOOD = "solid_wood"


class ObstacleType(str, Enum):
    """Types of obstacles that cabinets must avoid.

    Defines physical obstructions and infrastructure elements that
    require clearance or special handling during cabinet placement.

    Attributes:
        WINDOW: Window opening in wall.
        DOOR: Door or door frame.
        OUTLET: Electrical outlet/receptacle.
        SWITCH: Light switch or other wall switch.
        VENT: HVAC vent or register.
        SKYLIGHT: Skylight projection into cabinet space.
        CUSTOM: User-defined obstacle type.
        ELECTRICAL_PANEL: Electrical service panel (requires 36" clearance).
        COOKTOP: Cooking surface (requires 30" vertical clearance).
        HEAT_SOURCE: Heat-generating appliance or element.
        CLOSET_LIGHT: Closet lighting fixture (NEC clearance required).
    """

    # Existing values
    WINDOW = "window"
    DOOR = "door"
    OUTLET = "outlet"
    SWITCH = "switch"
    VENT = "vent"
    SKYLIGHT = "skylight"
    CUSTOM = "custom"

    # New safety-related obstacles (FRD-21)
    ELECTRICAL_PANEL = "electrical_panel"
    COOKTOP = "cooktop"
    HEAT_SOURCE = "heat_source"
    CLOSET_LIGHT = "closet_light"


class PanelType(str, Enum):
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

    # Countertop and zone panels (FRD-22)
    COUNTERTOP = "countertop"
    SUPPORT_BRACKET = "support_bracket"
    STEPPED_SIDE = "stepped_side"

    # Bay alcove panels (FRD-23)
    SEAT_SURFACE = "seat_surface"
    MULLION_FILLER = "mullion_filler"
    APEX_INFILL = "apex_infill"


class SectionType(str, Enum):
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


# --- FRD-21 Safety Compliance Value Objects ---


class SafetyCheckStatus(str, Enum):
    """Result status for safety checks.

    Indicates the outcome of a safety validation check.

    Attributes:
        PASS: Check passed successfully - no safety concerns.
        WARNING: Check identified a potential concern that should be reviewed.
        ERROR: Check identified a violation that must be addressed.
        NOT_APPLICABLE: Check was skipped - not relevant to this configuration.
    """

    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


class SafetyCategory(str, Enum):
    """Categories of safety checks.

    Groups safety checks by their domain for organized reporting
    and selective enabling/disabling of check categories.

    Attributes:
        STRUCTURAL: Weight capacity, deflection, span limits.
        STABILITY: Anti-tip requirements, center of gravity analysis.
        ACCESSIBILITY: ADA reach ranges, accessible storage percentage.
        CLEARANCE: Building code clearances (electrical, heat, egress).
        MATERIAL: Formaldehyde emissions, VOC compliance.
        CHILD_SAFETY: Entrapment hazards, sharp edges, soft-close hardware.
        SEISMIC: Earthquake zone anchoring requirements.
    """

    STRUCTURAL = "structural"
    STABILITY = "stability"
    ACCESSIBILITY = "accessibility"
    CLEARANCE = "clearance"
    MATERIAL = "material"
    CHILD_SAFETY = "child_safety"
    SEISMIC = "seismic"


class SeismicZone(str, Enum):
    """IBC Seismic Design Categories.

    Defines seismic risk zones per International Building Code.
    Higher letters indicate greater seismic risk and stricter
    anchoring requirements.

    Attributes:
        A: Low seismic risk - minimal anchoring.
        B: Low-moderate seismic risk.
        C: Moderate seismic risk.
        D: High seismic risk - enhanced anchoring required.
        E: Very high seismic risk - enhanced anchoring required.
        F: Very high seismic risk near major faults.

    Note:
        Zones D, E, F require seismic-rated anchoring hardware
        and may require structural engineering review.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class MaterialCertification(str, Enum):
    """Material certification levels for formaldehyde emissions.

    Tracks compliance with CARB ATCM 93120 and EPA TSCA Title VI
    requirements for composite wood products.

    Attributes:
        CARB_PHASE2: CARB Phase 2 compliant (TSCA Title VI equivalent).
        NAF: No Added Formaldehyde - exempt resin systems.
        ULEF: Ultra-Low Emitting Formaldehyde - below Phase 2 limits.
        NONE: Known non-compliant or no certification.
        UNKNOWN: Certification status not specified.

    Note:
        NAF and ULEF certifications exceed Phase 2 requirements and
        are considered best practice for indoor air quality.
    """

    CARB_PHASE2 = "carb_phase2"
    NAF = "naf"
    ULEF = "ulef"
    NONE = "none"
    UNKNOWN = "unknown"


class VOCCategory(str, Enum):
    """VOC content categories for finishes and coatings.

    Categorizes finishes by volatile organic compound content
    per SCAQMD Rule 1113 guidelines.

    Attributes:
        SUPER_COMPLIANT: Less than 10 g/L VOC content.
        COMPLIANT: Less than 50 g/L VOC content.
        STANDARD: Standard VOC content (may exceed 50 g/L).
        UNKNOWN: VOC category not specified.
    """

    SUPER_COMPLIANT = "super_compliant"
    COMPLIANT = "compliant"
    STANDARD = "standard"
    UNKNOWN = "unknown"


class ADAStandard(str, Enum):
    """ADA accessibility standard versions.

    Specifies which accessibility standard to use for compliance
    checking. Different standards may have different requirements.

    Attributes:
        ADA_2010: 2010 ADA Standards for Accessible Design (federal).
        ANSI_A117_1: ANSI A117.1 Accessible and Usable Buildings standard.
    """

    ADA_2010 = "ADA_2010"
    ANSI_A117_1 = "ANSI_A117.1"


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
    # Existing obstacle clearances
    ObstacleType.WINDOW: Clearance(top=2.0, bottom=2.0, left=2.0, right=2.0),
    ObstacleType.DOOR: Clearance(top=0.0, bottom=0.0, left=2.0, right=2.0),
    ObstacleType.OUTLET: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.SWITCH: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.VENT: Clearance(top=4.0, bottom=4.0, left=4.0, right=4.0),
    ObstacleType.SKYLIGHT: Clearance(top=2.0, bottom=2.0, left=2.0, right=2.0),
    ObstacleType.CUSTOM: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    # New safety-related clearances (FRD-21)
    # Note: Electrical panel 36" frontal clearance is checked separately by SafetyService
    ObstacleType.ELECTRICAL_PANEL: Clearance(
        top=0.0, bottom=0.0, left=15.0, right=15.0
    ),
    # Cooktop 30" top clearance per range hood/microwave clearance requirements
    ObstacleType.COOKTOP: Clearance(top=30.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.HEAT_SOURCE: Clearance(top=30.0, bottom=0.0, left=15.0, right=15.0),
    # Closet light 12" bottom clearance per NEC 410.16 for incandescent fixtures
    ObstacleType.CLOSET_LIGHT: Clearance(top=0.0, bottom=12.0, left=6.0, right=6.0),
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


# --- FRD-22 Countertops and Vertical Zones Value Objects ---


class ZoneType(str, Enum):
    """Types of vertical zones in cabinet configurations.

    Defines the different types of vertical zones that can be stacked
    to create multi-zone cabinet configurations like kitchen base/upper
    or mudroom bench/open shelving.

    Attributes:
        BASE: Floor-standing base cabinet zone.
        UPPER: Wall-mounted upper cabinet zone.
        GAP: Empty gap zone (for backsplash, mirror, hooks, etc.).
        BENCH: Bench/seat zone, typically lower height.
        OPEN: Open shelving zone without doors.
    """

    BASE = "base"
    UPPER = "upper"
    GAP = "gap"
    BENCH = "bench"
    OPEN = "open"


class ZoneMounting(str, Enum):
    """Mounting methods for cabinet zones.

    Defines how a zone is attached/supported in the overall configuration.

    Attributes:
        FLOOR: Zone rests on the floor (base cabinets, benches).
        WALL: Zone is mounted to the wall (upper cabinets).
        SUSPENDED: Zone is suspended from ceiling or structure.
        ON_BASE: Zone rests on top of a base zone (hutch uppers).
    """

    FLOOR = "floor"
    WALL = "wall"
    SUSPENDED = "suspended"
    ON_BASE = "on_base"


class GapPurpose(str, Enum):
    """Purpose designation for gap zones.

    Defines the intended use of a gap zone, which affects
    recommendations for wall treatment and accessories.

    Attributes:
        BACKSPLASH: Kitchen backsplash area (typically tile/stone).
        MIRROR: Bathroom mirror area.
        HOOKS: Coat hooks or hanging storage area.
        WORKSPACE: Workspace area between base and upper cabinets.
        DISPLAY: Display or decorative area.
    """

    BACKSPLASH = "backsplash"
    MIRROR = "mirror"
    HOOKS = "hooks"
    WORKSPACE = "workspace"
    DISPLAY = "display"


class ZonePreset(str, Enum):
    """Preset vertical zone configurations.

    Provides standard zone stack configurations for common use cases.
    Each preset defines a complete vertical arrangement of zones.

    Attributes:
        KITCHEN: Standard kitchen with base, countertop, backsplash, and uppers.
        MUDROOM: Mudroom with bench, hooks area, and open upper storage.
        VANITY: Bathroom vanity with base, counter, mirror area, and small uppers.
        HUTCH: Desk hutch with base desk, workspace gap, and upper storage.
        CUSTOM: User-defined custom zone configuration.
    """

    KITCHEN = "kitchen"
    MUDROOM = "mudroom"
    VANITY = "vanity"
    HUTCH = "hutch"
    CUSTOM = "custom"


class CountertopEdgeType(str, Enum):
    """Edge treatment types for countertops.

    Defines the different edge finishing options for countertop surfaces.
    Affects both aesthetics and cut list generation.

    Attributes:
        SQUARE: Standard square edge (most common, easiest to fabricate).
        EASED: Slightly rounded/softened edge (removes sharp corner).
        BULLNOSE: Fully rounded edge profile.
        BEVELED: Angled edge cut (typically 45 degrees).
        WATERFALL: Edge continues down as vertical panel.
    """

    SQUARE = "square"
    EASED = "eased"
    BULLNOSE = "bullnose"
    BEVELED = "beveled"
    WATERFALL = "waterfall"


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
            raise ValueError("Standing desk max height must be greater than min height")
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


# --- FRD-23 Bay Window Alcove Value Objects ---


class BayType(str, Enum):
    """Preset bay window configurations.

    Defines the different bay window configurations that can be used
    for alcove built-ins. Each type has different wall angles and
    facet arrangements.

    Attributes:
        THREE_WALL: Classic 3-wall bay with 45-degree angles.
        FIVE_WALL: 5-wall angled bay with 22.5-degree angles.
        BOX_BAY: 3-wall at 90-degree angles (rectangular projection).
        BOW: Curved bay approximated by multiple segments.
        CUSTOM: User-defined angles and wall configuration.
    """

    THREE_WALL = "three_wall"
    FIVE_WALL = "five_wall"
    BOX_BAY = "box_bay"
    BOW = "bow"
    CUSTOM = "custom"


class FillerTreatment(str, Enum):
    """Treatment options for mullion/narrow wall zones.

    Defines how to handle the narrow zones between bay window walls,
    such as the areas around mullions or narrow wall segments.

    Attributes:
        PANEL: Solid panel filler to close the gap.
        TRIM: Decorative trim piece to cover the gap.
        NONE: Leave the gap open/exposed.
    """

    PANEL = "panel"
    TRIM = "trim"
    NONE = "none"


@dataclass(frozen=True)
class ApexPoint:
    """Apex point for pyramidal/conical ceiling.

    Represents the highest point of a radial ceiling where all
    ceiling facets converge. Coordinates are relative to the
    bay alcove origin (typically center of bay at floor level).

    Attributes:
        x: X coordinate relative to bay origin (inches).
        y: Y coordinate relative to bay origin (inches).
        z: Height from floor (inches).
    """

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if self.z <= 0:
            raise ValueError("Apex height must be positive")

    def distance_to(self, point_x: float, point_y: float) -> float:
        """Calculate horizontal distance from apex to a point.

        Args:
            point_x: X coordinate of the target point.
            point_y: Y coordinate of the target point.

        Returns:
            Horizontal distance in inches.
        """
        return sqrt((self.x - point_x) ** 2 + (self.y - point_y) ** 2)


@dataclass(frozen=True)
class CeilingFacet:
    """A triangular ceiling facet in a radial ceiling.

    Each facet connects the apex point to a wall segment's top edge,
    forming one triangular face of the pyramidal/conical ceiling.

    Attributes:
        wall_index: Index of the wall this facet is above.
        edge_start: Point2D for left edge where facet meets wall.
        edge_end: Point2D for right edge where facet meets wall.
        edge_height: Height of wall top edge (where facet starts).
        apex: Reference to the apex point.
    """

    wall_index: int
    edge_start: Point2D
    edge_end: Point2D
    edge_height: float
    apex: ApexPoint

    def __post_init__(self) -> None:
        if self.wall_index < 0:
            raise ValueError("Wall index must be non-negative")
        if self.edge_height <= 0:
            raise ValueError("Edge height must be positive")
        if self.edge_height >= self.apex.z:
            raise ValueError("Edge height must be less than apex height")

    @property
    def slope_angle(self) -> float:
        """Calculate slope angle of this facet in degrees.

        The slope angle is measured from horizontal, representing
        how steeply the ceiling facet rises from the wall edge
        to the apex point.

        Returns:
            Slope angle in degrees (0-90).
        """
        # Calculate center of wall edge
        edge_center_x = (self.edge_start.x + self.edge_end.x) / 2
        edge_center_y = (self.edge_start.y + self.edge_end.y) / 2

        # Horizontal distance from edge center to apex
        horizontal_dist = self.apex.distance_to(edge_center_x, edge_center_y)

        # Vertical rise from edge to apex
        vertical_rise = self.apex.z - self.edge_height

        # Calculate angle from horizontal
        if horizontal_dist == 0:
            return 90.0
        return degrees(atan2(vertical_rise, horizontal_dist))

    def height_at_point(self, x: float, y: float) -> float:
        """Calculate ceiling height at a point under this facet.

        Uses linear interpolation based on radial distance from the apex.
        Points closer to the apex are higher, points closer to the wall
        edge are at the edge height.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.

        Returns:
            Ceiling height at the specified point in inches.
        """
        # Calculate center of wall edge
        edge_center_x = (self.edge_start.x + self.edge_end.x) / 2
        edge_center_y = (self.edge_start.y + self.edge_end.y) / 2

        # Distance from apex to edge center (full run of the facet)
        edge_dist = self.apex.distance_to(edge_center_x, edge_center_y)

        # Distance from apex to the query point
        point_dist = self.apex.distance_to(x, y)

        if edge_dist == 0:
            # Degenerate case: apex directly above edge center
            return self.apex.z

        # Linear interpolation: t=0 at apex (full height), t=1 at edge (edge height)
        t = min(1.0, point_dist / edge_dist)
        return self.apex.z - t * (self.apex.z - self.edge_height)


@dataclass(frozen=True)
class RadialCeilingGeometry:
    """Radial/pyramidal ceiling geometry for bay alcoves.

    Models a ceiling where multiple triangular facets converge
    to a central apex point, typical of bay window alcoves with
    pyramidal or conical ceiling treatments.

    Attributes:
        apex: The apex point where all facets meet.
        facets: Tuple of ceiling facets (one per wall segment).
        edge_height: Default wall top height where facets begin.
    """

    apex: ApexPoint
    facets: tuple[CeilingFacet, ...]
    edge_height: float

    def __post_init__(self) -> None:
        if self.edge_height <= 0:
            raise ValueError("Edge height must be positive")
        if len(self.facets) < 3:
            raise ValueError("Radial ceiling requires at least 3 facets")
        for facet in self.facets:
            if facet.apex != self.apex:
                raise ValueError("All facets must share the same apex point")

    def height_at_point(self, x: float, y: float) -> float | None:
        """Calculate ceiling height at any point.

        Determines which facet contains the point and returns the
        interpolated ceiling height at that location.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.

        Returns:
            Ceiling height at the specified point in inches,
            or None if the point is outside all facets.
        """
        # Find the facet that contains this point using a simple
        # closest-facet approach based on distance to wall edge center
        best_facet = None
        best_distance = float("inf")

        for facet in self.facets:
            # Calculate center of wall edge
            edge_center_x = (facet.edge_start.x + facet.edge_end.x) / 2
            edge_center_y = (facet.edge_start.y + facet.edge_end.y) / 2

            # Distance from point to edge center
            dist = sqrt((x - edge_center_x) ** 2 + (y - edge_center_y) ** 2)

            if dist < best_distance:
                best_distance = dist
                best_facet = facet

        if best_facet is None:
            return None

        return best_facet.height_at_point(x, y)

    @property
    def average_slope_angle(self) -> float:
        """Calculate the average slope angle across all facets.

        Returns:
            Average slope angle in degrees.
        """
        if not self.facets:
            return 0.0
        total = sum(facet.slope_angle for facet in self.facets)
        return total / len(self.facets)


class BayAlcoveConfig:
    """Domain configuration for bay window alcove built-ins.

    This is a lightweight domain representation of the bay alcove configuration
    that can be used by layout calculators and services. It holds the essential
    configuration data in a form suitable for domain logic.

    Attributes:
        bay_type: Type of bay configuration.
        walls: Tuple of wall configuration dictionaries.
        opening_width: Width of bay opening.
        bay_depth: Depth from main wall to furthest point.
        arc_angle: Arc angle for bow windows.
        segment_count: Segment count for bow windows.
        apex: ApexPoint for radial ceiling, or None.
        apex_mode: "auto" or "explicit" for apex calculation.
        edge_height: Height where ceiling meets walls.
        min_cabinet_width: Minimum width for cabinet zones.
        filler_treatment: Treatment for narrow zones.
        sill_clearance: Clearance below window sill.
        head_clearance: Clearance above window head.
        seat_surface_style: Seat surface construction style.
        flank_integration: Flanking cabinet connection style.
        top_style: Global top panel style.
        shelf_alignment: Global shelf alignment strategy.
    """

    def __init__(
        self,
        bay_type: str,
        walls: tuple,
        opening_width: float | None,
        bay_depth: float | None,
        arc_angle: float | None,
        segment_count: int | None,
        apex: "ApexPoint | None",
        apex_mode: str,
        edge_height: float,
        min_cabinet_width: float,
        filler_treatment: str,
        sill_clearance: float,
        head_clearance: float,
        seat_surface_style: str,
        flank_integration: str,
        top_style: str | None,
        shelf_alignment: str,
    ) -> None:
        self.bay_type = bay_type
        self.walls = walls
        self.opening_width = opening_width
        self.bay_depth = bay_depth
        self.arc_angle = arc_angle
        self.segment_count = segment_count
        self.apex = apex
        self.apex_mode = apex_mode
        self.edge_height = edge_height
        self.min_cabinet_width = min_cabinet_width
        self.filler_treatment = filler_treatment
        self.sill_clearance = sill_clearance
        self.head_clearance = head_clearance
        self.seat_surface_style = seat_surface_style
        self.flank_integration = flank_integration
        self.top_style = top_style
        self.shelf_alignment = shelf_alignment

    @property
    def is_bow(self) -> bool:
        """Check if this is a bow window configuration."""
        return self.bay_type == "bow"

    @property
    def wall_count(self) -> int:
        """Get the number of wall segments."""
        return len(self.walls)

    def get_wall(self, index: int) -> dict:
        """Get wall configuration by index.

        Args:
            index: Wall index (0-based).

        Returns:
            Wall configuration dictionary.

        Raises:
            IndexError: If index is out of range.
        """
        return self.walls[index]
