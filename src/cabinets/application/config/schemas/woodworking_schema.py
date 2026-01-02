"""Woodworking intelligence configuration schemas.

This module contains woodworking configuration models including
JoineryConfigSchema, HardwareConfigSchema, SpanLimitsConfigSchema,
WoodworkingConfigSchema, and bin packing configurations for FRD-13/FRD-14.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from cabinets.application.config.schemas.base import (
    JoineryTypeConfig,
    SplittablePanelType,
)


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

    width: float = Field(
        default=48.0, gt=0, le=120, description="Sheet width in inches"
    )
    height: float = Field(
        default=96.0, gt=0, le=120, description="Sheet height in inches"
    )


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
