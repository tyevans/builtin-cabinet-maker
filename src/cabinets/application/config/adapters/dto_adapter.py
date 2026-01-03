"""DTO adapter functions for converting configuration to DTOs.

This module provides conversion functions that transform the Pydantic-based
CabinetConfiguration into the existing WallInput and LayoutParametersInput DTOs
used by GenerateLayoutCommand.
"""

from cabinets.application.config.schemas import (
    CabinetConfiguration,
)
from cabinets.application.dtos import LayoutParametersInput, WallInput


def config_to_dtos(
    config: CabinetConfiguration,
) -> tuple[WallInput, LayoutParametersInput]:
    """Convert a CabinetConfiguration to WallInput and LayoutParametersInput DTOs.

    This function adapts the new configuration schema to the existing DTO
    structures used by GenerateLayoutCommand. It handles the mapping between
    the nested configuration structure and the flat DTO fields.

    Section handling:
        - If sections are specified in config, num_sections is the count
        - shelves_per_section uses the first section's shelf count (for now)
        - Future: domain layer should be extended to handle per-section shelves

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        A tuple of (WallInput, LayoutParametersInput) ready for GenerateLayoutCommand

    Example:
        >>> from cabinets.application.factory import get_factory
        >>> config = load_config(Path("my-cabinet.json"))
        >>> wall_input, params_input = config_to_dtos(config)
        >>> command = get_factory().create_generate_command()
        >>> result = command.execute(wall_input, params_input)
    """
    cabinet = config.cabinet

    # Create WallInput from cabinet dimensions
    wall_input = WallInput(
        width=cabinet.width,
        height=cabinet.height,
        depth=cabinet.depth,
    )

    # Determine number of sections and shelves per section
    num_sections = _get_num_sections(config)
    shelves_per_section = _get_shelves_per_section(config)

    # Get back material thickness (default to material thickness if not specified)
    back_thickness = (
        cabinet.back_material.thickness
        if cabinet.back_material is not None
        else cabinet.material.thickness
    )

    # Create LayoutParametersInput
    params_input = LayoutParametersInput(
        num_sections=num_sections,
        shelves_per_section=shelves_per_section,
        material_thickness=cabinet.material.thickness,
        material_type=cabinet.material.type.value,
        back_thickness=back_thickness,
    )

    return wall_input, params_input


def config_to_zone_configs(
    config: CabinetConfiguration,
) -> dict[str, dict | None]:
    """Extract zone configurations (toe kick, crown molding, light rail, face frame) from config.

    This function extracts the decorative zone configurations from the cabinet
    configuration and returns them in a format suitable for passing to the
    Cabinet entity. Only configurations with enabled=True are extracted.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        A dictionary with zone configuration dicts:
        - base_zone: Toe kick/base zone config (or None if disabled)
        - crown_molding: Crown molding zone config (or None if disabled)
        - light_rail: Light rail zone config (or None if disabled)
        - face_frame: Face frame config (or None if disabled)

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> zones = config_to_zone_configs(config)
        >>> cabinet = Cabinet(..., **zones)
    """
    cabinet = config.cabinet

    result: dict[str, dict | None] = {
        "base_zone": None,
        "crown_molding": None,
        "light_rail": None,
        "face_frame": None,
    }

    # Extract base zone (toe kick) config - only if enabled
    if cabinet.base_zone is not None and cabinet.base_zone.enabled:
        result["base_zone"] = {
            "height": cabinet.base_zone.height,
            "setback": cabinet.base_zone.setback,
            "zone_type": cabinet.base_zone.zone_type,
        }

    # Extract crown molding config - only if enabled
    if cabinet.crown_molding is not None and cabinet.crown_molding.enabled:
        result["crown_molding"] = {
            "height": cabinet.crown_molding.height,
            "setback": cabinet.crown_molding.setback,
            "nailer_width": cabinet.crown_molding.nailer_width,
        }

    # Extract light rail config - only if enabled
    if cabinet.light_rail is not None and cabinet.light_rail.enabled:
        result["light_rail"] = {
            "height": cabinet.light_rail.height,
            "setback": cabinet.light_rail.setback,
        }

    # Extract face frame config - only if enabled
    if cabinet.face_frame is not None and cabinet.face_frame.enabled:
        result["face_frame"] = {
            "stile_width": cabinet.face_frame.stile_width,
            "rail_width": cabinet.face_frame.rail_width,
            "joinery": cabinet.face_frame.joinery.value,
            "material_thickness": cabinet.face_frame.material_thickness,
        }

    return result


def _get_num_sections(config: CabinetConfiguration) -> int:
    """Get the number of sections from configuration.

    Args:
        config: The cabinet configuration

    Returns:
        Number of sections (defaults to 1 if no sections specified)
    """
    sections = config.cabinet.sections
    if not sections:
        return 1
    return len(sections)


def _get_shelves_per_section(config: CabinetConfiguration) -> int:
    """Get the shelves per section from configuration.

    Currently uses the first section's shelf count as the value for all sections.
    This is a simplification until the domain layer supports per-section shelf counts.

    Args:
        config: The cabinet configuration

    Returns:
        Number of shelves per section (defaults to 0 if no sections specified)
    """
    sections = config.cabinet.sections
    if not sections:
        return 0

    # Use first section's shelf count
    # Future enhancement: support per-section shelf counts in domain layer
    return sections[0].shelves


__all__ = [
    "config_to_dtos",
    "config_to_zone_configs",
]
