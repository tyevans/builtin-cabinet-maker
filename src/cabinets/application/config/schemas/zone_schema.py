"""Vertical zone and zone stack configuration schemas.

This module contains zone stack configuration models including
ZoneStackConfigSchema, VerticalZoneConfigSchema, and countertop
configurations for FRD-22.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from cabinets.application.config.schemas.base import (
    CountertopEdgeConfig,
    GapPurposeConfig,
    MaterialConfig,
    ZoneMountingConfig,
    ZonePresetConfig,
    ZoneTypeConfig,
)
from cabinets.application.config.schemas.cabinet_schema import SectionConfig


class CountertopOverhangSchema(BaseModel):
    """Countertop overhang configuration schema.

    Specifies how much the countertop surface extends beyond
    the base cabinet on each side.

    Attributes:
        front: Front overhang in inches (0.0 to 24.0).
        left: Left side overhang in inches (0.0 to 6.0).
        right: Right side overhang in inches (0.0 to 6.0).
        back: Back overhang in inches (0.0 to 2.0).
    """

    model_config = ConfigDict(extra="forbid")

    front: float = Field(
        default=1.0, ge=0.0, le=24.0, description="Front overhang in inches"
    )
    left: float = Field(
        default=0.0, ge=0.0, le=6.0, description="Left side overhang in inches"
    )
    right: float = Field(
        default=0.0, ge=0.0, le=6.0, description="Right side overhang in inches"
    )
    back: float = Field(
        default=0.0, ge=0.0, le=2.0, description="Back overhang in inches"
    )


class CountertopConfigSchema(BaseModel):
    """Countertop surface configuration schema.

    Defines the configuration for a countertop surface, including
    thickness, overhangs, edge treatment, and material.

    Attributes:
        thickness: Countertop thickness in inches (0.5 to 2.0).
        overhang: Overhang configuration for each side.
        edge_treatment: Type of edge treatment to apply.
        support_brackets: Whether to include support brackets for large overhangs.
        material: Optional material override for the countertop.
    """

    model_config = ConfigDict(extra="forbid")

    thickness: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Countertop thickness in inches"
    )
    overhang: CountertopOverhangSchema = Field(
        default_factory=CountertopOverhangSchema, description="Overhang configuration"
    )
    edge_treatment: CountertopEdgeConfig = Field(
        default=CountertopEdgeConfig.SQUARE, description="Edge treatment type"
    )
    support_brackets: bool = Field(
        default=False, description="Include support brackets for large overhangs"
    )
    material: MaterialConfig | None = Field(
        default=None, description="Optional material override for countertop"
    )


class VerticalZoneConfigSchema(BaseModel):
    """Configuration for a single vertical zone.

    Defines a vertical zone in a zone stack, such as a base cabinet,
    upper cabinet, or gap zone (backsplash, mirror, etc.).

    Attributes:
        zone_type: Type of zone (base, upper, gap, bench, open).
        height: Zone height in inches.
        depth: Zone depth in inches (0 for gap zones).
        mounting: How the zone is mounted (floor, wall, suspended, on_base).
        mounting_height: Height from floor to zone bottom (for wall-mounted zones).
        gap_purpose: Purpose of gap zone (backsplash, mirror, hooks, workspace, display).
        sections: Section configurations within the zone.
    """

    model_config = ConfigDict(extra="forbid")

    zone_type: ZoneTypeConfig = Field(description="Type of zone")
    height: float = Field(gt=0, description="Zone height in inches")
    depth: float = Field(ge=0, description="Zone depth in inches (0 for gap zones)")
    mounting: ZoneMountingConfig = Field(
        default=ZoneMountingConfig.FLOOR, description="How the zone is mounted"
    )
    mounting_height: float | None = Field(
        default=None, ge=0, description="Height from floor to zone bottom"
    )
    gap_purpose: GapPurposeConfig | None = Field(
        default=None, description="Purpose of gap zone"
    )
    sections: list[SectionConfig] = Field(
        default_factory=list, description="Section configurations within zone"
    )


class ZoneStackConfigSchema(BaseModel):
    """Configuration for vertical zone stack.

    Defines a vertical zone stack configuration, which can be either
    a preset (kitchen, mudroom, vanity, hutch) or a custom configuration.

    Attributes:
        preset: Zone preset name (kitchen, mudroom, vanity, hutch, custom).
        zones: Custom zones (required if preset=custom).
        countertop: Countertop configuration (optional).
        full_height_sides: Whether side panels span all zones.
        upper_cabinet_height: Height of upper zone (for presets).
    """

    model_config = ConfigDict(extra="forbid")

    preset: ZonePresetConfig = Field(
        default=ZonePresetConfig.CUSTOM, description="Zone preset name"
    )
    zones: list[VerticalZoneConfigSchema] = Field(
        default_factory=list, description="Custom zones (required if preset=custom)"
    )
    countertop: CountertopConfigSchema | None = Field(
        default=None, description="Countertop configuration"
    )
    full_height_sides: bool = Field(
        default=False, description="Side panels span all zones"
    )
    upper_cabinet_height: float = Field(
        default=30.0, ge=12.0, le=48.0, description="Height of upper zone (for presets)"
    )

    @model_validator(mode="after")
    def validate_preset_zones(self) -> "ZoneStackConfigSchema":
        """Validate that custom preset has zones, and non-custom presets don't require zones."""
        if self.preset == ZonePresetConfig.CUSTOM and not self.zones:
            raise ValueError("Custom zone preset requires 'zones' list to be defined")
        return self
