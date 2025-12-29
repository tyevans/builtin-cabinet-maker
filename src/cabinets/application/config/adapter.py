"""Adapter to convert CabinetConfiguration to existing DTOs and domain objects.

This module provides conversion functions that transform the new Pydantic-based
CabinetConfiguration into the existing WallInput and LayoutParametersInput DTOs
used by GenerateLayoutCommand, as well as domain-level SectionSpec objects
and Room domain entities.

This adapter layer allows gradual migration while preserving the existing
command infrastructure.
"""

from cabinets.application.config.schema import (
    BinPackingConfigSchema,
    CabinetConfiguration,
    CeilingConfig,
    CeilingSlopeConfig,
    ClearanceConfig,
    InstallationConfigSchema,
    JoineryConfigSchema,
    JoineryTypeConfig,
    LoadCategoryConfig,
    MountingSystemConfig,
    OutsideCornerConfigSchema,
    RowConfig,
    SectionConfig,
    SectionRowConfig,
    SectionTypeConfig,
    SkylightConfig,
    WallTypeConfig,
)
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.domain.entities import Obstacle, Room, WallSegment
from cabinets.domain.section_resolver import RowSpec, SectionRowSpec, SectionSpec
from cabinets.domain.value_objects import (
    CeilingSlope,
    Clearance,
    DEFAULT_CLEARANCES,
    LoadCategory,
    MountingSystem,
    ObstacleType,
    OutsideCornerConfig,
    SectionType,
    Skylight,
    WallType,
)


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


