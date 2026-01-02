"""Room, geometry, and obstacle adapter functions.

This module provides conversion functions that transform Pydantic room-related
configuration models into domain-level Room, Obstacle, and related entities.

Note: As of TD-07, ObstacleTypeConfig is now an alias for domain ObstacleType,
eliminating the need for enum conversion when constructing Obstacle entities.
"""

from cabinets.application.config.schemas import (
    CabinetConfiguration,
    CeilingSlopeConfig,
    ClearanceConfig,
    OutsideCornerConfigSchema,
    SkylightConfig,
)
from cabinets.domain.entities import Obstacle, Room, WallSegment
from cabinets.domain.value_objects import (
    CeilingSlope,
    Clearance,
    DEFAULT_CLEARANCES,
    ObstacleType,
    OutsideCornerConfig,
    Skylight,
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

    # Since TD-07, ObstacleTypeConfig is an alias for ObstacleType,
    # so obs.type can be used directly without conversion.
    return [
        Obstacle(
            obstacle_type=obs.type,
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


def config_to_outside_corner(
    config: CabinetConfiguration,
) -> OutsideCornerConfig | None:
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


__all__ = [
    "config_to_ceiling_slope",
    "config_to_clearance_defaults",
    "config_to_obstacles",
    "config_to_outside_corner",
    "config_to_room",
    "config_to_skylights",
]
