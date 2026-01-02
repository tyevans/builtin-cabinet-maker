"""Entertainment center configuration schemas.

This module contains entertainment center configuration models including
EntertainmentCenterConfigSchema and related media component schemas for FRD-19.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from cabinets.application.config.schemas.base import (
    EntertainmentLayoutTypeConfig,
    EquipmentTypeConfig,
    GrommetPositionConfig,
    MediaVentilationTypeConfig,
    SoundbarTypeConfig,
    SpeakerTypeConfig,
    TVMountingConfig,
    VentilationPatternConfig,
)


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
        description='Shelf depth in inches (default: equipment depth + 4")',
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

    storage_type: Literal[
        "dvd_drawer", "game_cubbies", "controller_drawer", "mixed"
    ] = Field(
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

    section_type: Literal[
        "equipment", "soundbar", "speaker", "storage", "ventilated"
    ] = Field(
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