def config_to_zone_configs(
    config: CabinetConfiguration,
) -> dict[str, dict | None]:
    """Extract zone configurations (toe kick, crown molding, light rail) from config.

    This function extracts the decorative zone configurations from the cabinet
    configuration and returns them in a format suitable for passing to the
    Cabinet entity.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        A dictionary with zone configuration dicts:
        - base_zone: Toe kick/base zone config (or None)
        - crown_molding: Crown molding zone config (or None)
        - light_rail: Light rail zone config (or None)

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
    }

    # Extract base zone (toe kick) config
    if cabinet.base_zone is not None:
        result["base_zone"] = {
            "height": cabinet.base_zone.height,
            "setback": cabinet.base_zone.setback,
            "zone_type": cabinet.base_zone.zone_type,
        }

    # Extract crown molding config
    if cabinet.crown_molding is not None:
        result["crown_molding"] = {
            "height": cabinet.crown_molding.height,
            "setback": cabinet.crown_molding.setback,
            "nailer_width": cabinet.crown_molding.nailer_width,
        }

    # Extract light rail config
    if cabinet.light_rail is not None:
        result["light_rail"] = {
            "height": cabinet.light_rail.height,
            "setback": cabinet.light_rail.setback,
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


def _section_row_config_to_spec(row_config: SectionRowConfig) -> SectionRowSpec:
    """Convert a single SectionRowConfig to a SectionRowSpec.

    Args:
        row_config: The Pydantic section row configuration model

    Returns:
        A domain SectionRowSpec object
    """
    section_type = _section_type_config_to_domain(row_config.section_type)

    return SectionRowSpec(
        height=row_config.height,
        section_type=section_type,
        shelves=row_config.shelves,
        component_config=row_config.component_config,
        min_height=row_config.min_height,
        max_height=row_config.max_height,
    )


def _section_config_to_spec(section_config: SectionConfig) -> SectionSpec:
    """Convert a single SectionConfig to a SectionSpec.

    Args:
        section_config: The Pydantic section configuration model

    Returns:
        A domain SectionSpec object
    """
    # Map SectionTypeConfig to domain SectionType
    section_type = _section_type_config_to_domain(section_config.section_type)

    # Convert section rows if present
    row_specs: tuple[SectionRowSpec, ...] | None = None
    if section_config.rows:
        row_specs = tuple(
            _section_row_config_to_spec(row) for row in section_config.rows
        )

    return SectionSpec(
        width=section_config.width,
        shelves=section_config.shelves,
        wall=section_config.wall,
        height_mode=section_config.height_mode.value if section_config.height_mode else None,
        section_type=section_type,
        min_width=section_config.min_width,
        max_width=section_config.max_width,
        depth=section_config.depth,
        component_config=section_config.component_config,
        row_specs=row_specs,
    )


def _section_type_config_to_domain(config_type: SectionTypeConfig) -> SectionType:
    """Convert SectionTypeConfig to domain SectionType.

    Args:
        config_type: The configuration section type enum

    Returns:
        The corresponding domain SectionType enum value
    """
    # Map using string values since both enums use the same string values
    return SectionType(config_type.value)


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


def config_to_all_section_specs(config: CabinetConfiguration) -> list[SectionSpec]:
    """Extract all section specs from config, whether in flat sections or rows.

    This function is useful for room layouts where sections need to be
    extracted from either the flat sections list or from within rows,
    preserving wall assignments.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of all SectionSpec objects from the configuration.
        Returns sections from rows if rows are defined, otherwise from sections.
    """
    # If rows are defined, extract sections from each row
    if config.cabinet.rows:
        all_sections: list[SectionSpec] = []
        for row in config.cabinet.rows:
            for section in row.sections:
                all_sections.append(_section_config_to_spec(section))
        return all_sections

    # Otherwise use flat sections
    return config_to_section_specs(config)


def has_row_specs(config: CabinetConfiguration) -> bool:
    """Check if the configuration uses multi-row layout.

    This determines whether to use the row-based cabinet generation
    which supports vertically stacked sections.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        True if the config has rows defined, False otherwise.
    """
    return config.cabinet.rows is not None and len(config.cabinet.rows) > 0


def config_to_row_specs(config: CabinetConfiguration) -> list[RowSpec]:
    """Convert configuration rows to domain RowSpec objects.

    This function transforms the Pydantic RowConfig models from the
    configuration schema into domain-level RowSpec objects that can
    be used with LayoutCalculator for multi-row cabinet generation.

    Each row contains one or more sections that are arranged horizontally
    within that row. Rows are stacked vertically from bottom to top.

    Args:
        config: A validated CabinetConfiguration instance with rows defined

    Returns:
        List of RowSpec objects ready for use with the domain layer.
        Will always contain at least one row if rows are defined.

    Raises:
        ValueError: If config does not have rows defined

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> if has_row_specs(config):
        ...     row_specs = config_to_row_specs(config)
        ...     cabinet = calculator.generate_cabinet_from_row_specs(wall, params, row_specs)
    """
    if not config.cabinet.rows:
        raise ValueError("Configuration does not have rows defined. Use config_to_section_specs() instead.")

    return [_row_config_to_spec(row) for row in config.cabinet.rows]


def _row_config_to_spec(row_config: RowConfig) -> RowSpec:
    """Convert a single RowConfig to a RowSpec.

    Args:
        row_config: The Pydantic row configuration model

    Returns:
        A domain RowSpec object
    """
    section_specs = tuple(_section_config_to_spec(section) for section in row_config.sections)

    return RowSpec(
        height=row_config.height,
        section_specs=section_specs,
        min_height=row_config.min_height,
        max_height=row_config.max_height,
    )


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


def _convert_ceiling_slope(config: CeilingSlopeConfig) -> CeilingSlope:
    """Convert CeilingSlopeConfig to domain CeilingSlope.

    Args:
        config: A CeilingSlopeConfig Pydantic model

    Returns:
        A domain CeilingSlope value object with the same values
    """
    return CeilingSlope(
        angle=config.angle,
        start_height=config.start_height,
        direction=config.direction,
        min_height=config.min_height,
    )


def _convert_skylight(config: SkylightConfig) -> Skylight:
    """Convert SkylightConfig to domain Skylight.

    Args:
        config: A SkylightConfig Pydantic model

    Returns:
        A domain Skylight value object with the same values
    """
    return Skylight(
        x_position=config.x_position,
        width=config.width,
        projection_depth=config.projection_depth,
        projection_angle=config.projection_angle,
    )


def _convert_outside_corner(config: OutsideCornerConfigSchema) -> OutsideCornerConfig:
    """Convert OutsideCornerConfigSchema to domain OutsideCornerConfig.

    Args:
        config: An OutsideCornerConfigSchema Pydantic model

    Returns:
        A domain OutsideCornerConfig value object with the same values
    """
    return OutsideCornerConfig(
        treatment=config.treatment,
        filler_width=config.filler_width,
        face_angle=config.face_angle,
    )


def config_to_ceiling_slope(config: CabinetConfiguration) -> CeilingSlope | None:
    """Convert config ceiling slope to domain CeilingSlope.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        A CeilingSlope domain value object if ceiling slope is configured,
        None otherwise.
    """
    if not config.room or not config.room.ceiling or not config.room.ceiling.slope:
        return None

    return _convert_ceiling_slope(config.room.ceiling.slope)


def config_to_skylights(config: CabinetConfiguration) -> list[Skylight]:
    """Convert config skylights to domain Skylight list.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of Skylight domain value objects. Empty if no skylights configured.
    """
    if not config.room or not config.room.ceiling:
        return []

    return [_convert_skylight(s) for s in config.room.ceiling.skylights]


def config_to_outside_corner(config: CabinetConfiguration) -> OutsideCornerConfig | None:
    """Convert config outside corner to domain OutsideCornerConfig.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        An OutsideCornerConfig domain value object if configured,
        None otherwise.
    """
    if not config.room or not config.room.outside_corner:
        return None

    return _convert_outside_corner(config.room.outside_corner)


def config_to_bin_packing(
    config: BinPackingConfigSchema | None,
) -> "BinPackingConfig":
    """Convert Pydantic bin packing config to domain dataclass.

    Args:
        config: Pydantic bin packing configuration, or None.

    Returns:
        BinPackingConfig domain dataclass.
        Returns default config (enabled=True) if input is None.
    """
    # Lazy import to avoid circular dependencies
    from cabinets.infrastructure.bin_packing import BinPackingConfig, SheetConfig

    if config is None:
        return BinPackingConfig()

    sheet_size = SheetConfig(
        width=config.sheet_size.width,
        height=config.sheet_size.height,
        edge_allowance=config.edge_allowance,
    )

    return BinPackingConfig(
        enabled=config.enabled,
        sheet_size=sheet_size,
        kerf=config.kerf,
        min_offcut_size=config.min_offcut_size,
        allow_panel_splitting=config.allow_panel_splitting,
        splittable_types=tuple(t.value for t in config.splittable_types),
        split_overlap=config.split_overlap,
    )


def config_to_woodworking(
    config: CabinetConfiguration,
) -> "WoodworkingConfig | None":
    """Convert configuration to WoodworkingConfig domain object.

    Args:
        config: Cabinet configuration with optional woodworking section.

    Returns:
        WoodworkingConfig if woodworking is configured, None otherwise.
    """
    # Lazy import to avoid circular dependencies
    from cabinets.domain.services.woodworking import WoodworkingConfig
    from cabinets.domain.value_objects import JointType

    if config.woodworking is None:
        return None

    woodworking = config.woodworking
    joinery = woodworking.joinery or JoineryConfigSchema()

    # Map JoineryTypeConfig to JointType
    joint_type_map = {
        JoineryTypeConfig.DADO: JointType.DADO,
        JoineryTypeConfig.RABBET: JointType.RABBET,
        JoineryTypeConfig.POCKET_SCREW: JointType.POCKET_SCREW,
        JoineryTypeConfig.DOWEL: JointType.DOWEL,
        JoineryTypeConfig.BISCUIT: JointType.BISCUIT,
        JoineryTypeConfig.BUTT: JointType.BUTT,
        JoineryTypeConfig.MORTISE_TENON: JointType.DOWEL,  # Map to closest equivalent
    }

    return WoodworkingConfig(
        default_shelf_joint=joint_type_map.get(joinery.default_shelf_joint, JointType.DADO),
        default_back_joint=joint_type_map.get(joinery.default_back_joint, JointType.RABBET),
        dado_depth_ratio=joinery.dado_depth_ratio,
        rabbet_depth_ratio=joinery.rabbet_depth_ratio,
        dowel_edge_offset=joinery.dowel_edge_offset,
        dowel_spacing=joinery.dowel_spacing,
        pocket_hole_edge_offset=joinery.pocket_hole_edge_offset,
        pocket_hole_spacing=joinery.pocket_hole_spacing,
    )


def config_to_span_limits(
    config: CabinetConfiguration,
) -> dict[tuple, float] | None:
    """Convert configuration to span limits dict.

    Args:
        config: Cabinet configuration with optional woodworking section.

    Returns:
        Dict of span limits if configured, None to use defaults.
    """
    if config.woodworking is None or config.woodworking.span_limits is None:
        return None

    from cabinets.domain.value_objects import MaterialType

    limits = config.woodworking.span_limits
    return {
        (MaterialType.PLYWOOD, 0.75): limits.plywood_3_4,
        (MaterialType.MDF, 0.75): limits.mdf_3_4,
        (MaterialType.PARTICLE_BOARD, 0.75): limits.particle_board_3_4,
        (MaterialType.SOLID_WOOD, 1.0): limits.solid_wood_1,
    }


def config_to_hardware_settings(
    config: CabinetConfiguration,
) -> dict | None:
    """Convert configuration to hardware settings dict.

    Args:
        config: Cabinet configuration with optional woodworking section.

    Returns:
        Dict of hardware settings if configured, None to use defaults.
    """
    if config.woodworking is None or config.woodworking.hardware is None:
        return None

    hardware = config.woodworking.hardware
    return {
        "add_overage": hardware.add_overage,
        "overage_percent": hardware.overage_percent,
        "case_screw_spacing": hardware.case_screw_spacing,
        "back_panel_screw_spacing": hardware.back_panel_screw_spacing,
    }


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

    # Map config enums to domain enums
    wall_type_map = {
        WallTypeConfig.DRYWALL: WallType.DRYWALL,
        WallTypeConfig.PLASTER: WallType.PLASTER,
        WallTypeConfig.CONCRETE: WallType.CONCRETE,
        WallTypeConfig.CMU: WallType.CMU,
        WallTypeConfig.BRICK: WallType.BRICK,
    }

    mounting_system_map = {
        MountingSystemConfig.DIRECT_TO_STUD: MountingSystem.DIRECT_TO_STUD,
        MountingSystemConfig.FRENCH_CLEAT: MountingSystem.FRENCH_CLEAT,
        MountingSystemConfig.HANGING_RAIL: MountingSystem.HANGING_RAIL,
        MountingSystemConfig.TOGGLE_BOLT: MountingSystem.TOGGLE_BOLT,
    }

    load_category_map = {
        LoadCategoryConfig.LIGHT: LoadCategory.LIGHT,
        LoadCategoryConfig.MEDIUM: LoadCategory.MEDIUM,
        LoadCategoryConfig.HEAVY: LoadCategory.HEAVY,
    }

    result: dict = {
        "wall_type": wall_type_map[installation.wall_type],
        "wall_thickness": installation.wall_thickness,
        "stud_spacing": installation.stud_spacing,
        "stud_offset": installation.stud_offset,
        "mounting_system": mounting_system_map[installation.mounting_system],
        "expected_load": load_category_map[installation.expected_load],
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
