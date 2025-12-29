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
    ConfigError,
    load_config,
    load_config_from_dict,
)
from cabinets.application.config.schema import (
    ArchTopConfigSchema,
    ArchTypeConfig,
    AssemblyOutputConfigSchema,
    BaseZoneConfigSchema,
    BinPackingConfigSchema,
    BomOutputConfigSchema,
    CabinetConfig,
    CabinetConfiguration,
    CableChannelConfigSchema,
    CableManagementTypeConfig,
    CeilingConfig,
    CeilingSlopeConfig,
    ClearanceConfig,
    ConduitDirectionConfig,
    CrownMoldingConfigSchema,
    DxfOutputConfigSchema,
    EdgeProfileConfigSchema,
    EdgeProfileTypeConfig,
    EntertainmentCenterConfigSchema,
    EntertainmentLayoutTypeConfig,
    EquipmentConfigSchema,
    EquipmentTypeConfig,
    FaceFrameConfigSchema,
    GrommetConfigSchema,
    GrommetPositionConfig,
    HardwareConfigSchema,
    HeightMode,
    InfrastructureConfigSchema,
    JoineryConfigSchema,
    JoineryTypeConfig,
    JsonOutputConfigSchema,
    LightingConfigSchema,
    LightingLocationConfig,
    LightingTypeConfig,
    LightRailConfigSchema,
    MaterialConfig,
    MediaCableManagementConfigSchema,
    MediaSectionConfigSchema,
    MediaStorageConfigSchema,
    MediaVentilationConfigSchema,
    MediaVentilationTypeConfig,
    ObstacleConfig,
    ObstacleDefaultsConfig,
    ObstacleTypeConfig,
    OutletConfigSchema,
    OutletTypeConfig,
    OutsideCornerConfigSchema,
    OutputConfig,
    PositionConfigSchema,
    RoomConfig,
    RowConfig,
    ScallopConfigSchema,
    SectionConfig,
    SectionRowConfig,
    SectionTypeConfig,
    SheetSizeConfigSchema,
    SkylightConfig,
    SoundbarConfigSchema,
    SoundbarTypeConfig,
    SpanLimitsConfigSchema,
    SpeakerConfigSchema,
    SpeakerTypeConfig,
    SUPPORTED_VERSIONS,
    SvgOutputConfigSchema,
    TVConfigSchema,
    TVMountingConfig,
    VentilationConfigSchema,
    VentilationPatternConfig,
    WallSegmentConfig,
    WireRouteConfigSchema,
    WoodworkingConfigSchema,
)
from cabinets.application.config.validator import (
    ValidationError,
    ValidationResult,
    ValidationWarning,
    check_infrastructure_advisories,
    check_obstacle_advisories,
    validate_config,
)
from cabinets.application.config.merger import merge_config_with_cli
from cabinets.application.config.adapter import (
    config_to_all_section_specs,
    config_to_bin_packing,
    config_to_ceiling_slope,
    config_to_clearance_defaults,
    config_to_dtos,
    config_to_hardware_settings,
    config_to_installation,
    config_to_obstacles,
    config_to_outside_corner,
    config_to_room,
    config_to_row_specs,
    config_to_section_specs,
    config_to_skylights,
    config_to_span_limits,
    config_to_woodworking,
    config_to_zone_configs,
    has_row_specs,
    has_section_specs,
)

__all__ = [
    # Schema models
    "CabinetConfiguration",
    "CabinetConfig",
    "CeilingConfig",
    "CeilingSlopeConfig",
    "MaterialConfig",
    "OutsideCornerConfigSchema",
    "SectionConfig",
    "SectionRowConfig",
    "SectionTypeConfig",
    "SkylightConfig",
    "OutputConfig",
    "RoomConfig",
    "RowConfig",
    "WallSegmentConfig",
    "ObstacleConfig",
    "ObstacleTypeConfig",
    "ClearanceConfig",
    "ObstacleDefaultsConfig",
    "HeightMode",
    "SUPPORTED_VERSIONS",
    # Decorative element schemas (FRD-12)
    "ArchTopConfigSchema",
    "ArchTypeConfig",
    "BaseZoneConfigSchema",
    "CrownMoldingConfigSchema",
    "EdgeProfileConfigSchema",
    "EdgeProfileTypeConfig",
    "FaceFrameConfigSchema",
    "JoineryTypeConfig",
    "LightRailConfigSchema",
    "ScallopConfigSchema",
    # Bin packing schemas (FRD-13)
    "BinPackingConfigSchema",
    "SheetSizeConfigSchema",
    # Woodworking intelligence schemas (FRD-14)
    "HardwareConfigSchema",
    "JoineryConfigSchema",
    "SpanLimitsConfigSchema",
    "WoodworkingConfigSchema",
    # Infrastructure integration schemas (FRD-15)
    "CableChannelConfigSchema",
    "CableManagementTypeConfig",
    "ConduitDirectionConfig",
    "GrommetConfigSchema",
    "InfrastructureConfigSchema",
    "LightingConfigSchema",
    "LightingLocationConfig",
    "LightingTypeConfig",
    "OutletConfigSchema",
    "OutletTypeConfig",
    "PositionConfigSchema",
    "VentilationConfigSchema",
    "VentilationPatternConfig",
    "WireRouteConfigSchema",
    # Output format schemas (FRD-16)
    "AssemblyOutputConfigSchema",
    "BomOutputConfigSchema",
    "DxfOutputConfigSchema",
    "JsonOutputConfigSchema",
    "SvgOutputConfigSchema",
    # Entertainment center schemas (FRD-19)
    "EntertainmentCenterConfigSchema",
    "EntertainmentLayoutTypeConfig",
    "EquipmentConfigSchema",
    "EquipmentTypeConfig",
    "GrommetPositionConfig",
    "MediaCableManagementConfigSchema",
    "MediaSectionConfigSchema",
    "MediaStorageConfigSchema",
    "MediaVentilationConfigSchema",
    "MediaVentilationTypeConfig",
    "SoundbarConfigSchema",
    "SoundbarTypeConfig",
    "SpeakerConfigSchema",
    "SpeakerTypeConfig",
    "TVConfigSchema",
    "TVMountingConfig",
    # Loader
    "load_config",
    "load_config_from_dict",
    "ConfigError",
    # Validation
    "ValidationResult",
    "ValidationError",
    "ValidationWarning",
    "validate_config",
    "check_infrastructure_advisories",
    "check_obstacle_advisories",
    # Merger
    "merge_config_with_cli",
    # Adapter
    "config_to_all_section_specs",
    "config_to_bin_packing",
    "config_to_ceiling_slope",
    "config_to_dtos",
    "config_to_hardware_settings",
    "config_to_installation",
    "config_to_obstacles",
    "config_to_clearance_defaults",
    "config_to_outside_corner",
    "config_to_room",
    "config_to_row_specs",
    "config_to_section_specs",
    "config_to_skylights",
    "config_to_span_limits",
    "config_to_woodworking",
    "config_to_zone_configs",
    "has_row_specs",
    "has_section_specs",
]
