"""Configuration schema and loading system for cabinet specifications.

This package provides JSON-based configuration loading and validation
for cabinet specifications. It includes Pydantic models for schema
validation, a configuration loader with comprehensive error handling,
and woodworking advisory checks.

Public API:
    - CabinetConfiguration: Root configuration model
    - MaterialConfig: Material specification model
    - SectionConfig: Section configuration model
    - CabinetConfig: Cabinet dimensions and structure model
    - OutputConfig: Output format configuration model
    - RoomConfig: Room geometry configuration model
    - WallSegmentConfig: Wall segment configuration model
    - ObstacleConfig: Obstacle configuration model
    - ObstacleTypeConfig: Obstacle type enum for configuration
    - ClearanceConfig: Clearance configuration model
    - ObstacleDefaultsConfig: Default clearances by obstacle type
    - HeightMode: Height mode enum for cabinet sections
    - load_config: Load configuration from a JSON file
    - load_config_from_dict: Load configuration from a dictionary
    - ConfigError: Exception for configuration errors
    - ValidationResult: Container for validation results
    - ValidationError: Blocking validation error
    - ValidationWarning: Non-blocking validation warning
    - validate_config: Perform full configuration validation
    - config_to_obstacles: Convert config obstacles to domain entities
    - config_to_clearance_defaults: Convert config defaults to domain mapping

Example:
    >>> from pathlib import Path
    >>> from cabinets.application.config import load_config, ConfigError
    >>>
    >>> try:
    ...     config = load_config(Path("my-cabinet.json"))
    ...     print(f"Cabinet dimensions: {config.cabinet.width}x{config.cabinet.height}")
    ... except ConfigError as e:
    ...     print(f"Error: {e}")
"""

