"""Configuration merging utilities for CLI override support.

This module provides functionality to merge CLI arguments with configuration
file values, following the precedence: CLI args > config values > defaults.

Only non-None CLI arguments override configuration values.
"""

from pathlib import Path
from typing import Any

from cabinets.application.config.schemas import (
    CabinetConfig,
    CabinetConfiguration,
    OutputConfig,
)


def merge_config_with_cli(
    config: CabinetConfiguration,
    *,
    width: float | None = None,
    height: float | None = None,
    depth: float | None = None,
    material_thickness: float | None = None,
    output_format: str | None = None,
    stl_file: str | Path | None = None,
) -> CabinetConfiguration:
    """Merge CLI arguments with configuration values.

    CLI arguments override corresponding config values only when the CLI
    argument is not None. This allows users to specify a base configuration
    file and selectively override specific values from the command line.

    Args:
        config: The base CabinetConfiguration to merge with
        width: Override for cabinet.width (if not None)
        height: Override for cabinet.height (if not None)
        depth: Override for cabinet.depth (if not None)
        material_thickness: Override for cabinet.material.thickness (if not None)
        output_format: Override for output.format (if not None)
        stl_file: Override for output.stl_file (if not None)

    Returns:
        A new CabinetConfiguration with merged values

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> # Override just the width from CLI
        >>> merged = merge_config_with_cli(config, width=60.0)
        >>> merged.cabinet.width
        60.0
    """
    # Build cabinet config with overrides
    cabinet_data = _build_cabinet_data(config, width, height, depth, material_thickness)

    # Build output config with overrides
    output_data = _build_output_data(config, output_format, stl_file)

    # Create new configuration with merged values
    # Preserve room, obstacle_defaults, bin_packing, woodworking, infrastructure,
    # and installation from original config
    return CabinetConfiguration(
        schema_version=config.schema_version,
        cabinet=CabinetConfig.model_validate(cabinet_data),
        output=OutputConfig.model_validate(output_data),
        room=config.room,
        obstacle_defaults=config.obstacle_defaults,
        bin_packing=config.bin_packing,
        woodworking=config.woodworking,
        infrastructure=config.infrastructure,
        installation=config.installation,
    )


def _build_cabinet_data(
    config: CabinetConfiguration,
    width: float | None,
    height: float | None,
    depth: float | None,
    material_thickness: float | None,
) -> dict[str, Any]:
    """Build cabinet configuration data with CLI overrides applied.

    Args:
        config: Base configuration
        width: CLI width override
        height: CLI height override
        depth: CLI depth override
        material_thickness: CLI material thickness override

    Returns:
        Dictionary suitable for CabinetConfig.model_validate()
    """
    cabinet = config.cabinet

    # Start with current cabinet values
    cabinet_data: dict[str, Any] = {
        "width": width if width is not None else cabinet.width,
        "height": height if height is not None else cabinet.height,
        "depth": depth if depth is not None else cabinet.depth,
        "sections": [section.model_dump() for section in cabinet.sections],
    }

    # Preserve rows if present (for multi-row cabinets)
    if cabinet.rows is not None:
        cabinet_data["rows"] = [row.model_dump() for row in cabinet.rows]

    # Handle material configuration
    material_data: dict[str, Any] = {
        "type": cabinet.material.type,
        "thickness": (
            material_thickness
            if material_thickness is not None
            else cabinet.material.thickness
        ),
    }
    cabinet_data["material"] = material_data

    # Handle back material if present
    if cabinet.back_material is not None:
        cabinet_data["back_material"] = cabinet.back_material.model_dump()

    # Preserve decorative zone configurations (FRD-12)
    if cabinet.face_frame is not None:
        cabinet_data["face_frame"] = cabinet.face_frame.model_dump()
    if cabinet.crown_molding is not None:
        cabinet_data["crown_molding"] = cabinet.crown_molding.model_dump()
    if cabinet.base_zone is not None:
        cabinet_data["base_zone"] = cabinet.base_zone.model_dump()
    if cabinet.light_rail is not None:
        cabinet_data["light_rail"] = cabinet.light_rail.model_dump()

    # Preserve zone stack configuration (FRD-22)
    if cabinet.zone_stack is not None:
        cabinet_data["zone_stack"] = cabinet.zone_stack.model_dump()

    # Preserve default_shelves if set
    if cabinet.default_shelves > 0:
        cabinet_data["default_shelves"] = cabinet.default_shelves

    return cabinet_data


def _build_output_data(
    config: CabinetConfiguration,
    output_format: str | None,
    stl_file: str | Path | None,
) -> dict[str, Any]:
    """Build output configuration data with CLI overrides applied.

    Args:
        config: Base configuration
        output_format: CLI format override
        stl_file: CLI STL file path override

    Returns:
        Dictionary suitable for OutputConfig.model_validate()
    """
    output = config.output

    output_data: dict[str, Any] = {
        "format": output_format if output_format is not None else output.format,
    }

    # Handle stl_file - convert Path to string if needed
    if stl_file is not None:
        output_data["stl_file"] = (
            str(stl_file) if isinstance(stl_file, Path) else stl_file
        )
    elif output.stl_file is not None:
        output_data["stl_file"] = output.stl_file

    return output_data
