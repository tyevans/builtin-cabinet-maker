"""Infrastructure integration configuration schemas.

This module contains infrastructure configuration models including
lighting, electrical outlets, cable management, ventilation, and
wire routing for FRD-15.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from cabinets.application.config.schemas.base import (
    ConduitDirectionConfig,
    LightingLocationConfig,
    LightingTypeConfig,
    OutletTypeConfig,
    VentilationPatternConfig,
)


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
    location: LightingLocationConfig = Field(..., description="Installation location")
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
    width: float = Field(..., gt=0, description="Ventilation area width in inches")
    height: float = Field(..., gt=0, description="Ventilation area height in inches")
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