from cabinets.application.config.loader import (
    ConfigError as ConfigError,
    load_config as load_config,
    load_config_from_dict as load_config_from_dict,
)
from cabinets.application.config.schemas import (
    AccessibilityConfigSchema as AccessibilityConfigSchema,
    ArchTopConfigSchema as ArchTopConfigSchema,
    ArchTypeConfig as ArchTypeConfig,
    AssemblyOutputConfigSchema as AssemblyOutputConfigSchema,
    BaseZoneConfigSchema as BaseZoneConfigSchema,
    BinPackingConfigSchema as BinPackingConfigSchema,
    BomOutputConfigSchema as BomOutputConfigSchema,
    CabinetConfig as CabinetConfig,
    CabinetConfiguration as CabinetConfiguration,
    CableChannelConfigSchema as CableChannelConfigSchema,
    CableManagementTypeConfig as CableManagementTypeConfig,
    CeilingConfig as CeilingConfig,
    CeilingSlopeConfig as CeilingSlopeConfig,
    ClearanceConfig as ClearanceConfig,
    ConduitDirectionConfig as ConduitDirectionConfig,
    CrownMoldingConfigSchema as CrownMoldingConfigSchema,
    DxfOutputConfigSchema as DxfOutputConfigSchema,
    EdgeProfileConfigSchema as EdgeProfileConfigSchema,
    EdgeProfileTypeConfig as EdgeProfileTypeConfig,
    EntertainmentCenterConfigSchema as EntertainmentCenterConfigSchema,
    EntertainmentLayoutTypeConfig as EntertainmentLayoutTypeConfig,
    EquipmentConfigSchema as EquipmentConfigSchema,
    EquipmentTypeConfig as EquipmentTypeConfig,
    FaceFrameConfigSchema as FaceFrameConfigSchema,
    GrommetConfigSchema as GrommetConfigSchema,
    GrommetPositionConfig as GrommetPositionConfig,
    HardwareConfigSchema as HardwareConfigSchema,
    HeightMode as HeightMode,
    InfrastructureConfigSchema as InfrastructureConfigSchema,
    JoineryConfigSchema as JoineryConfigSchema,
    JoineryTypeConfig as JoineryTypeConfig,
    JsonOutputConfigSchema as JsonOutputConfigSchema,
    LightingConfigSchema as LightingConfigSchema,
    LightingLocationConfig as LightingLocationConfig,
    LightingTypeConfig as LightingTypeConfig,
    LightRailConfigSchema as LightRailConfigSchema,
    MaterialConfig as MaterialConfig,
    MediaCableManagementConfigSchema as MediaCableManagementConfigSchema,
    MediaSectionConfigSchema as MediaSectionConfigSchema,
    MediaStorageConfigSchema as MediaStorageConfigSchema,
    MediaVentilationConfigSchema as MediaVentilationConfigSchema,
    MediaVentilationTypeConfig as MediaVentilationTypeConfig,
    ObstacleConfig as ObstacleConfig,
    ObstacleDefaultsConfig as ObstacleDefaultsConfig,
    ObstacleTypeConfig as ObstacleTypeConfig,
    OutletConfigSchema as OutletConfigSchema,
    OutletTypeConfig as OutletTypeConfig,
    OutsideCornerConfigSchema as OutsideCornerConfigSchema,
    OutputConfig as OutputConfig,
    PositionConfigSchema as PositionConfigSchema,
    RoomConfig as RoomConfig,
    RowConfig as RowConfig,
    SafetyConfigSchema as SafetyConfigSchema,
    ScallopConfigSchema as ScallopConfigSchema,
    SectionConfig as SectionConfig,
    SectionRowConfig as SectionRowConfig,
    SectionTypeConfig as SectionTypeConfig,
    SheetSizeConfigSchema as SheetSizeConfigSchema,
    SkylightConfig as SkylightConfig,
    SoundbarConfigSchema as SoundbarConfigSchema,
    SoundbarTypeConfig as SoundbarTypeConfig,
    SpanLimitsConfigSchema as SpanLimitsConfigSchema,
    SpeakerConfigSchema as SpeakerConfigSchema,
    SpeakerTypeConfig as SpeakerTypeConfig,
    SUPPORTED_VERSIONS as SUPPORTED_VERSIONS,
    SvgOutputConfigSchema as SvgOutputConfigSchema,
    TVConfigSchema as TVConfigSchema,
    TVMountingConfig as TVMountingConfig,
    VentilationConfigSchema as VentilationConfigSchema,
    VentilationPatternConfig as VentilationPatternConfig,
    WallSegmentConfig as WallSegmentConfig,
    WireRouteConfigSchema as WireRouteConfigSchema,
    WoodworkingConfigSchema as WoodworkingConfigSchema,
    # FRD-22: Countertops and Vertical Zones
    CountertopConfigSchema as CountertopConfigSchema,
    CountertopEdgeConfig as CountertopEdgeConfig,
    CountertopOverhangSchema as CountertopOverhangSchema,
    GapPurposeConfig as GapPurposeConfig,
    VerticalZoneConfigSchema as VerticalZoneConfigSchema,
    ZoneMountingConfig as ZoneMountingConfig,
    ZonePresetConfig as ZonePresetConfig,
    ZoneStackConfigSchema as ZoneStackConfigSchema,
    ZoneTypeConfig as ZoneTypeConfig,
    # FRD-23: Bay Window Alcove
    ApexPointConfig as ApexPointConfig,
    BayAlcoveConfigSchema as BayAlcoveConfigSchema,
    BayWallSegmentConfig as BayWallSegmentConfig,
    BayWindowConfig as BayWindowConfig,
    # FRD-17: Installation
    CleatConfigSchema as CleatConfigSchema,
    InstallationConfigSchema as InstallationConfigSchema,
    LoadCategoryConfig as LoadCategoryConfig,
    MountingSystemConfig as MountingSystemConfig,
    WallTypeConfig as WallTypeConfig,
    # FRD-18: Desk
    DeskGrommetConfigSchema as DeskGrommetConfigSchema,
    DeskMountingConfig as DeskMountingConfig,
    DeskPedestalConfigSchema as DeskPedestalConfigSchema,
    DeskSectionConfigSchema as DeskSectionConfigSchema,
    DeskSurfaceConfigSchema as DeskSurfaceConfigSchema,
    DeskTypeConfig as DeskTypeConfig,
    EdgeTreatmentConfig as EdgeTreatmentConfig,
    HutchConfigSchema as HutchConfigSchema,
    KeyboardTrayConfigSchema as KeyboardTrayConfigSchema,
    MonitorShelfConfigSchema as MonitorShelfConfigSchema,
    PedestalTypeConfig as PedestalTypeConfig,
    # FRD-13: Bin Packing
    SplittablePanelType as SplittablePanelType,
)
from cabinets.application.config.validator import (
    ValidationError as ValidationError,
    ValidationResult as ValidationResult,
    ValidationWarning as ValidationWarning,
    check_infrastructure_advisories as check_infrastructure_advisories,
    check_obstacle_advisories as check_obstacle_advisories,
    validate_config as validate_config,
)
from cabinets.application.config.merger import (
    merge_config_with_cli as merge_config_with_cli,
)
from cabinets.application.config.adapters import (
    BayAlcoveConfig as BayAlcoveConfig,
    config_to_all_section_specs as config_to_all_section_specs,
    config_to_bay_alcove as config_to_bay_alcove,
    config_to_bin_packing as config_to_bin_packing,
    config_to_ceiling_slope as config_to_ceiling_slope,
    config_to_clearance_defaults as config_to_clearance_defaults,
    config_to_dtos as config_to_dtos,
    config_to_hardware_settings as config_to_hardware_settings,
    config_to_installation as config_to_installation,
    config_to_obstacles as config_to_obstacles,
    config_to_outside_corner as config_to_outside_corner,
    config_to_room as config_to_room,
    config_to_row_specs as config_to_row_specs,
    config_to_safety as config_to_safety,
    config_to_section_specs as config_to_section_specs,
    config_to_skylights as config_to_skylights,
    config_to_span_limits as config_to_span_limits,
    config_to_woodworking as config_to_woodworking,
    config_to_zone_configs as config_to_zone_configs,
    config_to_zone_layout as config_to_zone_layout,
    has_row_specs as has_row_specs,
    has_section_specs as has_section_specs,
)

# All imported names are automatically available for direct import.
# No __all__ needed since star imports are not used.
