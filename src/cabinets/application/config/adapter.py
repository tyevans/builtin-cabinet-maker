"""Adapter to convert CabinetConfiguration to existing DTOs and domain objects.

This module provides conversion functions that transform the new Pydantic-based
CabinetConfiguration into the existing WallInput and LayoutParametersInput DTOs
used by GenerateLayoutCommand, as well as domain-level SectionSpec objects
and Room domain entities.

This adapter layer allows gradual migration while preserving the existing
command infrastructure.
"""

from cabinets.application.config.schema import (
    CabinetConfiguration,
    ClearanceConfig,
    SectionConfig,
)
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.domain.entities import Obstacle, Room, WallSegment
from cabinets.domain.section_resolver import SectionSpec
from cabinets.domain.value_objects import Clearance, DEFAULT_CLEARANCES, ObstacleType


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
        >>> config = load_config(Path("my-cabinet.json"))
        >>> wall_input, params_input = config_to_dtos(config)
        >>> command = GenerateLayoutCommand()
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


def config_to_section_specs(config: CabinetConfiguration) -> list[SectionSpec]:
    """Convert configuration sections to domain SectionSpec objects.

    This function transforms the Pydantic SectionConfig models from the
    configuration schema into domain-level SectionSpec objects that can
    be used with LayoutCalculator.generate_cabinet_from_specs().

    If no sections are specified in the config, returns a single "fill"
    section with 0 shelves (the default behavior).

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of SectionSpec objects ready for use with the domain layer.
        Will always contain at least one section.

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> section_specs = config_to_section_specs(config)
        >>> cabinet = calculator.generate_cabinet_from_specs(wall, params, section_specs)
    """
    sections = config.cabinet.sections

    if not sections:
        # Default: single fill section with no shelves
        return [SectionSpec(width="fill", shelves=0)]

    return [_section_config_to_spec(section) for section in sections]


def _section_config_to_spec(section_config: SectionConfig) -> SectionSpec:
    """Convert a single SectionConfig to a SectionSpec.

    Args:
        section_config: The Pydantic section configuration model

    Returns:
        A domain SectionSpec object
    """
    return SectionSpec(
        width=section_config.width,
        shelves=section_config.shelves,
        wall=section_config.wall,
        height_mode=section_config.height_mode.value if section_config.height_mode else None,
    )


def has_section_specs(config: CabinetConfiguration) -> bool:
    """Check if the configuration has explicit section specifications.

    This is useful for determining whether to use the new specs-based
    cabinet generation or the legacy uniform sections approach.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        True if the config has sections with explicit specifications
        (either fixed widths or varying shelf counts), False otherwise.
    """
    sections = config.cabinet.sections
    if not sections:
        return False

    # If there's only one section with fill width and default shelves,
    # we could use the legacy approach, but for consistency we'll
    # consider any explicit sections list as "having specs"
    return len(sections) > 0


def config_to_room(config: CabinetConfiguration) -> Room | None:
    """Convert room configuration to Room domain entity.

    This function transforms the Pydantic RoomConfig model from the
    configuration schema into a domain-level Room entity that can
    be used for room-aware cabinet layout operations.

    Returns None if no room is configured, maintaining backward
    compatibility with configurations that only specify cabinet
    dimensions without room context.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        A Room domain entity if room configuration exists,
        None if no room is configured.

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> room = config_to_room(config)
        >>> if room:
        ...     positions = room.get_wall_positions()
        ...     for pos in positions:
        ...         print(f"Wall {pos.wall_index}: {pos.start} -> {pos.end}")
    """
    if config.room is None:
        return None

    walls = [
        WallSegment(
            length=wall.length,
            height=wall.height,
            angle=wall.angle,
            name=wall.name,
            depth=wall.depth,
        )
        for wall in config.room.walls
    ]

    return Room(
        name=config.room.name,
        walls=walls,
        is_closed=config.room.is_closed,
    )


def config_to_obstacles(config: CabinetConfiguration) -> list[Obstacle]:
    """Convert config obstacles to domain Obstacle entities.

    This function transforms the Pydantic ObstacleConfig models from the
    configuration schema into domain-level Obstacle entities that can
    be used for obstacle-aware cabinet layout operations.

    Returns an empty list if no room is configured or if the room has
    no obstacles defined.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of Obstacle domain entities ready for use with the domain layer.

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> obstacles = config_to_obstacles(config)
        >>> for obs in obstacles:
        ...     print(f"Obstacle: {obs.obstacle_type.value} on wall {obs.wall_index}")
    """
    if not config.room or not config.room.obstacles:
        return []

    return [
        Obstacle(
            obstacle_type=ObstacleType(obs.type.value),
            wall_index=obs.wall,
            horizontal_offset=obs.horizontal_offset,
            bottom=obs.bottom,
            width=obs.width,
            height=obs.height,
            clearance_override=_clearance_config_to_domain(obs.clearance)
            if obs.clearance
            else None,
            name=obs.name,
        )
        for obs in config.room.obstacles
    ]


def config_to_clearance_defaults(
    config: CabinetConfiguration,
) -> dict[ObstacleType, Clearance]:
    """Convert config obstacle defaults to domain clearance mapping.

    This function merges the system-wide default clearances with any
    custom defaults specified in the configuration. Configuration values
    override the built-in system defaults.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        Dictionary mapping ObstacleType to Clearance values, with configuration
        overrides applied on top of system defaults.

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> defaults = config_to_clearance_defaults(config)
        >>> window_clearance = defaults[ObstacleType.WINDOW]
        >>> print(f"Window clearance: top={window_clearance.top}")
    """
    # Start with a copy of built-in defaults
    defaults = dict(DEFAULT_CLEARANCES)

    if not config.obstacle_defaults:
        return defaults

    # Override with config values
    od = config.obstacle_defaults
    if od.window:
        defaults[ObstacleType.WINDOW] = _clearance_config_to_domain(od.window)
    if od.door:
        defaults[ObstacleType.DOOR] = _clearance_config_to_domain(od.door)
    if od.outlet:
        defaults[ObstacleType.OUTLET] = _clearance_config_to_domain(od.outlet)
    if od.switch:
        defaults[ObstacleType.SWITCH] = _clearance_config_to_domain(od.switch)
    if od.vent:
        defaults[ObstacleType.VENT] = _clearance_config_to_domain(od.vent)
    if od.skylight:
        defaults[ObstacleType.SKYLIGHT] = _clearance_config_to_domain(od.skylight)
    if od.custom:
        defaults[ObstacleType.CUSTOM] = _clearance_config_to_domain(od.custom)

    return defaults


def _clearance_config_to_domain(config: ClearanceConfig) -> Clearance:
    """Convert ClearanceConfig to domain Clearance.

    Args:
        config: A ClearanceConfig Pydantic model

    Returns:
        A domain Clearance value object with the same values
    """
    return Clearance(
        top=config.top,
        bottom=config.bottom,
        left=config.left,
        right=config.right,
    )
