"""Installation support configuration schemas.

This module contains installation configuration models including
InstallationConfigSchema and CleatConfigSchema for FRD-17.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from cabinets.application.config.schemas.base import (
    LoadCategoryConfig,
    MountingSystemConfig,
    WallTypeConfig,
)


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
