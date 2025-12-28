"""Pydantic configuration schema models for cabinet specifications.

This module defines the configuration schema for JSON-based cabinet configuration
files. It uses Pydantic v2 for validation and serialization.

The MaterialType enum is reused from the domain layer to ensure consistency
and avoid duplication.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cabinets.domain.value_objects import MaterialType


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
        """Validate that angle is one of the allowed values."""
        if v not in (-90, 0, 90):
            raise ValueError("Angle must be -90, 0, or 90 degrees")
        return v


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
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, description="Room identifier")
    walls: list[WallSegmentConfig] = Field(..., min_length=1, description="Wall segments")
    is_closed: bool = Field(default=False, description="Whether walls form a closed polygon")
    obstacles: list[ObstacleConfig] = Field(default_factory=list, description="Wall obstacles")

    @field_validator("walls")
    @classmethod
    def validate_first_wall_angle(cls, v: list[WallSegmentConfig]) -> list[WallSegmentConfig]:
        """Validate that the first wall has angle=0."""
        if v and v[0].angle != 0:
            raise ValueError("First wall must have angle=0")
        return v


class SectionConfig(BaseModel):
    """Configuration for a cabinet section.

    Attributes:
        width: Section width in inches, or "fill" to auto-calculate remaining space
        shelves: Number of shelves in this section (0 to 20)
        wall: Wall name or index where this section is placed (optional)
        height_mode: How the section uses wall height (full, lower, upper, auto)
    """

    model_config = ConfigDict(extra="forbid")

    width: float | Literal["fill"] = "fill"
    shelves: int = Field(default=0, ge=0, le=20)
    wall: str | int | None = Field(default=None, description="Wall name or index")
    height_mode: HeightMode | None = Field(
        default=None, description="Height mode for the section"
    )

    @field_validator("width")
    @classmethod
    def validate_width(cls, v: float | str) -> float | str:
        """Validate that numeric width is positive."""
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError("width must be positive")
        return v


class CabinetConfig(BaseModel):
    """Configuration for the cabinet dimensions and structure.

    Attributes:
        width: Overall cabinet width in inches (6.0 to 240.0)
        height: Overall cabinet height in inches (6.0 to 120.0)
        depth: Overall cabinet depth in inches (4.0 to 36.0)
        material: Primary material for cabinet construction
        back_material: Material for back panel (optional, defaults to material if not specified)
        sections: List of section configurations (1 to 20 sections)
    """

    model_config = ConfigDict(extra="forbid")

    width: float = Field(..., ge=6.0, le=240.0)
    height: float = Field(..., ge=6.0, le=120.0)
    depth: float = Field(..., ge=4.0, le=36.0)
    material: MaterialConfig = Field(default_factory=MaterialConfig)
    back_material: MaterialConfig | None = None
    sections: list[SectionConfig] = Field(default_factory=list, max_length=20)

    @field_validator("sections")
    @classmethod
    def validate_sections_not_empty_if_provided(
        cls, v: list[SectionConfig]
    ) -> list[SectionConfig]:
        """Ensure sections list has at least 1 section if provided."""
        # Empty list is allowed - it means use default single section
        return v


class OutputConfig(BaseModel):
    """Configuration for output format and file paths.

    Attributes:
        format: Output format type
        stl_file: Path to STL output file (optional)
    """

    model_config = ConfigDict(extra="forbid")

    format: Literal["all", "cutlist", "diagram", "materials", "json", "stl"] = "all"
    stl_file: str | None = None


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

    @field_validator("schema_version")
    @classmethod
    def validate_supported_version(cls, v: str) -> str:
        """Validate that schema version is supported.

        Currently supports version 1.x (major version 1).
        """
        major_version = int(v.split(".")[0])
        if major_version != 1:
            raise ValueError(
                f"Unsupported schema version '{v}'. "
                f"Only version 1.x is supported."
            )
        return v
