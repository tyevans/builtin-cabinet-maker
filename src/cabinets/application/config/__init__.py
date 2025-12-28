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
    CabinetConfig,
    CabinetConfiguration,
    ClearanceConfig,
    HeightMode,
    MaterialConfig,
    ObstacleConfig,
    ObstacleDefaultsConfig,
    ObstacleTypeConfig,
    OutputConfig,
    RoomConfig,
    SectionConfig,
    WallSegmentConfig,
)
from cabinets.application.config.validator import (
    ValidationError,
    ValidationResult,
    ValidationWarning,
    check_obstacle_advisories,
    validate_config,
)
from cabinets.application.config.merger import merge_config_with_cli
from cabinets.application.config.adapter import (
    config_to_clearance_defaults,
    config_to_dtos,
    config_to_obstacles,
    config_to_room,
    config_to_section_specs,
    has_section_specs,
)

__all__ = [
    # Schema models
    "CabinetConfiguration",
    "CabinetConfig",
    "MaterialConfig",
    "SectionConfig",
    "OutputConfig",
    "RoomConfig",
    "WallSegmentConfig",
    "ObstacleConfig",
    "ObstacleTypeConfig",
    "ClearanceConfig",
    "ObstacleDefaultsConfig",
    "HeightMode",
    # Loader
    "load_config",
    "load_config_from_dict",
    "ConfigError",
    # Validation
    "ValidationResult",
    "ValidationError",
    "ValidationWarning",
    "validate_config",
    "check_obstacle_advisories",
    # Merger
    "merge_config_with_cli",
    # Adapter
    "config_to_dtos",
    "config_to_room",
    "config_to_section_specs",
    "config_to_obstacles",
    "config_to_clearance_defaults",
    "has_section_specs",
]
