"""Built-in desk configuration schemas.

This module contains desk configuration models including
DeskSectionConfigSchema and related desk component schemas for FRD-18.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from cabinets.application.config.schemas.base import (
    DeskMountingConfig,
    DeskTypeConfig,
    EdgeTreatmentConfig,
    PedestalTypeConfig,
)


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
                    f'Standing desk height {self.surface.desk_height}" '
                    'must be at least 38"'
                )
        return self
