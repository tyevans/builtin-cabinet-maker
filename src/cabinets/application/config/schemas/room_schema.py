"""Room geometry configuration schemas.

This module contains room configuration models including RoomConfig,
WallSegmentConfig, obstacle configurations, ceiling configurations,
bay alcove configurations, and corner treatments.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from cabinets.application.config.schemas.base import (
    ClearanceConfig,
    ObstacleTypeConfig,
)


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
        is_egress: If True, this obstacle is an emergency egress point
            that must not be blocked (applies to windows and doors)
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
    is_egress: bool = False  # FRD-21: Egress checking support


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


class WallSegmentConfig(BaseModel):
    """Configuration for a wall segment in a room.

    Wall segments define the geometry of walls where cabinets can be placed.
    Each segment has a length, height, and angle relative to the previous wall.

    Attributes:
        length: Length along the wall in inches
        height: Wall height in inches
        angle: Angle from previous wall (-135 to 135 degrees)
        name: Optional wall identifier for referencing in section configs
        depth: Available depth for cabinets in inches
    """

    model_config = ConfigDict(extra="forbid")

    length: float = Field(..., gt=0, description="Length along the wall in inches")
    height: float = Field(..., gt=0, description="Wall height in inches")
    angle: float = Field(
        default=0.0, description="Angle from previous wall (-135 to 135)"
    )
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

    angle: float = Field(
        ge=0, le=60, description="Slope angle in degrees from horizontal"
    )
    start_height: float = Field(gt=0, description="Height at slope start in inches")
    direction: Literal["left_to_right", "right_to_left", "front_to_back"]
    min_height: float = Field(
        default=24.0, ge=0, description="Minimum usable height in inches"
    )


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
    projection_depth: float = Field(
        gt=0, description="How far skylight projects down in inches"
    )
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


# =============================================================================
# Bay Window Alcove Configurations (FRD-23)
# =============================================================================


class BayWindowConfig(BaseModel):
    """Window configuration for bay wall segments.

    Describes a window within a bay alcove wall segment. Windows affect
    cabinet layout by defining zones where cabinetry must work around
    or underneath the window opening.

    Attributes:
        sill_height: Height of window sill from floor in inches.
        head_height: Height of window head from floor in inches.
        width: Window width in inches, or "full" for full wall width.
        projection_depth: How far the window projects into the room in inches.
    """

    model_config = ConfigDict(extra="forbid")

    sill_height: float = Field(ge=0, description="Height of window sill from floor")
    head_height: float = Field(gt=0, description="Height of window head from floor")
    width: float | Literal["full"] = Field(
        default="full", description="Window width or 'full' for full wall"
    )
    projection_depth: float = Field(
        default=0.0, ge=0, description="Window projection into room"
    )

    @model_validator(mode="after")
    def validate_heights(self) -> "BayWindowConfig":
        """Validate that head height is greater than sill height."""
        if self.head_height <= self.sill_height:
            raise ValueError("head_height must be greater than sill_height")
        return self


class BayWallSegmentConfig(BaseModel):
    """Configuration for a single bay alcove wall segment.

    Describes one wall segment within a bay alcove. Bay alcoves consist
    of multiple angled wall segments that create the distinctive bay
    window shape. Each segment can have its own window and configuration.

    Attributes:
        length: Wall length in inches.
        angle: Angle from previous wall in degrees, or None for auto-calculation.
        window: Optional window configuration for this wall segment.
        name: Optional identifier for the wall segment.
        zone_type: Force zone type ("cabinet", "filler", or "auto" for threshold detection).
        shelf_alignment: Per-wall shelf alignment override.
        top_style: Per-wall top panel style override.
    """

    model_config = ConfigDict(extra="forbid")

    length: float = Field(gt=0, description="Wall length in inches")
    angle: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Angle from previous wall (None=auto)",
    )
    window: BayWindowConfig | None = None
    name: str | None = None

    # Flexibility: override auto-detection
    zone_type: Literal["cabinet", "filler", "auto"] = Field(
        default="auto",
        description="Force zone type regardless of width. 'auto' uses min_cabinet_width threshold",
    )
    shelf_alignment: Literal["rectangular", "wall_parallel"] | None = Field(
        default=None, description="Per-wall shelf alignment override"
    )
    top_style: Literal["flat", "ceiling_follow", "angled"] | None = Field(
        default=None, description="Per-wall top panel style override"
    )


class ApexPointConfig(BaseModel):
    """Apex point configuration for pyramidal ceiling.

    The apex is the highest point of a radial/pyramidal ceiling where
    all ceiling facets converge. This is common in bay window alcoves
    where the ceiling slopes up to a central point.

    Attributes:
        x: X offset from bay center in inches.
        y: Y offset from bay center in inches.
        z: Height from floor to apex in inches.
    """

    model_config = ConfigDict(extra="forbid")

    x: float = Field(default=0.0, description="X offset from bay center")
    y: float = Field(default=0.0, description="Y offset from bay center")
    z: float = Field(gt=0, description="Height from floor to apex")


class BayAlcoveConfigSchema(BaseModel):
    """Configuration for bay window alcove built-ins.

    Bay window alcoves are semi-enclosed spaces created by angled walls
    projecting outward from the main room. This configuration describes
    the geometry of the bay, window placement, ceiling treatment, and
    preferences for cabinet construction within the alcove.

    Supports standard bay types (three-wall, five-wall, box, bow) as well
    as custom configurations with arbitrary wall segments.

    Attributes:
        bay_type: Type of bay configuration (three_wall, five_wall, box_bay, bow, custom).
        walls: List of wall segments defining the bay geometry (3-12 walls).
        opening_width: Width of bay opening from main room in inches.
        bay_depth: Depth from main wall to furthest point in inches.
        arc_angle: Total arc angle for bow window (required when bay_type="bow").
        segment_count: Number of segments for bow window (required when bay_type="bow").
        apex: Apex point configuration for radial ceiling, or "auto" for center.
        edge_height: Height where ceiling meets walls in inches.
        min_cabinet_width: Minimum width for a wall segment to get full cabinet (inches).
        filler_treatment: Treatment for narrow filler zones (panel, trim, none).
        sill_clearance: Clearance below window sill for under-window cabinets (inches).
        head_clearance: Clearance above window head in inches.
        seat_surface_style: How seat surfaces are constructed.
        flank_integration: How flanking cabinets connect.
        top_style: Global top panel style.
        shelf_alignment: Global shelf alignment strategy.
    """

    model_config = ConfigDict(extra="forbid")

    # Bay geometry
    bay_type: Literal["three_wall", "five_wall", "box_bay", "bow", "custom"] = "custom"
    walls: list[BayWallSegmentConfig] = Field(min_length=3, max_length=12)
    opening_width: float | None = Field(
        default=None, gt=0, description="Width of bay opening"
    )
    bay_depth: float | None = Field(
        default=None, gt=0, description="Depth from main wall to furthest point"
    )

    # Bow window presets (when bay_type="bow")
    arc_angle: float | None = Field(
        default=None, ge=30, le=180, description="Total arc angle for bow window"
    )
    segment_count: int | None = Field(
        default=None, ge=3, le=12, description="Number of segments to approximate arc"
    )

    # Ceiling geometry
    apex: ApexPointConfig | Literal["auto"] | None = Field(
        default="auto", description="Apex point or 'auto' for center"
    )
    edge_height: float = Field(
        default=84.0, gt=0, description="Height where ceiling meets walls"
    )

    # Zone detection
    min_cabinet_width: float = Field(default=6.0, ge=3.0, le=24.0)
    filler_treatment: Literal["panel", "trim", "none"] = "panel"
    sill_clearance: float = Field(default=1.0, ge=0)
    head_clearance: float = Field(default=2.0, ge=0)

    # Flexibility options
    seat_surface_style: Literal["continuous", "per_section", "bridged"] = "per_section"
    flank_integration: Literal["separate", "shared_panel", "butted"] = "separate"
    top_style: Literal["flat", "ceiling_follow", "angled"] | None = None
    shelf_alignment: Literal["rectangular", "wall_parallel", "mixed"] = "rectangular"

    @model_validator(mode="after")
    def validate_bow_config(self) -> "BayAlcoveConfigSchema":
        """Validate bow window has required arc_angle and segment_count."""
        if self.bay_type == "bow":
            if self.arc_angle is None:
                raise ValueError("arc_angle required for bow bay_type")
            if self.segment_count is None:
                raise ValueError("segment_count required for bow bay_type")
        return self


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
        bay_alcove: Optional bay window alcove configuration (FRD-23)
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, description="Room identifier")
    walls: list[WallSegmentConfig] = Field(
        ..., min_length=1, description="Wall segments"
    )
    is_closed: bool = Field(
        default=False, description="Whether walls form a closed polygon"
    )
    obstacles: list[ObstacleConfig] = Field(
        default_factory=list, description="Wall obstacles"
    )
    ceiling: CeilingConfig | None = None
    outside_corner: OutsideCornerConfigSchema | None = None
    bay_alcove: BayAlcoveConfigSchema | None = Field(
        default=None, description="Bay window alcove configuration (FRD-23)"
    )

    @field_validator("walls")
    @classmethod
    def validate_first_wall_angle(
        cls, v: list[WallSegmentConfig]
    ) -> list[WallSegmentConfig]:
        """Validate that the first wall has angle=0."""
        if v and v[0].angle != 0:
            raise ValueError("First wall must have angle=0")
        return v
