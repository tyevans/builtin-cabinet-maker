"""Configuration schema models for cabinet specifications.

This package provides all Pydantic schema models for JSON-based cabinet
configuration files. All models are re-exported here for backward compatibility.

The schemas are organized into the following modules:
- base.py: Enums and shared base models
- cabinet_schema.py: Cabinet and section configurations
- room_schema.py: Room geometry configurations
- safety_schema.py: Safety and accessibility configurations
- zone_schema.py: Vertical zone and zone stack configurations
- installation_schema.py: Installation support configurations
- woodworking_schema.py: Woodworking and bin packing configurations
- infrastructure_schema.py: Infrastructure integration configurations
- desk_schema.py: Built-in desk configurations
- entertainment_schema.py: Entertainment center configurations
- output_schema.py: Output format configurations
- root.py: Root configuration model
"""

# Base enums and shared models
from cabinets.application.config.schemas.base import (
    # Version constants
    SUPPORTED_VERSIONS as SUPPORTED_VERSIONS,
    # Obstacle and section enums
    ObstacleTypeConfig as ObstacleTypeConfig,
    HeightMode as HeightMode,
    SectionTypeConfig as SectionTypeConfig,
    # Decorative enums
    ArchTypeConfig as ArchTypeConfig,
    JoineryTypeConfig as JoineryTypeConfig,
    EdgeProfileTypeConfig as EdgeProfileTypeConfig,
    # Infrastructure enums
    LightingTypeConfig as LightingTypeConfig,
    LightingLocationConfig as LightingLocationConfig,
    OutletTypeConfig as OutletTypeConfig,
    CableManagementTypeConfig as CableManagementTypeConfig,
    VentilationPatternConfig as VentilationPatternConfig,
    ConduitDirectionConfig as ConduitDirectionConfig,
    # Installation enums
    WallTypeConfig as WallTypeConfig,
    MountingSystemConfig as MountingSystemConfig,
    LoadCategoryConfig as LoadCategoryConfig,
    # Zone enums
    ZoneTypeConfig as ZoneTypeConfig,
    ZoneMountingConfig as ZoneMountingConfig,
    GapPurposeConfig as GapPurposeConfig,
    ZonePresetConfig as ZonePresetConfig,
    CountertopEdgeConfig as CountertopEdgeConfig,
    # Desk enums
    DeskTypeConfig as DeskTypeConfig,
    EdgeTreatmentConfig as EdgeTreatmentConfig,
    PedestalTypeConfig as PedestalTypeConfig,
    DeskMountingConfig as DeskMountingConfig,
    # Entertainment enums
    EquipmentTypeConfig as EquipmentTypeConfig,
    MediaVentilationTypeConfig as MediaVentilationTypeConfig,
    SoundbarTypeConfig as SoundbarTypeConfig,
    SpeakerTypeConfig as SpeakerTypeConfig,
    GrommetPositionConfig as GrommetPositionConfig,
    EntertainmentLayoutTypeConfig as EntertainmentLayoutTypeConfig,
    TVMountingConfig as TVMountingConfig,
    # Bin packing enums
    SplittablePanelType as SplittablePanelType,
    # Shared models
    ClearanceConfig as ClearanceConfig,
    MaterialConfig as MaterialConfig,
)

# Cabinet and section schemas
from cabinets.application.config.schemas.cabinet_schema import (
    # Decorative schemas
    FaceFrameConfigSchema as FaceFrameConfigSchema,
    CrownMoldingConfigSchema as CrownMoldingConfigSchema,
    BaseZoneConfigSchema as BaseZoneConfigSchema,
    LightRailConfigSchema as LightRailConfigSchema,
    ArchTopConfigSchema as ArchTopConfigSchema,
    EdgeProfileConfigSchema as EdgeProfileConfigSchema,
    ScallopConfigSchema as ScallopConfigSchema,
    # Section schemas
    SectionRowConfig as SectionRowConfig,
    SectionConfig as SectionConfig,
    RowConfig as RowConfig,
)

