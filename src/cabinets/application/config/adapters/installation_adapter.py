"""Installation configuration adapter functions.

This module provides conversion functions that transform Pydantic installation-related
configuration models into domain-level installation configuration dictionaries.

Note: As of TD-07, config enums (WallTypeConfig, etc.) are now aliases for domain
enums (WallType, etc.), eliminating the need for enum conversion mappings.
"""

from cabinets.application.config.schemas import (
    CabinetConfiguration,
)


def config_to_installation(
    config: CabinetConfiguration,
) -> dict | None:
    """Convert configuration to installation settings dict.

    This function transforms the Pydantic InstallationConfigSchema from the
    configuration into a dictionary suitable for constructing domain-level
    installation configuration objects.

    Args:
        config: Cabinet configuration with optional installation section.

    Returns:
        Dict of installation settings if configured, None otherwise.

    Example:
        >>> config = load_config(Path("cabinet.json"))
        >>> installation = config_to_installation(config)
        >>> if installation:
        ...     print(f"Wall type: {installation['wall_type']}")
    """
    if config.installation is None:
        return None

    installation = config.installation

    # Since TD-07, config enums are now aliases for domain enums,
    # so no conversion mapping is needed - values can be used directly.
    result: dict = {
        "wall_type": installation.wall_type,
        "wall_thickness": installation.wall_thickness,
        "stud_spacing": installation.stud_spacing,
        "stud_offset": installation.stud_offset,
        "mounting_system": installation.mounting_system,
        "expected_load": installation.expected_load,
        "generate_instructions": installation.generate_instructions,
    }

    # Include cleat configuration if present
    if installation.cleat is not None:
        result["cleat"] = {
            "position_from_top": installation.cleat.position_from_top,
            "width_percentage": installation.cleat.width_percentage,
            "bevel_angle": installation.cleat.bevel_angle,
        }
    else:
        result["cleat"] = None

    return result


__all__ = [
    "config_to_installation",
]
