"""Pydantic configuration schema models for cabinet specifications.

This module defines the configuration schema for JSON-based cabinet configuration
files. It uses Pydantic v2 for validation and serialization.

The MaterialType enum is reused from the domain layer to ensure consistency
and avoid duplication.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cabinets.domain.value_objects import MaterialType

# Supported schema versions for configuration files
# Version 1.0: Initial schema with basic cabinet configuration
# Version 1.1: Added room geometry, obstacles, and inside corner support (FRD-10)
# Version 1.2: Added sloped ceilings, skylights, and outside corners (FRD-11)
# Version 1.3: Added decorative elements (FRD-12)
# Version 1.4: Added bin packing configuration (FRD-13)
# Version 1.5: Added woodworking intelligence (FRD-14)
# Version 1.6: Added infrastructure integration (FRD-15)
# Version 1.7: Added per-format output configuration (FRD-16)
# Version 1.8: Added installation support (FRD-17)
SUPPORTED_VERSIONS: frozenset[str] = frozenset({"1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8"})


class ObstacleTypeConfig(str, Enum):
    """Obstacle types for configuration.

    This enum mirrors the domain ObstacleType but is used for configuration
    parsing. It uses string values for JSON serialization compatibility.
    """

    WINDOW = "window"
    DOOR = "door"
    OUTLET = "outlet"
    SWITCH = "switch"
    VENT = "vent"
    SKYLIGHT = "skylight"
    CUSTOM = "custom"


class HeightMode(str, Enum):
    """Height mode for cabinet sections.

    Determines how a section uses the available wall height:
    - FULL: Section spans the full wall height
    - LOWER: Section is placed below obstacles (e.g., under a window)
    - UPPER: Section is placed above obstacles (e.g., above a door)
    - AUTO: System automatically determines the best height mode
    """

    FULL = "full"
    LOWER = "lower"
    UPPER = "upper"
    AUTO = "auto"


class SectionTypeConfig(str, Enum):
    """Section type for configuration.

    Defines the different types of cabinet sections that can be created,
    each with its own visual and functional characteristics.

    This enum mirrors the domain SectionType but is used for configuration
    parsing. It uses string values for JSON serialization compatibility.

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


class ArchTypeConfig(str, Enum):
    """Arch type for configuration.

    Defines the curve geometry for arched cabinet openings.

    Attributes:
        FULL_ROUND: Semicircular arch where radius equals half the opening width.
        SEGMENTAL: Partial arc with specified radius larger than half width.
        ELLIPTICAL: Elliptical curve for a softer arch profile.
    """

    FULL_ROUND = "full_round"
    SEGMENTAL = "segmental"
    ELLIPTICAL = "elliptical"


class JoineryTypeConfig(str, Enum):
    """Joinery type for configuration.

    Defines how cabinet components are joined together.

    Attributes:
        DADO: Groove cut into one panel to receive another.
        RABBET: L-shaped cut along panel edge for back panel fit.
        POCKET_SCREW: Pocket hole joinery with angled screws.
        MORTISE_TENON: Traditional mortise and tenon joints.
        DOWEL: Dowel pin joinery for alignment and strength.
        BISCUIT: Football-shaped spline for panel alignment.
        BUTT: Simple butt joint with mechanical fasteners.
    """

    DADO = "dado"
    RABBET = "rabbet"
    POCKET_SCREW = "pocket_screw"
    MORTISE_TENON = "mortise_tenon"
    DOWEL = "dowel"
    BISCUIT = "biscuit"
    BUTT = "butt"


class EdgeProfileTypeConfig(str, Enum):
    """Edge profile type for configuration.

    Defines router bit profiles for visible edges.

    Attributes:
        CHAMFER: Angled flat cut at 45 degrees.
        ROUNDOVER: Rounded edge profile.
        OGEE: S-curve decorative profile.
        BEVEL: Angled cut at specified angle.
        COVE: Concave curved profile.
        ROMAN_OGEE: Complex S-curve with fillet.
    """

    CHAMFER = "chamfer"
    ROUNDOVER = "roundover"
    OGEE = "ogee"
    BEVEL = "bevel"
    COVE = "cove"
    ROMAN_OGEE = "roman_ogee"


# =============================================================================
# Infrastructure Integration Enums (FRD-15)
# =============================================================================


class LightingTypeConfig(str, Enum):
    """Lighting type for cabinet infrastructure.

    Defines the type of lighting to be installed in or around cabinets.

    Attributes:
        LED_STRIP: Linear LED strip lighting, typically for under-cabinet illumination.
        PUCK_LIGHT: Round puck-style lights for focused illumination.
        ACCENT: Accent lighting for decorative purposes.
    """

    LED_STRIP = "led_strip"
    PUCK_LIGHT = "puck_light"
    ACCENT = "accent"


class LightingLocationConfig(str, Enum):
    """Location for lighting installation.

    Defines where lighting is positioned relative to the cabinet.

    Attributes:
        UNDER_CABINET: Lighting mounted on the underside of the cabinet.
        IN_CABINET: Lighting inside the cabinet for interior illumination.
        ABOVE_CABINET: Lighting mounted above the cabinet.
    """

    UNDER_CABINET = "under_cabinet"
    IN_CABINET = "in_cabinet"
    ABOVE_CABINET = "above_cabinet"


class OutletTypeConfig(str, Enum):
    """Electrical outlet type for cabinet infrastructure.

    Defines the type of electrical outlet to be installed.

    Attributes:
        SINGLE: Single electrical outlet.
        DOUBLE: Double (duplex) electrical outlet.
        GFI: Ground Fault Interrupter outlet for wet locations.
    """

    SINGLE = "single"
    DOUBLE = "double"
    GFI = "gfi"


class CableManagementTypeConfig(str, Enum):
    """Cable management type for routing cables through cabinets.

    Defines the method used to manage cables within cabinet structures.

    Attributes:
        GROMMET: Round cable pass-through grommet.
        CHANNEL: Linear cable routing channel.
    """

    GROMMET = "grommet"
    CHANNEL = "channel"


class VentilationPatternConfig(str, Enum):
    """Ventilation pattern for cabinet panels.

    Defines the pattern of ventilation holes cut into panels.

    Attributes:
        GRID: Regular grid pattern of holes.
        SLOT: Horizontal or vertical slot pattern.
        CIRCULAR: Circular arrangement of holes.
    """

    GRID = "grid"
    SLOT = "slot"
    CIRCULAR = "circular"


class ConduitDirectionConfig(str, Enum):
    """Direction for electrical conduit routing.

    Defines the direction in which conduit exits from an electrical box.

    Attributes:
        TOP: Conduit exits from the top of the box.
        BOTTOM: Conduit exits from the bottom of the box.
        LEFT: Conduit exits from the left side of the box.
        RIGHT: Conduit exits from the right side of the box.
    """

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


# =============================================================================
# Installation Support Enums (FRD-17)
# =============================================================================


class WallTypeConfig(str, Enum):
    """Wall construction type for configuration.

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


class MountingSystemConfig(str, Enum):
    """Cabinet mounting method for configuration.

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


