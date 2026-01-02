"""Root configuration schema.

This module contains the root CabinetConfiguration model and CabinetConfig
which represent the top-level configuration structure for cabinet specifications.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from cabinets.application.config.schemas.base import (
    MaterialConfig,
    SUPPORTED_VERSIONS,
)
from cabinets.application.config.schemas.cabinet_schema import (
    BaseZoneConfigSchema,
    CrownMoldingConfigSchema,
    FaceFrameConfigSchema,
    LightRailConfigSchema,
    RowConfig,
    SectionConfig,
)
from cabinets.application.config.schemas.room_schema import (
    ObstacleDefaultsConfig,
    RoomConfig,
)
from cabinets.application.config.schemas.safety_schema import SafetyConfigSchema
from cabinets.application.config.schemas.zone_schema import ZoneStackConfigSchema
from cabinets.application.config.schemas.installation_schema import (
    InstallationConfigSchema,
)
from cabinets.application.config.schemas.woodworking_schema import (
    BinPackingConfigSchema,
    WoodworkingConfigSchema,
)
from cabinets.application.config.schemas.infrastructure_schema import (
    InfrastructureConfigSchema,
)
from cabinets.application.config.schemas.output_schema import OutputConfig


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
        zone_stack: Vertical zone stack configuration (optional, FRD-22)
    """

    model_config = ConfigDict(extra="forbid")

    width: float = Field(..., ge=6.0, le=240.0)
    height: float = Field(..., ge=6.0, le=120.0)
    depth: float = Field(..., ge=4.0, le=36.0)
    material: MaterialConfig = Field(default_factory=MaterialConfig)
    back_material: MaterialConfig | None = None
    sections: list[SectionConfig] = Field(default_factory=list, max_length=20)
    rows: list[RowConfig] | None = Field(
        default=None,
        max_length=10,
        description="Row configurations for multi-row layout",
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

    # Vertical zone stack (FRD-22)
    zone_stack: ZoneStackConfigSchema | None = Field(
        default=None, description="Vertical zone stack configuration (optional, FRD-22)"
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
        safety: Optional safety compliance configuration (v1.10+)

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
    room: RoomConfig | None = Field(
        default=None, description="Room geometry (optional)"
    )
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
    safety: SafetyConfigSchema | None = Field(
        default=None, description="Safety compliance configuration (optional)"
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