# Room geometry schemas
from cabinets.application.config.schemas.room_schema import (
    ObstacleConfig as ObstacleConfig,
    ObstacleDefaultsConfig as ObstacleDefaultsConfig,
    WallSegmentConfig as WallSegmentConfig,
    CeilingSlopeConfig as CeilingSlopeConfig,
    SkylightConfig as SkylightConfig,
    CeilingConfig as CeilingConfig,
    OutsideCornerConfigSchema as OutsideCornerConfigSchema,
    # Bay window alcove
    BayWindowConfig as BayWindowConfig,
    BayWallSegmentConfig as BayWallSegmentConfig,
    ApexPointConfig as ApexPointConfig,
    BayAlcoveConfigSchema as BayAlcoveConfigSchema,
    RoomConfig as RoomConfig,
)

# Safety schemas
from cabinets.application.config.schemas.safety_schema import (
    AccessibilityConfigSchema as AccessibilityConfigSchema,
    SafetyConfigSchema as SafetyConfigSchema,
)

# Zone schemas
from cabinets.application.config.schemas.zone_schema import (
    CountertopOverhangSchema as CountertopOverhangSchema,
    CountertopConfigSchema as CountertopConfigSchema,
    VerticalZoneConfigSchema as VerticalZoneConfigSchema,
    ZoneStackConfigSchema as ZoneStackConfigSchema,
)

# Installation schemas
from cabinets.application.config.schemas.installation_schema import (
    CleatConfigSchema as CleatConfigSchema,
    InstallationConfigSchema as InstallationConfigSchema,
)

# Woodworking schemas
from cabinets.application.config.schemas.woodworking_schema import (
    SheetSizeConfigSchema as SheetSizeConfigSchema,
    BinPackingConfigSchema as BinPackingConfigSchema,
    JoineryConfigSchema as JoineryConfigSchema,
    SpanLimitsConfigSchema as SpanLimitsConfigSchema,
    HardwareConfigSchema as HardwareConfigSchema,
    WoodworkingConfigSchema as WoodworkingConfigSchema,
)

# Infrastructure schemas
from cabinets.application.config.schemas.infrastructure_schema import (
    PositionConfigSchema as PositionConfigSchema,
    LightingConfigSchema as LightingConfigSchema,
    OutletConfigSchema as OutletConfigSchema,
    GrommetConfigSchema as GrommetConfigSchema,
    CableChannelConfigSchema as CableChannelConfigSchema,
    VentilationConfigSchema as VentilationConfigSchema,
    WireRouteConfigSchema as WireRouteConfigSchema,
    InfrastructureConfigSchema as InfrastructureConfigSchema,
)

# Desk schemas
from cabinets.application.config.schemas.desk_schema import (
    DeskGrommetConfigSchema as DeskGrommetConfigSchema,
    DeskSurfaceConfigSchema as DeskSurfaceConfigSchema,
    DeskPedestalConfigSchema as DeskPedestalConfigSchema,
    KeyboardTrayConfigSchema as KeyboardTrayConfigSchema,
    HutchConfigSchema as HutchConfigSchema,
    MonitorShelfConfigSchema as MonitorShelfConfigSchema,
    DeskSectionConfigSchema as DeskSectionConfigSchema,
)

# Entertainment schemas
from cabinets.application.config.schemas.entertainment_schema import (
    EquipmentConfigSchema as EquipmentConfigSchema,
    MediaVentilationConfigSchema as MediaVentilationConfigSchema,
    SoundbarConfigSchema as SoundbarConfigSchema,
    SpeakerConfigSchema as SpeakerConfigSchema,
    TVConfigSchema as TVConfigSchema,
    MediaStorageConfigSchema as MediaStorageConfigSchema,
    MediaCableManagementConfigSchema as MediaCableManagementConfigSchema,
    MediaSectionConfigSchema as MediaSectionConfigSchema,
    EntertainmentCenterConfigSchema as EntertainmentCenterConfigSchema,
)

# Output schemas
from cabinets.application.config.schemas.output_schema import (
    DxfOutputConfigSchema as DxfOutputConfigSchema,
    SvgOutputConfigSchema as SvgOutputConfigSchema,
    BomOutputConfigSchema as BomOutputConfigSchema,
    AssemblyOutputConfigSchema as AssemblyOutputConfigSchema,
    JsonOutputConfigSchema as JsonOutputConfigSchema,
    OutputConfig as OutputConfig,
)

# Root configuration
from cabinets.application.config.schemas.root import (
    CabinetConfig as CabinetConfig,
    CabinetConfiguration as CabinetConfiguration,
)

# All imported names are automatically available for direct import.
# No __all__ needed since star imports are not used.