class LoadCategoryConfig(str, Enum):
    """Expected load category for configuration.

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


class ClearanceConfig(BaseModel):
    """Clearance distances around an obstacle.

    Specifies the minimum space that must be kept clear around an obstacle
    in each direction. All values are in inches and must be non-negative.

    Attributes:
        top: Clearance above the obstacle (default 0.0)
        bottom: Clearance below the obstacle (default 0.0)
        left: Clearance to the left of the obstacle (default 0.0)
        right: Clearance to the right of the obstacle (default 0.0)
    """

    model_config = ConfigDict(extra="forbid")

    top: float = Field(default=0.0, ge=0)
    bottom: float = Field(default=0.0, ge=0)
    left: float = Field(default=0.0, ge=0)
    right: float = Field(default=0.0, ge=0)


class ObstacleConfig(BaseModel):
    """Configuration for a wall obstacle.

    Obstacles represent features on walls that cabinets must avoid,
    such as windows, doors, outlets, switches, and vents.

    Attributes:
        type: The type of obstacle (window, door, outlet, etc.)
        wall: Wall index where this obstacle is located (0-based)
        horizontal_offset: Distance from wall start to obstacle left edge
        bottom: Distance from floor to obstacle bottom edge
        width: Obstacle width in inches
        height: Obstacle height in inches
        clearance: Optional custom clearance (overrides type defaults)
        name: Optional identifier for the obstacle
    """

    model_config = ConfigDict(extra="forbid")

    type: ObstacleTypeConfig
    wall: int = Field(ge=0, description="Wall index")
    horizontal_offset: float = Field(ge=0, description="Distance from wall start")
    bottom: float = Field(ge=0, description="Distance from floor")
    width: float = Field(gt=0, description="Obstacle width")
    height: float = Field(gt=0, description="Obstacle height")
    clearance: ClearanceConfig | None = None
    name: str | None = None


class ObstacleDefaultsConfig(BaseModel):
    """Default clearances by obstacle type.

    Allows configuration of default clearance distances for each obstacle
    type. If not specified for a type, the system defaults are used.

    Attributes:
        window: Default clearance for windows
        door: Default clearance for doors
        outlet: Default clearance for outlets
        switch: Default clearance for switches
        vent: Default clearance for vents
        skylight: Default clearance for skylights
        custom: Default clearance for custom obstacles
    """

    model_config = ConfigDict(extra="forbid")

    window: ClearanceConfig | None = None
    door: ClearanceConfig | None = None
    outlet: ClearanceConfig | None = None
    switch: ClearanceConfig | None = None
    vent: ClearanceConfig | None = None
    skylight: ClearanceConfig | None = None
    custom: ClearanceConfig | None = None


class MaterialConfig(BaseModel):
    """Material configuration for cabinet components.

    Attributes:
        type: The type of material (plywood, mdf, particle_board, solid_wood)
        thickness: Material thickness in inches (0.25 to 2.0)
    """

    model_config = ConfigDict(extra="forbid")

    type: MaterialType = MaterialType.PLYWOOD
    thickness: float = Field(default=0.75, ge=0.25, le=2.0)


class WallSegmentConfig(BaseModel):
    """Configuration for a wall segment in a room.

    Wall segments define the geometry of walls where cabinets can be placed.
    Each segment has a length, height, and angle relative to the previous wall.

    Attributes:
        length: Length along the wall in inches
        height: Wall height in inches
        angle: Angle from previous wall (-90, 0, or 90 degrees)
        name: Optional wall identifier for referencing in section configs
        depth: Available depth for cabinets in inches
    """

    model_config = ConfigDict(extra="forbid")

    length: float = Field(..., gt=0, description="Length along the wall in inches")
    height: float = Field(..., gt=0, description="Wall height in inches")
    angle: float = Field(default=0.0, description="Angle from previous wall (-90, 0, or 90)")
    name: str | None = Field(default=None, description="Optional wall identifier")
    depth: float = Field(default=12.0, gt=0, description="Available depth for cabinets")

    @field_validator("angle")
    @classmethod
    def validate_angle(cls, v: float) -> float:
        """Validate that angle is within the allowed range."""
        if not -135 <= v <= 135:
            raise ValueError("Angle must be between -135 and 135 degrees")
        return v


class CeilingSlopeConfig(BaseModel):
    """Configuration for sloped ceiling.

    Represents a sloped ceiling that affects cabinet height along a wall.
    Used for attic spaces, vaulted ceilings, or other non-flat ceiling conditions.

    Attributes:
        angle: Slope angle in degrees from horizontal (0-60).
        start_height: Height at slope start in inches.
        direction: Direction of slope - which way the ceiling descends.
        min_height: Minimum usable height in inches (default 24.0).
    """

    model_config = ConfigDict(extra="forbid")

    angle: float = Field(ge=0, le=60, description="Slope angle in degrees from horizontal")
    start_height: float = Field(gt=0, description="Height at slope start in inches")
    direction: Literal["left_to_right", "right_to_left", "front_to_back"]
    min_height: float = Field(default=24.0, ge=0, description="Minimum usable height in inches")


class SkylightConfig(BaseModel):
    """Configuration for skylight projection.

    Represents a skylight that may project down into the cabinet area,
    creating a void that panels must avoid.

    Attributes:
        x_position: Position along wall in inches (from left edge).
        width: Skylight width in inches.
        projection_depth: How far skylight projects down in inches.
        projection_angle: Angle from ceiling in degrees (90 = vertical projection).
    """

    model_config = ConfigDict(extra="forbid")

    x_position: float = Field(ge=0, description="Position along wall in inches")
    width: float = Field(gt=0, description="Skylight width in inches")
    projection_depth: float = Field(gt=0, description="How far skylight projects down in inches")
    projection_angle: float = Field(
        default=90.0, gt=0, le=180, description="Angle from ceiling (90 = vertical)"
    )


class CeilingConfig(BaseModel):
    """Container for ceiling-related configuration.

    Groups all ceiling-related configuration options including
    slope and skylights.

    Attributes:
        slope: Optional ceiling slope configuration.
        skylights: List of skylight configurations.
    """

    model_config = ConfigDict(extra="forbid")

    slope: CeilingSlopeConfig | None = None
    skylights: list[SkylightConfig] = Field(default_factory=list)


class OutsideCornerConfigSchema(BaseModel):
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

    model_config = ConfigDict(extra="forbid")

    treatment: Literal["angled_face", "butted_filler", "wrap_around"] = "angled_face"
    filler_width: float = Field(
        default=3.0, gt=0, description="Width for butted_filler treatment"
    )
    face_angle: float = Field(
        default=45.0, gt=0, lt=90, description="Angle for angled_face treatment"
    )


class RoomConfig(BaseModel):
    """Configuration for room geometry.

    Rooms define the overall geometry where cabinets will be placed.
    A room consists of one or more wall segments that can optionally
    form a closed polygon. Obstacles define features on walls that
    cabinets must avoid.

    Attributes:
        name: Room identifier
        walls: List of wall segments defining the room geometry
        is_closed: Whether walls form a closed polygon
        obstacles: List of obstacles on the room walls
        ceiling: Optional ceiling configuration (slope, skylights)
        outside_corner: Optional outside corner treatment configuration
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, description="Room identifier")
    walls: list[WallSegmentConfig] = Field(..., min_length=1, description="Wall segments")
    is_closed: bool = Field(default=False, description="Whether walls form a closed polygon")
    obstacles: list[ObstacleConfig] = Field(default_factory=list, description="Wall obstacles")
    ceiling: CeilingConfig | None = None
    outside_corner: OutsideCornerConfigSchema | None = None

    @field_validator("walls")
    @classmethod
    def validate_first_wall_angle(cls, v: list[WallSegmentConfig]) -> list[WallSegmentConfig]:
        """Validate that the first wall has angle=0."""
        if v and v[0].angle != 0:
            raise ValueError("First wall must have angle=0")
        return v


# =============================================================================
# Decorative Element Configurations (FRD-12)
# =============================================================================


class FaceFrameConfigSchema(BaseModel):
    """Configuration for face frame construction.

    Face frames consist of vertical stiles and horizontal rails
    that create an opening for doors or drawers.

    Attributes:
        stile_width: Width of vertical stiles in inches.
        rail_width: Width of horizontal rails in inches.
        joinery: Type of joint for stile/rail connections.
        material_thickness: Thickness of frame material in inches.
    """

    model_config = ConfigDict(extra="forbid")

    stile_width: float = Field(default=1.5, gt=0, le=6.0)
    rail_width: float = Field(default=1.5, gt=0, le=6.0)
    joinery: JoineryTypeConfig = JoineryTypeConfig.POCKET_SCREW
    material_thickness: float = Field(default=0.75, ge=0.5, le=1.5)


class CrownMoldingConfigSchema(BaseModel):
    """Configuration for crown molding zone.

    Defines the zone at cabinet top for crown molding installation.

    Attributes:
        height: Zone height for molding in inches.
        setback: Top panel setback distance in inches.
        nailer_width: Width of nailer strip in inches.
    """

    model_config = ConfigDict(extra="forbid")

    height: float = Field(default=3.0, gt=0, le=12.0)
    setback: float = Field(default=0.75, gt=0, le=3.0)
    nailer_width: float = Field(default=2.0, gt=0, le=6.0)


class BaseZoneConfigSchema(BaseModel):
    """Configuration for base/toe kick zone.

    Defines the zone at cabinet bottom for toe kick or base molding.

    Attributes:
        height: Zone height in inches.
        setback: Toe kick depth/recess in inches.
        zone_type: Type of base treatment.
    """

    model_config = ConfigDict(extra="forbid")

    height: float = Field(default=3.5, ge=3.0, le=6.0)
    setback: float = Field(default=3.0, ge=0, le=6.0)
    zone_type: Literal["toe_kick", "base_molding"] = "toe_kick"


class LightRailConfigSchema(BaseModel):
    """Configuration for light rail zone.

    Defines the zone under wall cabinets for lighting installation.

    Attributes:
        height: Zone height in inches.
        setback: Light rail setback in inches.
        generate_strip: Whether to generate a light rail strip piece.
    """

    model_config = ConfigDict(extra="forbid")

    height: float = Field(default=1.5, gt=0, le=4.0)
    setback: float = Field(default=0.25, ge=0, le=2.0)
    generate_strip: bool = True


class ArchTopConfigSchema(BaseModel):
    """Configuration for arched opening.

    Defines the geometry of an arched opening within a cabinet section.

    Attributes:
        arch_type: Type of arch curve.
        radius: Radius in inches, or "auto" to calculate from width.
        spring_height: Height where arch curve begins in inches.
    """

    model_config = ConfigDict(extra="forbid")

    arch_type: ArchTypeConfig = ArchTypeConfig.FULL_ROUND
    radius: float | Literal["auto"] = "auto"
    spring_height: float = Field(default=0.0, ge=0)

    @field_validator("radius")
    @classmethod
    def validate_radius(cls, v: float | str) -> float | str:
        """Validate radius is positive or 'auto'."""
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError("radius must be positive")
        return v


class EdgeProfileConfigSchema(BaseModel):
    """Configuration for edge routing profile.

    Defines the router profile applied to visible panel edges.

    Attributes:
        profile_type: Type of edge profile.
        size: Profile size/radius in inches.
        edges: Specific edges to profile, or "auto" for visible edges.
    """

    model_config = ConfigDict(extra="forbid")

    profile_type: EdgeProfileTypeConfig
    size: float = Field(gt=0, le=1.0)
    edges: list[Literal["top", "bottom", "left", "right", "front"]] | Literal["auto"] = "auto"


class ScallopConfigSchema(BaseModel):
    """Configuration for scalloped edge pattern.

    Defines a repeating scallop pattern for decorative edges.

    Attributes:
        depth: Depth of each scallop in inches.
        width: Nominal width of each scallop in inches.
        count: Number of scallops, or "auto" to fit evenly.
    """

    model_config = ConfigDict(extra="forbid")

    depth: float = Field(gt=0, le=3.0)
    width: float = Field(gt=0)
    count: int | Literal["auto"] = "auto"

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int | str) -> int | str:
        """Validate count is positive or 'auto'."""
        if isinstance(v, int) and v < 1:
            raise ValueError("count must be at least 1")
        return v


# =============================================================================
# Section and Cabinet Configurations
# =============================================================================


class SectionRowConfig(BaseModel):
    """Configuration for a vertical row within a section.

    This is used when a section needs vertical stacking (rows) rather than
    a single uniform configuration. Each row represents a vertical zone
    within the section's boundaries.

    Attributes:
        height: Row height in inches, or "fill" to auto-calculate remaining space
        section_type: Type for this row (open, doored, drawers, cubby)
        shelves: Number of shelves in this row (0 to 20)
        component_config: Component-specific configuration
        min_height: Minimum allowed height in inches (default 6.0)
        max_height: Maximum allowed height in inches (optional)
    """

    model_config = ConfigDict(extra="forbid")

    height: float | Literal["fill"] = "fill"
    section_type: SectionTypeConfig = Field(
        default=SectionTypeConfig.OPEN, description="Type for this row"
    )
    shelves: int = Field(default=0, ge=0, le=20, description="Number of shelves")
    component_config: dict[str, Any] = Field(
        default_factory=dict, description="Component-specific configuration"
    )
    min_height: float = Field(
        default=6.0, gt=0, description="Minimum allowed height in inches"
    )
    max_height: float | None = Field(
        default=None, gt=0, description="Maximum allowed height in inches"
    )

    @field_validator("height")
    @classmethod
    def validate_height(cls, v: float | str) -> float | str:
        """Validate that numeric height is positive."""
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError("height must be positive")
        return v

    @model_validator(mode="after")
    def validate_height_constraints(self) -> "SectionRowConfig":
        """Validate that max_height >= min_height when both are set."""
        if self.max_height is not None and self.max_height < self.min_height:
            raise ValueError(
                f"max_height ({self.max_height}) must be greater than or equal to "
                f"min_height ({self.min_height})"
            )
        return self


