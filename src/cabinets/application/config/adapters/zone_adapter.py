"""Zone and bay alcove adapter functions.

This module provides conversion functions that transform Pydantic zone-related
configuration models into domain-level zone configuration objects.
"""

from typing import TYPE_CHECKING

from cabinets.application.config.schemas import (
    CabinetConfiguration,
    ZoneStackConfigSchema,
)
from cabinets.domain.value_objects import (
    ApexPoint,
    BayAlcoveConfig,
)

if TYPE_CHECKING:
    from cabinets.domain.services.zone_layout import ZoneLayoutConfig
    from cabinets.domain.value_objects import MaterialSpec


def config_to_zone_layout(
    zone_stack_schema: ZoneStackConfigSchema,
    cabinet_width: float,
    material: "MaterialSpec | None" = None,
) -> "ZoneLayoutConfig":
    """Convert zone stack schema to ZoneLayoutConfig for the service.

    This function transforms the Pydantic ZoneStackConfigSchema from the
    configuration into a domain-level ZoneLayoutConfig that can be used
    with the ZoneLayoutService.

    Args:
        zone_stack_schema: The Pydantic schema for zone stack
        cabinet_width: Cabinet width to use for the zone stack
        material: Optional default material

    Returns:
        ZoneLayoutConfig for use with ZoneLayoutService

    Example:
        >>> from cabinets.application.config import load_config
        >>> from cabinets.domain.services.zone_layout import ZoneLayoutService
        >>>
        >>> config = load_config("kitchen-cabinet.json")
        >>> if config.cabinet.zone_stack:
        ...     zone_config = config_to_zone_layout(
        ...         config.cabinet.zone_stack,
        ...         config.cabinet.width,
        ...     )
        ...     service = ZoneLayoutService()
        ...     result = service.generate(zone_config)
    """
    # Lazy import to avoid circular dependencies
    from cabinets.domain.services.zone_layout import CountertopConfig, ZoneLayoutConfig

    # Convert countertop config
    countertop_config = None
    if zone_stack_schema.countertop:
        ct = zone_stack_schema.countertop
        countertop_config = CountertopConfig(
            thickness=ct.thickness,
            front_overhang=ct.overhang.front,
            left_overhang=ct.overhang.left,
            right_overhang=ct.overhang.right,
            back_overhang=ct.overhang.back,
            edge_treatment=ct.edge_treatment.value,
            support_brackets=ct.support_brackets,
            material=ct.material.model_dump() if ct.material else None,
        )

    # Convert custom zones if present
    custom_zones = None
    if zone_stack_schema.zones:
        custom_zones = []
        for zone in zone_stack_schema.zones:
            zone_dict: dict = {
                "zone_type": zone.zone_type.value,
                "height": zone.height,
                "depth": zone.depth,
                "mounting": zone.mounting.value,
                "sections": [s.model_dump() for s in zone.sections],
            }
            if zone.gap_purpose:
                zone_dict["gap_purpose"] = zone.gap_purpose.value
            if zone.mounting_height is not None:
                zone_dict["mounting_height"] = zone.mounting_height
            custom_zones.append(zone_dict)

    return ZoneLayoutConfig(
        preset=zone_stack_schema.preset.value,
        width=cabinet_width,
        custom_zones=custom_zones,
        countertop=countertop_config,
        full_height_sides=zone_stack_schema.full_height_sides,
        upper_cabinet_height=zone_stack_schema.upper_cabinet_height,
        material=material,
    )


def config_to_bay_alcove(
    config: CabinetConfiguration,
) -> BayAlcoveConfig | None:
    """Convert bay alcove configuration to domain value objects.

    This function transforms the Pydantic BayAlcoveConfigSchema from the
    configuration into domain-level value objects that can be used for
    bay window alcove cabinet layout operations.

    Returns None if no bay alcove is configured, maintaining backward
    compatibility with configurations that don't include bay alcove data.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        A BayAlcoveConfig domain object if bay alcove configuration exists,
        None if no bay alcove is configured.

    Example:
        >>> config = load_config(Path("bay-window.json"))
        >>> bay_alcove = config_to_bay_alcove(config)
        >>> if bay_alcove:
        ...     for wall in bay_alcove.walls:
        ...         print(f"Wall: {wall.length}in at {wall.angle} degrees")
    """
    if config.room is None or config.room.bay_alcove is None:
        return None

    bay_config = config.room.bay_alcove

    # Convert apex point configuration
    apex: ApexPoint | None = None
    if bay_config.apex is not None and bay_config.apex != "auto":
        apex_config = bay_config.apex
        apex = ApexPoint(
            x=apex_config.x,
            y=apex_config.y,
            z=apex_config.z,
        )

    # Convert wall segment configurations
    wall_configs = []
    for wall in bay_config.walls:
        wall_dict: dict = {
            "length": wall.length,
            "angle": wall.angle,
            "name": wall.name,
            "zone_type": wall.zone_type,
            "shelf_alignment": wall.shelf_alignment,
            "top_style": wall.top_style,
        }

        # Convert window if present
        if wall.window is not None:
            wall_dict["window"] = {
                "sill_height": wall.window.sill_height,
                "head_height": wall.window.head_height,
                "width": wall.window.width,
                "projection_depth": wall.window.projection_depth,
            }

        wall_configs.append(wall_dict)

    # Build the domain configuration
    return BayAlcoveConfig(
        bay_type=bay_config.bay_type,
        walls=tuple(wall_configs),
        opening_width=bay_config.opening_width,
        bay_depth=bay_config.bay_depth,
        arc_angle=bay_config.arc_angle,
        segment_count=bay_config.segment_count,
        apex=apex,
        apex_mode="auto" if bay_config.apex == "auto" else "explicit",
        edge_height=bay_config.edge_height,
        min_cabinet_width=bay_config.min_cabinet_width,
        filler_treatment=bay_config.filler_treatment,
        sill_clearance=bay_config.sill_clearance,
        head_clearance=bay_config.head_clearance,
        seat_surface_style=bay_config.seat_surface_style,
        flank_integration=bay_config.flank_integration,
        top_style=bay_config.top_style,
        shelf_alignment=bay_config.shelf_alignment,
    )


__all__ = [
    "config_to_bay_alcove",
    "config_to_zone_layout",
]
