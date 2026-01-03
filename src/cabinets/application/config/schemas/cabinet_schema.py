"""Cabinet and section configuration schemas.

This module contains the core cabinet configuration models including
CabinetConfig, SectionConfig, and related section/row configuration schemas.
"""

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from cabinets.application.config.schemas.base import (
    ArchTypeConfig,
    EdgeProfileTypeConfig,
    HeightMode,
    JoineryTypeConfig,
    SectionTypeConfig,
)


# =============================================================================
# Decorative Element Schemas (FRD-12)
# =============================================================================


class FaceFrameConfigSchema(BaseModel):
    """Configuration for face frame construction.

    Face frames consist of vertical stiles and horizontal rails
    that create an opening for doors or drawers.

    Attributes:
        enabled: Whether face frame is enabled (for frontend toggle support).
        stile_width: Width of vertical stiles in inches.
        rail_width: Width of horizontal rails in inches.
        joinery: Type of joint for stile/rail connections.
        material_thickness: Thickness of frame material in inches.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Whether face frame is enabled")
    stile_width: float = Field(default=1.5, gt=0, le=6.0)
    rail_width: float = Field(default=1.5, gt=0, le=6.0)
    joinery: JoineryTypeConfig = JoineryTypeConfig.POCKET_SCREW
    material_thickness: float = Field(default=0.75, ge=0.5, le=1.5)


class CrownMoldingConfigSchema(BaseModel):
    """Configuration for crown molding zone.

    Defines the zone at cabinet top for crown molding installation.

    Attributes:
        enabled: Whether crown molding is enabled (for frontend toggle support).
        height: Zone height for molding in inches.
        setback: Top panel setback distance in inches.
        nailer_width: Width of nailer strip in inches.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Whether crown molding is enabled")
    height: float = Field(default=3.0, gt=0, le=12.0)
    setback: float = Field(default=0.75, gt=0, le=3.0)
    nailer_width: float = Field(default=2.0, gt=0, le=6.0)


class BaseZoneConfigSchema(BaseModel):
    """Configuration for base/toe kick zone.

    Defines the zone at cabinet bottom for toe kick or base molding.

    Attributes:
        enabled: Whether base zone is enabled (for frontend toggle support).
        height: Zone height in inches.
        setback: Toe kick depth/recess in inches.
        zone_type: Type of base treatment.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Whether base zone is enabled")
    height: float = Field(default=3.5, ge=3.0, le=6.0)
    setback: float = Field(default=3.0, ge=0, le=6.0)
    zone_type: Literal["toe_kick", "base_molding"] = "toe_kick"


class LightRailConfigSchema(BaseModel):
    """Configuration for light rail zone.

    Defines the zone under wall cabinets for lighting installation.

    Attributes:
        enabled: Whether light rail is enabled (for frontend toggle support).
        height: Zone height in inches.
        setback: Light rail setback in inches.
        generate_strip: Whether to generate a light rail strip piece.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Whether light rail is enabled")
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
    edges: (
        list[Literal["top", "bottom", "left", "right", "front"]] | Literal["auto"]
    ) = "auto"


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