class SectionConfig(BaseModel):
    """Configuration for a cabinet section.

    A section can be configured in two ways:
    1. Flat configuration: Use shelves/section_type for uniform section
    2. Row-based configuration: Use rows for vertical stacking within the section

    Attributes:
        width: Section width in inches, or "fill" to auto-calculate remaining space
        shelves: Number of shelves in this section (0 to 20). Ignored if rows is set.
        wall: Wall name or index where this section is placed (optional)
        height_mode: How the section uses wall height (full, lower, upper, auto)
        section_type: Type of cabinet section (open, doored, drawers, cubby).
            Ignored if rows is set.
        depth: Per-section depth override in inches (optional)
        min_width: Minimum allowed width in inches (default 6.0)
        max_width: Maximum allowed width in inches (optional)
        component_config: Component-specific configuration passed to the component
        rows: Vertical rows within this section for multi-row layout (optional).
            When set, shelves and section_type should be at defaults.
        arch_top: Arch top configuration for arched openings (optional, FRD-12)
        edge_profile: Edge profile for shelves/panels (optional, FRD-12)
        scallop: Scallop pattern for valances (optional, FRD-12)
    """

    model_config = ConfigDict(extra="forbid")

    width: float | Literal["fill"] = "fill"
    shelves: int = Field(default=0, ge=0, le=20)
    wall: str | int | None = Field(default=None, description="Wall name or index")
    height_mode: HeightMode | None = Field(
        default=None, description="Height mode for the section"
    )
    section_type: SectionTypeConfig = Field(
        default=SectionTypeConfig.OPEN, description="Type of cabinet section"
    )
    depth: float | None = Field(
        default=None, gt=0, description="Per-section depth override in inches"
    )
    min_width: float = Field(
        default=6.0, gt=0, description="Minimum allowed width in inches"
    )
    max_width: float | None = Field(
        default=None, gt=0, description="Maximum allowed width in inches"
    )
    component_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Component-specific configuration passed to the component",
    )

    # Decorative element fields (FRD-12)
    arch_top: ArchTopConfigSchema | None = Field(
        default=None, description="Arch top configuration (optional)"
    )
    edge_profile: EdgeProfileConfigSchema | None = Field(
        default=None, description="Edge profile for shelves/panels (optional)"
    )
    scallop: ScallopConfigSchema | None = Field(
        default=None, description="Scallop pattern for valances (optional)"
    )

    # Row-based layout (alternative to flat shelves/section_type)
    rows: list[SectionRowConfig] | None = Field(
        default=None,
        max_length=10,
        description="Vertical rows within this section for multi-row layout",
    )

    @field_validator("width")
    @classmethod
    def validate_width(cls, v: float | str) -> float | str:
        """Validate that numeric width is positive."""
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError("width must be positive")
        return v

    @model_validator(mode="after")
    def validate_width_constraints(self) -> "SectionConfig":
        """Validate that max_width >= min_width when both are set."""
        if self.max_width is not None and self.max_width < self.min_width:
            raise ValueError(
                f"max_width ({self.max_width}) must be greater than or equal to "
                f"min_width ({self.min_width})"
            )
        return self

    @model_validator(mode="after")
    def validate_rows_vs_flat_properties(self) -> "SectionConfig":
        """Validate that rows and flat section_type/shelves are mutually exclusive."""
        if self.rows:
            if self.shelves != 0:
                raise ValueError(
                    "Cannot specify 'shelves' when 'rows' is defined. "
                    "Specify shelves within each row instead."
                )
            if self.section_type != SectionTypeConfig.OPEN:
                raise ValueError(
                    "Cannot specify 'section_type' when 'rows' is defined. "
                    "Specify section_type within each row instead."
                )
        return self


class RowConfig(BaseModel):
    """Configuration for a horizontal row (vertical zone) within a cabinet.

    Rows allow vertically stacking different section layouts. Each row has its
    own height and contains horizontally arranged sections. This enables layouts
    like: bottom doored cabinets, drawer row above, open shelves, and cubbies at top.

    Attributes:
        height: Row height in inches, or "fill" to auto-calculate remaining space
        sections: List of section configurations within this row (min 1)
        min_height: Minimum allowed height in inches (default 6.0)
        max_height: Maximum allowed height in inches (optional)
    """

    model_config = ConfigDict(extra="forbid")

    height: float | Literal["fill"] = "fill"
    sections: list[SectionConfig] = Field(..., min_length=1, max_length=20)
    min_height: float = Field(
        default=6.0, gt=0, description="Minimum allowed height in inches"
    )
    max_height: float | None = Field(
        default=None, gt=0, description="Maximum allowed height in inches"
    )

    @field_validator("height")
    @classmethod
    def validate_height(cls, v: float | str) -> float | str:
        """Validate that numeric height is positive."""
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError("height must be positive")
        return v

    @model_validator(mode="after")
    def validate_height_constraints(self) -> "RowConfig":
        """Validate that max_height >= min_height when both are set."""
        if self.max_height is not None and self.max_height < self.min_height:
            raise ValueError(
                f"max_height ({self.max_height}) must be greater than or equal to "
                f"min_height ({self.min_height})"
            )
        return self


class CabinetConfig(BaseModel):
    """Configuration for the cabinet dimensions and structure.

    Supports two layout modes:
    1. Single-row layout: Use `sections` for horizontal-only section arrangement
    2. Multi-row layout: Use `rows` for vertically stacked horizontal sections

    Attributes:
        width: Overall cabinet width in inches (6.0 to 240.0)
        height: Overall cabinet height in inches (6.0 to 120.0)
        depth: Overall cabinet depth in inches (4.0 to 36.0)
        material: Primary material for cabinet construction
        back_material: Material for back panel (optional, defaults to material if not specified)
        sections: List of section configurations for single-row layout (1 to 20 sections)
        rows: List of row configurations for multi-row layout (1 to 10 rows)
        default_shelves: Default shelf count for sections that don't specify shelves (0 to 20)
        face_frame: Face frame configuration (optional, FRD-12)
        crown_molding: Crown molding zone configuration (optional, FRD-12)
        base_zone: Base/toe kick zone configuration (optional, FRD-12)
        light_rail: Light rail zone configuration (optional, FRD-12)
    """

    model_config = ConfigDict(extra="forbid")

    width: float = Field(..., ge=6.0, le=240.0)
    height: float = Field(..., ge=6.0, le=120.0)
    depth: float = Field(..., ge=4.0, le=36.0)
    material: MaterialConfig = Field(default_factory=MaterialConfig)
    back_material: MaterialConfig | None = None
    sections: list[SectionConfig] = Field(default_factory=list, max_length=20)
    rows: list[RowConfig] | None = Field(
        default=None, max_length=10, description="Row configurations for multi-row layout"
    )
    default_shelves: int = Field(
        default=0, ge=0, le=20, description="Default shelf count for sections"
    )

    # Decorative element fields (FRD-12)
    face_frame: FaceFrameConfigSchema | None = Field(
        default=None, description="Face frame configuration (optional)"
    )
    crown_molding: CrownMoldingConfigSchema | None = Field(
        default=None, description="Crown molding zone (optional)"
    )
    base_zone: BaseZoneConfigSchema | None = Field(
        default=None, description="Base/toe kick zone (optional)"
    )
    light_rail: LightRailConfigSchema | None = Field(
        default=None, description="Light rail zone (optional)"
    )

    @field_validator("sections")
    @classmethod
    def validate_sections_not_empty_if_provided(
        cls, v: list[SectionConfig]
    ) -> list[SectionConfig]:
        """Ensure sections list has at least 1 section if provided."""
        # Empty list is allowed - it means use default single section
        return v

    @model_validator(mode="after")
    def validate_rows_or_sections(self) -> "CabinetConfig":
        """Validate that only one of 'rows' or 'sections' is used, not both."""
        if self.rows and self.sections:
            raise ValueError(
                "Specify either 'rows' for multi-row layout or 'sections' for "
                "single-row layout, not both"
            )
        return self


# =============================================================================
# Bin Packing Configuration (FRD-13)
# =============================================================================


class SheetSizeConfigSchema(BaseModel):
    """Configuration for sheet material dimensions.

    Standard sheet sizes:
    - 4'x8' (48"x96") - most common plywood
    - 5'x5' (60"x60") - Baltic birch

    Attributes:
        width: Sheet width in inches (default 48.0 for 4' sheets).
        height: Sheet height in inches (default 96.0 for 8' sheets).
    """

    model_config = ConfigDict(extra="forbid")

    width: float = Field(default=48.0, gt=0, le=120, description="Sheet width in inches")
    height: float = Field(default=96.0, gt=0, le=120, description="Sheet height in inches")


class SplittablePanelType(str, Enum):
    """Panel types that can be split when oversized.

    These panel types are typically hidden or can have seams without
    affecting appearance or function.
    """

    BACK = "back"


class BinPackingConfigSchema(BaseModel):
    """Configuration for bin packing cut optimization.

    Controls how cut pieces are arranged on sheet goods to minimize waste.
    When enabled, the cut list is optimized using a guillotine-compatible
    bin packing algorithm.

    Attributes:
        enabled: Whether bin packing optimization is enabled.
        sheet_size: Sheet dimensions configuration.
        kerf: Saw blade kerf width in inches (1/8" typical).
        edge_allowance: Unusable material at sheet edges in inches.
        min_offcut_size: Minimum dimension for tracking offcuts.
        allow_panel_splitting: Whether oversized panels can be split.
        splittable_types: Panel types that can be split when oversized.
        split_overlap: Overlap amount at panel joints in inches.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable bin packing optimization")
    sheet_size: SheetSizeConfigSchema = Field(
        default_factory=SheetSizeConfigSchema,
        description="Sheet dimensions",
    )
    kerf: float = Field(
        default=0.125,
        ge=0,
        le=0.5,
        description="Saw kerf width in inches",
    )
    edge_allowance: float = Field(
        default=0.5,
        ge=0,
        le=2.0,
        description="Edge allowance in inches",
    )
    min_offcut_size: float = Field(
        default=6.0,
        ge=0,
        description="Minimum offcut dimension to track",
    )
    allow_panel_splitting: bool = Field(
        default=True,
        description="Allow oversized panels to be split into multiple pieces",
    )
    splittable_types: list[SplittablePanelType] = Field(
        default_factory=lambda: [SplittablePanelType.BACK],
        description="Panel types that can be split when oversized",
    )
    split_overlap: float = Field(
        default=1.0,
        ge=0,
        le=6.0,
        description="Overlap at panel joints in inches (for structural integrity)",
    )

    @field_validator("kerf")
    @classmethod
    def validate_kerf(cls, v: float) -> float:
        """Validate kerf is within reasonable bounds."""
        if v > 0.5:
            raise ValueError("Kerf cannot exceed 0.5 inches")
        return v


# =============================================================================
# Woodworking Intelligence Configuration (FRD-14)
# =============================================================================


class JoineryConfigSchema(BaseModel):
    """Configuration for joinery specifications.

    Controls default joint types and dimension calculations for
    cabinet joinery.

    Attributes:
        default_shelf_joint: Default joint type for shelf-to-side connections.
        default_back_joint: Default joint type for back panel attachment.
        dado_depth_ratio: Ratio of material thickness for dado depth (default 0.333).
        rabbet_depth_ratio: Ratio of material thickness for rabbet depth (default 0.5).
        dowel_edge_offset: Distance from edges for dowel placement in inches.
        dowel_spacing: Spacing between dowels in inches.
        pocket_hole_edge_offset: Distance from edges for pocket holes in inches.
        pocket_hole_spacing: Spacing between pocket holes in inches.
    """

    model_config = ConfigDict(extra="forbid")

    default_shelf_joint: JoineryTypeConfig = JoineryTypeConfig.DADO
    default_back_joint: JoineryTypeConfig = JoineryTypeConfig.RABBET
    dado_depth_ratio: float = Field(
        default=0.333,
        gt=0,
        lt=0.5,
        description="Ratio of material thickness for dado depth",
    )
    rabbet_depth_ratio: float = Field(
        default=0.5,
        gt=0,
        lt=1.0,
        description="Ratio of material thickness for rabbet depth",
    )
    dowel_edge_offset: float = Field(
        default=2.0,
        gt=0,
        le=6.0,
        description="Distance from edges for first/last dowels",
    )
    dowel_spacing: float = Field(
        default=6.0,
        gt=2.0,
        le=12.0,
        description="Spacing between dowels",
    )
    pocket_hole_edge_offset: float = Field(
        default=4.0,
        gt=0,
        le=8.0,
        description="Distance from edges for first/last pocket holes",
    )
    pocket_hole_spacing: float = Field(
        default=8.0,
        gt=4.0,
        le=16.0,
        description="Spacing between pocket holes",
    )


class SpanLimitsConfigSchema(BaseModel):
    """Configuration for shelf span limits by material.

    Allows overriding default maximum spans for each material type.
    Values are in inches.

    Attributes:
        plywood_3_4: Maximum span for 3/4" plywood (default 36").
        mdf_3_4: Maximum span for 3/4" MDF (default 24").
        particle_board_3_4: Maximum span for 3/4" particle board (default 24").
        solid_wood_1: Maximum span for 1" solid wood (default 42").
    """

    model_config = ConfigDict(extra="forbid")

    plywood_3_4: float = Field(default=36.0, gt=12.0, le=60.0)
    mdf_3_4: float = Field(default=24.0, gt=12.0, le=48.0)
    particle_board_3_4: float = Field(default=24.0, gt=12.0, le=48.0)
    solid_wood_1: float = Field(default=42.0, gt=12.0, le=72.0)


class HardwareConfigSchema(BaseModel):
    """Configuration for hardware calculation.

    Controls how hardware quantities are calculated and whether
    overage is added for waste/mistakes.

    Attributes:
        add_overage: Whether to add overage to hardware quantities.
        overage_percent: Percentage of overage to add (default 10%).
        case_screw_spacing: Spacing between case assembly screws in inches.
        back_panel_screw_spacing: Spacing between back panel screws in inches.
    """

    model_config = ConfigDict(extra="forbid")

    add_overage: bool = True
    overage_percent: float = Field(
        default=10.0,
        ge=0,
        le=50,
        description="Percentage of overage to add",
    )
    case_screw_spacing: float = Field(
        default=8.0,
        gt=4.0,
        le=16.0,
        description="Spacing between case screws",
    )
    back_panel_screw_spacing: float = Field(
        default=6.0,
        gt=3.0,
        le=12.0,
        description="Spacing between back panel screws",
    )


class WoodworkingConfigSchema(BaseModel):
    """Container for woodworking intelligence configuration.

    Groups all woodworking-related configuration options including
    joinery, span limits, and hardware settings.

    Attributes:
        joinery: Joinery configuration options.
        span_limits: Material-specific span limit overrides.
        hardware: Hardware calculation configuration.
        warnings_enabled: Whether to generate span and capacity warnings.
        grain_recommendations_enabled: Whether to add grain direction recommendations.
        capacity_estimates_enabled: Whether to include weight capacity estimates.
    """

    model_config = ConfigDict(extra="forbid")

    joinery: JoineryConfigSchema | None = Field(
        default=None,
        description="Joinery configuration (optional)",
    )
    span_limits: SpanLimitsConfigSchema | None = Field(
        default=None,
        description="Span limit overrides (optional)",
    )
    hardware: HardwareConfigSchema | None = Field(
        default=None,
        description="Hardware configuration (optional)",
    )
    warnings_enabled: bool = Field(
        default=True,
        description="Whether to generate woodworking warnings",
    )
    grain_recommendations_enabled: bool = Field(
        default=True,
        description="Whether to add grain direction recommendations",
    )
    capacity_estimates_enabled: bool = Field(
        default=True,
        description="Whether to include weight capacity estimates",
    )


# =============================================================================
# Infrastructure Integration Configuration (FRD-15)
# =============================================================================


class PositionConfigSchema(BaseModel):
    """Configuration for a 2D position.

    Represents a position on a panel or within a section,
    typically used for placing infrastructure elements.

    Attributes:
        x: Horizontal position in inches from the left edge.
        y: Vertical position in inches from the bottom edge.
    """

    model_config = ConfigDict(extra="forbid")

    x: float = Field(..., description="Horizontal position in inches")
    y: float = Field(..., description="Vertical position in inches")


class LightingConfigSchema(BaseModel):
    """Configuration for lighting installation.

    Defines lighting elements to be installed in or around cabinets,
    including the routing channels needed for wiring.

    Attributes:
        type: Type of lighting (led_strip, puck_light, accent).
        location: Where the lighting is installed relative to cabinet.
        section_indices: List of section indices where lighting is installed.
        length: Length of LED strip in inches (for led_strip type).
        diameter: Diameter of puck lights in inches (for puck_light type).
        channel_width: Width of wiring channel in inches.
        channel_depth: Depth of wiring channel in inches.
        position: Optional specific position for the lighting element.
    """

    model_config = ConfigDict(extra="forbid")

    type: LightingTypeConfig = Field(..., description="Type of lighting")
    location: LightingLocationConfig = Field(
        ..., description="Installation location"
    )
    section_indices: list[int] = Field(
        ..., min_length=1, description="Section indices where lighting is installed"
    )
    length: float | None = Field(
        default=None,
        gt=0,
        description="LED strip length in inches",
    )
    diameter: float = Field(
        default=2.5,
        gt=0,
        le=6.0,
        description="Puck light diameter in inches",
    )
    channel_width: float = Field(
        default=0.5,
        gt=0,
        le=2.0,
        description="Wiring channel width in inches",
    )
    channel_depth: float = Field(
        default=0.25,
        gt=0,
        le=1.0,
        description="Wiring channel depth in inches",
    )
    position: PositionConfigSchema | None = Field(
        default=None,
        description="Specific position for the lighting element",
    )

    @model_validator(mode="after")
    def validate_lighting_type_requirements(self) -> "LightingConfigSchema":
        """Validate type-specific requirements."""
        if self.type == LightingTypeConfig.LED_STRIP and self.length is None:
            raise ValueError("LED strip lighting requires 'length' to be specified")
        return self


class OutletConfigSchema(BaseModel):
    """Configuration for electrical outlet placement.

    Defines an electrical outlet to be installed within a cabinet,
    including the panel location and conduit routing direction.

    Attributes:
        type: Type of outlet (single, double, gfi).
        section_index: Index of the section where outlet is installed.
        panel: Panel where outlet is mounted (back, left_side, right_side).
        position: Position on the panel for the outlet.
        conduit_direction: Direction for conduit exit from the outlet box.
    """

    model_config = ConfigDict(extra="forbid")

    type: OutletTypeConfig = Field(..., description="Type of outlet")
    section_index: int = Field(
        ..., ge=0, description="Section index for outlet installation"
    )
    panel: str = Field(
        ...,
        pattern=r"^(back|left_side|right_side)$",
        description="Panel for outlet mounting",
    )
    position: PositionConfigSchema = Field(..., description="Position on panel")
    conduit_direction: ConduitDirectionConfig = Field(
        default=ConduitDirectionConfig.BOTTOM,
        description="Direction for conduit routing",
    )


class GrommetConfigSchema(BaseModel):
    """Configuration for cable pass-through grommet.

    Defines a cable grommet for routing cables through panels,
    providing a clean finished appearance for cable routing.

    Attributes:
        size: Grommet diameter in inches (2.0, 2.5, or 3.0 typical sizes).
        panel: Panel where grommet is installed.
        position: Position on the panel for the grommet.
        section_index: Optional section index if grommet is section-specific.
    """

    model_config = ConfigDict(extra="forbid")

    size: float = Field(
        ...,
        gt=0,
        le=6.0,
        description="Grommet diameter in inches",
    )
    panel: str = Field(..., description="Panel for grommet installation")
    position: PositionConfigSchema = Field(..., description="Position on panel")
    section_index: int | None = Field(
        default=None,
        ge=0,
        description="Section index if grommet is section-specific",
    )

    @field_validator("size")
    @classmethod
    def validate_common_sizes(cls, v: float) -> float:
        """Validate grommet size is a common standard size."""
        common_sizes = {2.0, 2.5, 3.0}
        if v not in common_sizes:
            # Allow non-standard sizes but they should be reasonable
            if v < 0.5 or v > 6.0:
                raise ValueError(
                    f"Grommet size {v} is outside reasonable range (0.5-6.0 inches)"
                )
        return v


class CableChannelConfigSchema(BaseModel):
    """Configuration for cable routing channel.

    Defines a linear channel for routing cables within or through cabinets,
    typically milled into the back of panels.

    Attributes:
        start: Starting position of the channel.
        end: Ending position of the channel.
        width: Channel width in inches.
        depth: Channel depth in inches.
    """

    model_config = ConfigDict(extra="forbid")

    start: PositionConfigSchema = Field(..., description="Channel start position")
    end: PositionConfigSchema = Field(..., description="Channel end position")
    width: float = Field(
        default=2.0,
        gt=0,
        le=4.0,
        description="Channel width in inches",
    )
    depth: float = Field(
        default=1.0,
        gt=0,
        le=2.0,
        description="Channel depth in inches",
    )


class VentilationConfigSchema(BaseModel):
    """Configuration for ventilation cutouts.

    Defines ventilation areas in panels for heat dissipation
    from electronics or other heat-generating equipment.

    Attributes:
        pattern: Pattern of ventilation holes (grid, slot, circular).
        panel: Panel where ventilation is located.
        position: Position of the ventilation area on the panel.
        width: Width of the ventilation area in inches.
        height: Height of the ventilation area in inches.
        hole_size: Size of individual holes in inches.
    """

    model_config = ConfigDict(extra="forbid")

    pattern: VentilationPatternConfig = Field(
        ..., description="Ventilation hole pattern"
    )
    panel: str = Field(..., description="Panel for ventilation")
    position: PositionConfigSchema = Field(
        ..., description="Position of ventilation area"
    )
    width: float = Field(
        ..., gt=0, description="Ventilation area width in inches"
    )
    height: float = Field(
        ..., gt=0, description="Ventilation area height in inches"
    )
    hole_size: float = Field(
        default=0.25,
        gt=0,
        le=2.0,
        description="Individual hole size in inches",
    )


class WireRouteConfigSchema(BaseModel):
    """Configuration for wire routing path.

    Defines a path for routing wires through the cabinet structure,
    including waypoints and panel penetration points.

    Attributes:
        waypoints: List of positions defining the wire route path.
        hole_diameter: Diameter of holes at panel penetrations in inches.
        panel_penetrations: List of panels the wire route passes through.
    """

    model_config = ConfigDict(extra="forbid")

    waypoints: list[PositionConfigSchema] = Field(
        ...,
        min_length=2,
        description="Waypoints defining the wire route",
    )
    hole_diameter: float = Field(
        default=0.75,
        gt=0,
        le=3.0,
        description="Hole diameter at panel penetrations in inches",
    )
    panel_penetrations: list[str] = Field(
        default_factory=list,
        description="Panels the wire route passes through",
    )


class InfrastructureConfigSchema(BaseModel):
    """Container for all infrastructure integration configuration.

    Groups all infrastructure-related configuration options including
    lighting, electrical outlets, cable management, and ventilation.

    Attributes:
        lighting: List of lighting configurations.
        outlets: List of electrical outlet configurations.
        grommets: List of cable grommet configurations.
        cable_channels: List of cable channel configurations.
        ventilation: List of ventilation area configurations.
        wire_routes: List of wire routing path configurations.
    """

    model_config = ConfigDict(extra="forbid")

    lighting: list[LightingConfigSchema] = Field(
        default_factory=list,
        description="Lighting configurations",
    )
    outlets: list[OutletConfigSchema] = Field(
        default_factory=list,
        description="Electrical outlet configurations",
    )
    grommets: list[GrommetConfigSchema] = Field(
        default_factory=list,
        description="Cable grommet configurations",
    )
    cable_channels: list[CableChannelConfigSchema] = Field(
        default_factory=list,
        description="Cable channel configurations",
    )
    ventilation: list[VentilationConfigSchema] = Field(
        default_factory=list,
        description="Ventilation area configurations",
    )
    wire_routes: list[WireRouteConfigSchema] = Field(
        default_factory=list,
        description="Wire routing path configurations",
    )


# =============================================================================
# Installation Support Configuration (FRD-17)
# =============================================================================


class CleatConfigSchema(BaseModel):
    """French cleat configuration.

    Defines the parameters for French cleat mounting system,
    including position, width, and bevel angle.

    Attributes:
        position_from_top: Distance from cabinet top to cleat position in inches.
        width_percentage: Cleat width as percentage of cabinet width (75-100%).
        bevel_angle: Bevel angle for cleat in degrees (30-45 degrees standard).
    """

    model_config = ConfigDict(extra="forbid")

    position_from_top: float = Field(
        default=4.0,
        ge=2.0,
        le=12.0,
        description="Distance from cabinet top to cleat in inches",
    )
    width_percentage: float = Field(
        default=90.0,
        ge=75.0,
        le=100.0,
        description="Cleat width as percentage of cabinet width",
    )
    bevel_angle: float = Field(
        default=45.0,
        ge=30.0,
        le=45.0,
        description="Bevel angle for cleat in degrees",
    )


class InstallationConfigSchema(BaseModel):
    """Installation configuration schema.

    Defines all parameters for cabinet installation planning,
    including wall type, stud spacing, mounting system, and load expectations.

    Attributes:
        wall_type: Type of wall construction (drywall, plaster, concrete, etc.).
        wall_thickness: Wall material thickness in inches.
        stud_spacing: Distance between wall studs in inches (16" or 24" typical).
        stud_offset: Distance from wall start to first stud in inches.
        mounting_system: Cabinet mounting method.
        expected_load: Expected load category for the cabinet.
        cleat: Optional French cleat configuration (when using french_cleat system).
        generate_instructions: Whether to generate installation instructions.
    """

    model_config = ConfigDict(extra="forbid")

    wall_type: WallTypeConfig = Field(
        default=WallTypeConfig.DRYWALL,
        description="Wall construction type",
    )
    wall_thickness: float = Field(
        default=0.5,
        ge=0.25,
        le=2.0,
        description="Wall material thickness in inches",
    )
    stud_spacing: float = Field(
        default=16.0,
        ge=12.0,
        le=32.0,
        description="Distance between wall studs in inches",
    )
    stud_offset: float = Field(
        default=0.0,
        ge=0.0,
        description="Distance from wall start to first stud in inches",
    )
    mounting_system: MountingSystemConfig = Field(
        default=MountingSystemConfig.DIRECT_TO_STUD,
        description="Cabinet mounting method",
    )
    expected_load: LoadCategoryConfig = Field(
        default=LoadCategoryConfig.MEDIUM,
        description="Expected load category",
    )
    cleat: CleatConfigSchema | None = Field(
        default=None,
        description="French cleat configuration (optional)",
    )
    generate_instructions: bool = Field(
        default=True,
        description="Whether to generate installation instructions",
    )

    @model_validator(mode="after")
    def validate_mounting_system_wall_type_compatibility(
        self,
    ) -> "InstallationConfigSchema":
        """Validate that mounting system is compatible with wall type.

        Toggle bolts are not valid for concrete, CMU, or brick walls
        as they require a hollow cavity to expand into.
        """
        masonry_wall_types = {
            WallTypeConfig.CONCRETE,
            WallTypeConfig.CMU,
            WallTypeConfig.BRICK,
        }
        if (
            self.mounting_system == MountingSystemConfig.TOGGLE_BOLT
            and self.wall_type in masonry_wall_types
        ):
            raise ValueError(
                f"Toggle bolt mounting system is not valid for {self.wall_type.value} walls. "
                "Toggle bolts require a hollow wall cavity. Use direct_to_stud or french_cleat "
                "with appropriate masonry anchors instead."
            )
        return self


# =============================================================================
# Built-in Desk Enums (FRD-18)
# =============================================================================


class DeskTypeConfig(str, Enum):
    """Desk configuration type.

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


class EdgeTreatmentConfig(str, Enum):
    """Desktop edge treatment type.

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


class PedestalTypeConfig(str, Enum):
    """Desk pedestal type.

    Defines the different pedestal configurations that support desk surfaces.

    Attributes:
        FILE: File drawer pedestal with pencil drawer above file drawer.
        STORAGE: Multiple storage drawers pedestal.
        OPEN: Open shelving pedestal without drawers.
    """

    FILE = "file"
    STORAGE = "storage"
    OPEN = "open"


class DeskMountingConfig(str, Enum):
    """Desktop mounting method.

    Defines how the desktop is supported.

    Attributes:
        PEDESTAL: Supported by desk pedestals.
        FLOATING: Wall-mounted with cleats.
        LEGS: Supported by desk legs.
    """

    PEDESTAL = "pedestal"
    FLOATING = "floating"
    LEGS = "legs"


# =============================================================================
# Built-in Desk Configuration Models (FRD-18)
# =============================================================================


class DeskGrommetConfigSchema(BaseModel):
    """Cable grommet configuration for desk surfaces.

    Specifies the position and size of a cable grommet cutout in the desktop.

    Attributes:
        x_position: Distance from left edge of desktop in inches.
        y_position: Distance from front edge of desktop in inches.
        diameter: Grommet diameter in inches (1.5-3.5", default 2.5").
    """

    model_config = ConfigDict(extra="forbid")

    x_position: float = Field(..., description="Distance from left edge")
    y_position: float = Field(..., description="Distance from front edge")
    diameter: float = Field(default=2.5, ge=1.5, le=3.5)


class DeskSurfaceConfigSchema(BaseModel):
    """Desktop surface configuration.

    Specifies the dimensions and features of the desk surface.

    Attributes:
        desk_height: Height of desk surface in inches (26-50", default 30").
        depth: Desktop depth in inches (18-36", default 24").
        thickness: Desktop panel thickness in inches (0.75-1.5", default 1.0").
        edge_treatment: Edge finishing type (square, bullnose, waterfall, eased).
        grommets: List of cable grommet configurations.
        mounting: Desktop mounting method (pedestal, floating, legs).
        exposed_left: Apply edge banding to left edge.
        exposed_right: Apply edge banding to right edge.
    """

    model_config = ConfigDict(extra="forbid")

    desk_height: float = Field(default=30.0, ge=26.0, le=50.0)
    depth: float = Field(default=24.0, ge=18.0, le=36.0)
    thickness: float = Field(default=1.0, ge=0.75, le=1.5)
    edge_treatment: EdgeTreatmentConfig = EdgeTreatmentConfig.SQUARE
    grommets: list[DeskGrommetConfigSchema] = Field(default_factory=list)
    mounting: DeskMountingConfig = DeskMountingConfig.PEDESTAL
    exposed_left: bool = False
    exposed_right: bool = False


class DeskPedestalConfigSchema(BaseModel):
    """Desk pedestal configuration.

    Specifies the type, size, and position of a desk pedestal.

    Attributes:
        pedestal_type: Type of pedestal (file, storage, open).
        width: Pedestal width in inches (12-30", default 18").
        position: Position relative to knee clearance (left or right).
        drawer_count: Number of drawers for storage type (1-6, default 3).
        file_type: Type of files for file pedestal (letter or legal).
        wire_chase: Whether to include a wire chase for cable routing.
    """

    model_config = ConfigDict(extra="forbid")

    pedestal_type: PedestalTypeConfig = PedestalTypeConfig.STORAGE
    width: float = Field(default=18.0, ge=12.0, le=30.0)
    position: Literal["left", "right"] = "left"
    drawer_count: int = Field(default=3, ge=1, le=6)
    file_type: Literal["letter", "legal"] = "letter"
    wire_chase: bool = False


class KeyboardTrayConfigSchema(BaseModel):
    """Keyboard tray configuration.

    Specifies the dimensions and features of a pull-out keyboard tray.

    Attributes:
        width: Tray width in inches (15-30", default 20").
        depth: Tray depth in inches (8-14", default 10").
        slide_length: Slide length in inches (10-20", default 14").
        enclosed: Add enclosure rails for dust protection.
        wrist_rest: Include padded wrist rest.
    """

    model_config = ConfigDict(extra="forbid")

    width: float = Field(default=20.0, ge=15.0, le=30.0)
    depth: float = Field(default=10.0, ge=8.0, le=14.0)
    slide_length: int = Field(default=14, ge=10, le=20)
    enclosed: bool = False
    wrist_rest: bool = False


class HutchConfigSchema(BaseModel):
    """Desk hutch configuration.

    Specifies the dimensions and features of an upper storage hutch.

    Attributes:
        height: Hutch height in inches (12-48", default 24").
        depth: Hutch depth in inches (6-16", default 12").
        head_clearance: Space above desktop in inches (12-24", default 15").
        shelf_count: Number of interior shelves (0-4, default 1).
        doors: Include cabinet doors.
        task_light_zone: Include task lighting mounting zone.
    """

    model_config = ConfigDict(extra="forbid")

    height: float = Field(default=24.0, ge=12.0, le=48.0)
    depth: float = Field(default=12.0, ge=6.0, le=16.0)
    head_clearance: float = Field(default=15.0, ge=12.0, le=24.0)
    shelf_count: int = Field(default=1, ge=0, le=4)
    doors: bool = False
    task_light_zone: bool = True


class MonitorShelfConfigSchema(BaseModel):
    """Monitor shelf configuration.

    Specifies the dimensions and features of a monitor riser shelf.

    Attributes:
        width: Shelf width in inches (12-60", default 24").
        height: Riser height in inches (4-12", default 6").
        depth: Shelf depth in inches (6-14", default 10").
        cable_pass: Include cable pass-through gap at back.
        arm_mount: Include monitor arm mounting hardware.
    """

    model_config = ConfigDict(extra="forbid")

    width: float = Field(default=24.0, ge=12.0, le=60.0)
    height: float = Field(default=6.0, ge=4.0, le=12.0)
    depth: float = Field(default=10.0, ge=6.0, le=14.0)
    cable_pass: bool = True
    arm_mount: bool = False


class DeskSectionConfigSchema(BaseModel):
    """Complete desk section configuration.

    Top-level configuration for a desk section, combining all desk components.

    Attributes:
        desk_type: Type of desk layout (single, l_shaped, corner, standing).
        surface: Desktop surface configuration.
        pedestals: List of pedestal configurations.
        keyboard_tray: Optional keyboard tray configuration.
        hutch: Optional hutch configuration.
        monitor_shelf: Optional monitor shelf configuration.
        knee_clearance_width: Minimum knee clearance width in inches (20"+, default 24").
        modesty_panel: Include modesty panel at back of knee zone.
    """

    model_config = ConfigDict(extra="forbid")

    desk_type: DeskTypeConfig = DeskTypeConfig.SINGLE
    surface: DeskSurfaceConfigSchema = Field(default_factory=DeskSurfaceConfigSchema)
    pedestals: list[DeskPedestalConfigSchema] = Field(default_factory=list)
    keyboard_tray: KeyboardTrayConfigSchema | None = None
    hutch: HutchConfigSchema | None = None
    monitor_shelf: MonitorShelfConfigSchema | None = None
    knee_clearance_width: float = Field(default=24.0, ge=20.0)
    modesty_panel: bool = True

    @model_validator(mode="after")
    def validate_standing_desk(self) -> "DeskSectionConfigSchema":
        """Validate standing desk specific constraints."""
        if self.desk_type == DeskTypeConfig.STANDING:
            if self.surface.desk_height < 38.0:
                raise ValueError(
                    f"Standing desk height {self.surface.desk_height}\" "
                    "must be at least 38\""
                )
        return self


# =============================================================================
# Entertainment Center Enums (FRD-19)
# =============================================================================


class EquipmentTypeConfig(str, Enum):
    """Equipment type for media shelves.

    Defines the type of AV equipment to accommodate, which determines
    default shelf dimensions and ventilation requirements.

    Attributes:
        RECEIVER: AV receiver (typically 17"W x 6"H x 15"D, generates heat).
        CONSOLE_HORIZONTAL: Gaming console in horizontal orientation.
        CONSOLE_VERTICAL: Gaming console in vertical orientation.
        STREAMING: Streaming device (small form factor).
        CABLE_BOX: Cable/satellite box.
        BLU_RAY: Blu-ray/DVD player.
        TURNTABLE: Vinyl turntable (requires vibration isolation).
        CUSTOM: Custom equipment with user-specified dimensions.
    """

    RECEIVER = "receiver"
    CONSOLE_HORIZONTAL = "console_horizontal"
    CONSOLE_VERTICAL = "console_vertical"
    STREAMING = "streaming"
    CABLE_BOX = "cable_box"
    BLU_RAY = "blu_ray"
    TURNTABLE = "turntable"
    CUSTOM = "custom"


class MediaVentilationTypeConfig(str, Enum):
    """Ventilation type for media sections.

    Defines the ventilation approach for thermal management in
    enclosed media cabinet sections.

    Attributes:
        PASSIVE_REAR: Ventilation slots in rear panel.
        PASSIVE_BOTTOM: Ventilation slots in bottom panel.
        PASSIVE_SLOTS: Side ventilation slots.
        ACTIVE_FAN: Active cooling with fan mount.
        NONE: No ventilation (for non-heat-generating equipment).
    """

    PASSIVE_REAR = "passive_rear"
    PASSIVE_BOTTOM = "passive_bottom"
    PASSIVE_SLOTS = "passive_slots"
    ACTIVE_FAN = "active_fan"
    NONE = "none"


class SoundbarTypeConfig(str, Enum):
    """Soundbar size preset type.

    Defines standard soundbar size presets for shelf configuration.

    Attributes:
        COMPACT: Small soundbar (18-24" width).
        STANDARD: Standard soundbar (32-40" width).
        PREMIUM: Premium soundbar (42-48" width).
        CUSTOM: Custom dimensions specified by user.
    """

    COMPACT = "compact"
    STANDARD = "standard"
    PREMIUM = "premium"
    CUSTOM = "custom"


class SpeakerTypeConfig(str, Enum):
    """Speaker type for alcove configuration.

    Defines the type of speaker to accommodate, which determines
    alcove dimensions and acoustic considerations.

    Attributes:
        CENTER_CHANNEL: Center channel speaker for surround sound.
        BOOKSHELF: Bookshelf speaker (left/right channels).
        SUBWOOFER: Subwoofer with bass port clearance requirements.
    """

    CENTER_CHANNEL = "center_channel"
    BOOKSHELF = "bookshelf"
    SUBWOOFER = "subwoofer"


class GrommetPositionConfig(str, Enum):
    """Grommet position for cable management.

    Defines where cable grommets are placed on equipment shelves.

    Attributes:
        CENTER_REAR: Centered at rear of shelf.
        LEFT_REAR: Left side at rear of shelf.
        RIGHT_REAR: Right side at rear of shelf.
        NONE: No grommet.
    """

    CENTER_REAR = "center_rear"
    LEFT_REAR = "left_rear"
    RIGHT_REAR = "right_rear"
    NONE = "none"


class EntertainmentLayoutTypeConfig(str, Enum):
    """Entertainment center layout type.

    Defines the overall layout configuration for entertainment centers.

    Attributes:
        CONSOLE: Low console under wall-mounted TV.
        WALL_UNIT: Full wall unit surrounding TV.
        FLOATING: Wall-mounted floating shelves.
        TOWER: Vertical tower units flanking TV.
    """

    CONSOLE = "console"
    WALL_UNIT = "wall_unit"
    FLOATING = "floating"
    TOWER = "tower"


class TVMountingConfig(str, Enum):
    """TV mounting type.

    Defines how the TV is mounted relative to the entertainment center.

    Attributes:
        WALL: TV is wall-mounted above/within the unit.
        STAND: TV sits on a stand on top of a cabinet section.
    """

    WALL = "wall"
    STAND = "stand"


# =============================================================================
# Entertainment Center Configuration Models (FRD-19)
# =============================================================================


class EquipmentConfigSchema(BaseModel):
    """Configuration for equipment shelf component.

    Specifies equipment type, dimensions, and grommet placement for
    media equipment shelves.

    Attributes:
        equipment_type: Type of equipment to accommodate.
        custom_dimensions: Custom dimensions for custom equipment type.
        depth: Shelf depth in inches (default: equipment depth + 4").
        vertical_clearance: Vertical clearance above equipment in inches.
        grommet_position: Position for cable grommet.
        grommet_diameter: Grommet diameter in inches.
    """

    model_config = ConfigDict(extra="forbid")

    equipment_type: EquipmentTypeConfig = Field(
        default=EquipmentTypeConfig.RECEIVER,
        description="Type of equipment to accommodate",
    )
    custom_dimensions: dict[str, float] | None = Field(
        default=None,
        description="Custom dimensions: {width, height, depth, generates_heat, clearance}",
    )
    depth: float | None = Field(
        default=None,
        ge=12.0,
        le=30.0,
        description="Shelf depth in inches (default: equipment depth + 4\")",
    )
    vertical_clearance: float | None = Field(
        default=None,
        ge=4.0,
        le=24.0,
        description="Vertical clearance above equipment in inches",
    )
    grommet_position: GrommetPositionConfig = Field(
        default=GrommetPositionConfig.CENTER_REAR,
        description="Position for cable grommet",
    )
    grommet_diameter: float = Field(
        default=2.5,
        ge=1.5,
        le=3.5,
        description="Grommet diameter in inches",
    )


class MediaVentilationConfigSchema(BaseModel):
    """Configuration for ventilated section component.

    Specifies ventilation type and parameters for media cabinet
    thermal management.

    Attributes:
        ventilation_type: Type of ventilation.
        vent_pattern: Pattern for passive ventilation cutouts.
        open_area_percent: Target percentage of open area for airflow.
        fan_size_mm: Fan diameter in mm for active ventilation.
        has_equipment: Whether section contains equipment requiring cooling.
        enclosed: Whether section is enclosed (affects ventilation requirements).
    """

    model_config = ConfigDict(extra="forbid")

    ventilation_type: MediaVentilationTypeConfig = Field(
        default=MediaVentilationTypeConfig.PASSIVE_REAR,
        description="Type of ventilation",
    )
    vent_pattern: VentilationPatternConfig = Field(
        default=VentilationPatternConfig.GRID,
        description="Pattern for passive ventilation cutouts",
    )
    open_area_percent: float = Field(
        default=30.0,
        ge=10.0,
        le=80.0,
        description="Target percentage of open area for airflow",
    )
    fan_size_mm: int = Field(
        default=120,
        ge=80,
        le=140,
        description="Fan diameter in mm for active ventilation",
    )
    has_equipment: bool = Field(
        default=True,
        description="Whether section contains equipment requiring cooling",
    )
    enclosed: bool = Field(
        default=True,
        description="Whether section is enclosed (affects ventilation requirements)",
    )


class SoundbarConfigSchema(BaseModel):
    """Configuration for soundbar shelf component.

    Specifies soundbar type, dimensions, and acoustic clearances.

    Attributes:
        soundbar_type: Soundbar size preset.
        soundbar_width: Soundbar width for custom type.
        soundbar_height: Soundbar height for custom type.
        soundbar_depth: Soundbar depth for custom type.
        dolby_atmos: Whether soundbar has upward-firing Atmos speakers.
        side_clearance: Clearance from side walls for sound projection.
        ceiling_clearance: Clearance above soundbar (important for Atmos).
        include_mount: Include soundbar mounting bracket hardware.
    """

    model_config = ConfigDict(extra="forbid")

    soundbar_type: SoundbarTypeConfig = Field(
        default=SoundbarTypeConfig.STANDARD,
        description="Soundbar size preset",
    )
    soundbar_width: float = Field(
        default=36.0,
        ge=18.0,
        le=72.0,
        description="Soundbar width for custom type",
    )
    soundbar_height: float = Field(
        default=3.0,
        ge=2.0,
        le=6.0,
        description="Soundbar height for custom type",
    )
    soundbar_depth: float = Field(
        default=4.0,
        ge=2.0,
        le=8.0,
        description="Soundbar depth for custom type",
    )
    dolby_atmos: bool = Field(
        default=False,
        description="Whether soundbar has upward-firing Atmos speakers",
    )
    side_clearance: float = Field(
        default=12.0,
        ge=0.0,
        le=24.0,
        description="Clearance from side walls for sound projection",
    )
    ceiling_clearance: float = Field(
        default=36.0,
        ge=12.0,
        le=96.0,
        description="Clearance above soundbar (important for Atmos)",
    )
    include_mount: bool = Field(
        default=False,
        description="Include soundbar mounting bracket hardware",
    )


class SpeakerConfigSchema(BaseModel):
    """Configuration for speaker alcove component.

    Specifies speaker type, dimensions, and acoustic considerations.

    Attributes:
        speaker_type: Speaker type preset.
        speaker_width: Speaker width for custom dimensions.
        speaker_height: Speaker height for custom dimensions.
        speaker_depth: Speaker depth for custom dimensions.
        alcove_height_from_floor: Height of alcove bottom from floor.
        port_clearance: Clearance for subwoofer bass port.
        include_dampening: Include acoustic dampening material hardware.
        include_top: Include top panel for alcove.
    """

    model_config = ConfigDict(extra="forbid")

    speaker_type: SpeakerTypeConfig = Field(
        default=SpeakerTypeConfig.CENTER_CHANNEL,
        description="Speaker type preset",
    )
    speaker_width: float = Field(
        default=24.0,
        ge=4.0,
        le=36.0,
        description="Speaker width for custom dimensions",
    )
    speaker_height: float = Field(
        default=8.0,
        ge=4.0,
        le=24.0,
        description="Speaker height for custom dimensions",
    )
    speaker_depth: float = Field(
        default=12.0,
        ge=4.0,
        le=24.0,
        description="Speaker depth for custom dimensions",
    )
    alcove_height_from_floor: float = Field(
        default=36.0,
        ge=6.0,
        le=72.0,
        description="Height of alcove bottom from floor",
    )
    port_clearance: float = Field(
        default=4.0,
        ge=2.0,
        le=12.0,
        description="Clearance for subwoofer bass port",
    )
    include_dampening: bool = Field(
        default=True,
        description="Include acoustic dampening material hardware",
    )
    include_top: bool = Field(
        default=True,
        description="Include top panel for alcove",
    )


class TVConfigSchema(BaseModel):
    """Configuration for TV integration.

    Specifies TV size, mounting type, and cable management.

    Attributes:
        screen_size: TV screen size in inches (diagonal).
        mounting: TV mounting type (wall or stand).
        center_height: Height of TV center from floor (for optimal viewing).
        cable_grommet: Include cable grommet for TV cables.
    """

    model_config = ConfigDict(extra="forbid")

    screen_size: Literal[50, 55, 65, 75, 85] = Field(
        default=55,
        description="TV screen size in inches (diagonal)",
    )
    mounting: TVMountingConfig = Field(
        default=TVMountingConfig.WALL,
        description="TV mounting type",
    )
    center_height: float = Field(
        default=42.0,
        ge=24.0,
        le=72.0,
        description="Height of TV center from floor (for optimal viewing)",
    )
    cable_grommet: bool = Field(
        default=True,
        description="Include cable grommet for TV cables",
    )


class MediaStorageConfigSchema(BaseModel):
    """Configuration for media storage sections.

    Specifies storage type for DVDs, games, remotes, etc.

    Attributes:
        storage_type: Type of media storage.
        drawer_count: Number of drawers for drawer-based storage.
        include_dividers: Include drawer dividers for organization.
    """

    model_config = ConfigDict(extra="forbid")

    storage_type: Literal["dvd_drawer", "game_cubbies", "controller_drawer", "mixed"] = Field(
        default="mixed",
        description="Type of media storage",
    )
    drawer_count: int = Field(
        default=2,
        ge=1,
        le=6,
        description="Number of drawers for drawer-based storage",
    )
    include_dividers: bool = Field(
        default=True,
        description="Include drawer dividers for organization",
    )


class MediaCableManagementConfigSchema(BaseModel):
    """Configuration for cable management in media centers.

    Specifies cable routing options including grommets and cable chases.

    Attributes:
        vertical_chase: Include vertical cable chase.
        chase_width: Width of cable chase in inches.
        grommets_per_shelf: Number of grommets per equipment shelf.
        grommet_diameter: Default grommet diameter in inches.
    """

    model_config = ConfigDict(extra="forbid")

    vertical_chase: bool = Field(
        default=False,
        description="Include vertical cable chase",
    )
    chase_width: float = Field(
        default=3.0,
        ge=2.0,
        le=6.0,
        description="Width of cable chase in inches",
    )
    grommets_per_shelf: int = Field(
        default=1,
        ge=0,
        le=3,
        description="Number of grommets per equipment shelf",
    )
    grommet_diameter: float = Field(
        default=2.5,
        ge=1.5,
        le=3.5,
        description="Default grommet diameter in inches",
    )


class MediaSectionConfigSchema(BaseModel):
    """Configuration for individual media section.

    Specifies the type of media section (equipment, soundbar, speaker,
    or standard storage) and its specific configuration.

    Attributes:
        section_type: Type of media section.
        equipment: Equipment shelf configuration (when section_type is 'equipment').
        ventilation: Ventilation configuration (for any enclosed section).
        soundbar: Soundbar shelf configuration (when section_type is 'soundbar').
        speaker: Speaker alcove configuration (when section_type is 'speaker').
        storage: Storage section configuration (when section_type is 'storage').
    """

    model_config = ConfigDict(extra="forbid")

    section_type: Literal["equipment", "soundbar", "speaker", "storage", "ventilated"] = Field(
        default="equipment",
        description="Type of media section",
    )
    equipment: EquipmentConfigSchema | None = Field(
        default=None,
        description="Equipment shelf configuration (when section_type is 'equipment')",
    )
    ventilation: MediaVentilationConfigSchema | None = Field(
        default=None,
        description="Ventilation configuration (for any enclosed section)",
    )
    soundbar: SoundbarConfigSchema | None = Field(
        default=None,
        description="Soundbar shelf configuration (when section_type is 'soundbar')",
    )
    speaker: SpeakerConfigSchema | None = Field(
        default=None,
        description="Speaker alcove configuration (when section_type is 'speaker')",
    )
    storage: MediaStorageConfigSchema | None = Field(
        default=None,
        description="Storage section configuration (when section_type is 'storage')",
    )


class EntertainmentCenterConfigSchema(BaseModel):
    """Complete entertainment center configuration.

    Top-level configuration for entertainment centers with TV integration,
    media sections, and cable management.

    Attributes:
        layout_type: Entertainment center layout type.
        tv: TV integration configuration.
        sections: List of media sections.
        cable_management: Cable management configuration.
        flanking_storage: Include flanking storage sections on sides.
        flanking_width: Width of flanking storage sections.
    """

    model_config = ConfigDict(extra="forbid")

    layout_type: EntertainmentLayoutTypeConfig = Field(
        default=EntertainmentLayoutTypeConfig.CONSOLE,
        description="Entertainment center layout type",
    )
    tv: TVConfigSchema = Field(
        default_factory=TVConfigSchema,
        description="TV integration configuration",
    )
    sections: list[MediaSectionConfigSchema] = Field(
        default_factory=list,
        description="List of media sections",
    )
    cable_management: MediaCableManagementConfigSchema = Field(
        default_factory=MediaCableManagementConfigSchema,
        description="Cable management configuration",
    )
    flanking_storage: bool = Field(
        default=True,
        description="Include flanking storage sections on sides",
    )
    flanking_width: float = Field(
        default=18.0,
        ge=12.0,
        le=36.0,
        description="Width of flanking storage sections",
    )


# =============================================================================
# Output Format Configuration Schemas (FRD-16)
# =============================================================================


class DxfOutputConfigSchema(BaseModel):
    """DXF export configuration.

    Controls how DXF (Drawing Exchange Format) files are generated for
    CNC machining and CAD software compatibility.

    Attributes:
        mode: Output mode - "per_panel" creates separate files, "combined" creates one file.
        units: Measurement units in the output file.
        hole_pattern: Pattern name for system holes (e.g., "32mm" for European system).
        hole_diameter: Diameter of system holes in inches.
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["per_panel", "combined"] = "combined"
    units: Literal["inches", "mm"] = "inches"
    hole_pattern: str = "32mm"
    hole_diameter: float = Field(default=0.197, gt=0, description="Hole diameter in inches (5mm default)")


class SvgOutputConfigSchema(BaseModel):
    """SVG export configuration.

    Controls how SVG (Scalable Vector Graphics) files are generated for
    web display, documentation, and 2D visualization.

    Attributes:
        scale: Pixels per inch scaling factor.
        show_dimensions: Whether to display dimension annotations.
        show_labels: Whether to display panel/component labels.
        show_grain: Whether to display grain direction indicators.
        use_panel_colors: Whether to use different colors for panel types.
    """

    model_config = ConfigDict(extra="forbid")

    scale: float = Field(default=10.0, gt=0, description="Pixels per inch")
    show_dimensions: bool = True
    show_labels: bool = True
    show_grain: bool = False
    use_panel_colors: bool = True


class BomOutputConfigSchema(BaseModel):
    """BOM (Bill of Materials) export configuration.

    Controls how the bill of materials is generated, including format
    and optional cost calculations.

    Attributes:
        format: Output format for the BOM.
        include_costs: Whether to include cost calculations (requires pricing data).
        sheet_size: Standard sheet dimensions for material calculations (width, height in inches).
    """

    model_config = ConfigDict(extra="forbid")

    format: Literal["text", "csv", "json"] = "text"
    include_costs: bool = False
    sheet_size: tuple[float, float] = Field(
        default=(48.0, 96.0),
        description="Standard sheet size (width, height) in inches",
    )

    @field_validator("sheet_size")
    @classmethod
    def validate_sheet_size(cls, v: tuple[float, float]) -> tuple[float, float]:
        """Validate that sheet dimensions are positive."""
        if v[0] <= 0 or v[1] <= 0:
            raise ValueError("Sheet dimensions must be positive")
        return v


class AssemblyOutputConfigSchema(BaseModel):
    """Assembly instructions export configuration.

    Controls how assembly instruction documents are generated,
    including safety information and metadata.

    Attributes:
        include_safety_warnings: Whether to include safety warnings and precautions.
        include_timestamps: Whether to include generation timestamps.
    """

    model_config = ConfigDict(extra="forbid")

    include_safety_warnings: bool = True
    include_timestamps: bool = True


class JsonOutputConfigSchema(BaseModel):
    """Enhanced JSON export configuration.

    Controls what data is included in JSON exports for integration
    with other software or data analysis.

    Attributes:
        include_3d_positions: Include 3D position data for each panel.
        include_joinery: Include joinery details (dado, rabbet, etc.).
        include_warnings: Include woodworking warnings and advisories.
        include_bom: Include bill of materials data.
        indent: JSON indentation level (0 for compact).
    """

    model_config = ConfigDict(extra="forbid")

    include_3d_positions: bool = True
    include_joinery: bool = True
    include_warnings: bool = True
    include_bom: bool = True
    indent: int = Field(default=2, ge=0, description="JSON indentation spaces")


class OutputConfig(BaseModel):
    """Configuration for output format and file paths.

    Supports both legacy single-format output and new multi-format output
    with per-format configuration options.

    Attributes:
        format: Legacy single format type (use 'formats' for multi-format output).
        stl_file: Path to STL output file (optional).
        formats: List of output formats to generate (FRD-16).
        output_dir: Directory for output files (FRD-16).
        project_name: Base name for output files (FRD-16).
        dxf: DXF export configuration (FRD-16).
        svg: SVG export configuration (FRD-16).
        bom: BOM export configuration (FRD-16).
        assembly: Assembly instructions configuration (FRD-16).
        json_options: Enhanced JSON export configuration (FRD-16), aliased as "json" in config files.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # Legacy fields
    format: Literal["all", "cutlist", "diagram", "materials", "json", "stl", "cutlayout", "woodworking", "installation"] = "all"
    stl_file: str | None = None

    # New fields for FRD-16
    formats: list[str] = Field(default_factory=list, description="List of output formats to generate")
    output_dir: str | None = Field(default=None, description="Directory for output files")
    project_name: str = Field(default="cabinet", description="Base name for output files")

    # Per-format configuration
    dxf: DxfOutputConfigSchema | None = None
    svg: SvgOutputConfigSchema | None = None
    bom: BomOutputConfigSchema | None = None
    assembly: AssemblyOutputConfigSchema | None = None
    json_options: JsonOutputConfigSchema | None = Field(default=None, alias="json")

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: list[str]) -> list[str]:
        """Validate format names in the formats list."""
        valid_formats = {"stl", "dxf", "json", "bom", "svg", "assembly", "cutlist", "diagram", "materials", "woodworking", "installation"}
        invalid = set(v) - valid_formats - {"all"}
        if invalid:
            raise ValueError(f"Invalid formats: {invalid}. Valid formats: {sorted(valid_formats)}")
        return v


class CabinetConfiguration(BaseModel):
    """Root configuration model for cabinet specifications.

    This is the top-level model that represents a complete cabinet configuration
    file. It includes schema versioning for future compatibility.

    Attributes:
        schema_version: Version string in format "major.minor" (e.g., "1.0")
        cabinet: Cabinet dimensions and structure configuration
        output: Output format configuration
        room: Optional room geometry configuration (v1.1+)
        obstacle_defaults: Optional default clearances by obstacle type
        bin_packing: Optional bin packing configuration (v1.4+)
        woodworking: Optional woodworking intelligence configuration (v1.5+)
        infrastructure: Optional infrastructure integration configuration (v1.6+)
        installation: Optional installation support configuration (v1.8+)

    Example:
        >>> config = CabinetConfiguration(
        ...     schema_version="1.0",
        ...     cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0)
        ... )
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., pattern=r"^\d+\.\d+$")
    cabinet: CabinetConfig
    output: OutputConfig = Field(default_factory=OutputConfig)
    room: RoomConfig | None = Field(default=None, description="Room geometry (optional)")
    obstacle_defaults: ObstacleDefaultsConfig | None = Field(
        default=None, description="Default clearances by obstacle type"
    )
    bin_packing: BinPackingConfigSchema | None = Field(
        default=None, description="Bin packing optimization (optional)"
    )
    woodworking: WoodworkingConfigSchema | None = Field(
        default=None, description="Woodworking intelligence (optional)"
    )
    infrastructure: InfrastructureConfigSchema | None = Field(
        default=None, description="Infrastructure integration (optional)"
    )
    installation: InstallationConfigSchema | None = Field(
        default=None, description="Installation support (optional)"
    )

    @field_validator("schema_version")
    @classmethod
    def validate_supported_version(cls, v: str) -> str:
        """Validate that schema version is supported.

        Validates that the schema version is in the set of SUPPORTED_VERSIONS.
        Also allows newer minor versions within the same major version for
        forward compatibility (e.g., 1.3 is accepted if major version 1 is supported).
        """
        if v in SUPPORTED_VERSIONS:
            return v

        # Check if it's a newer minor version of a supported major version
        major_version = int(v.split(".")[0])
        supported_majors = {int(sv.split(".")[0]) for sv in SUPPORTED_VERSIONS}
        if major_version in supported_majors:
            return v

        raise ValueError(
            f"Unsupported schema version '{v}'. "
            f"Supported versions: {sorted(SUPPORTED_VERSIONS)}"
        )
