"""Woodworking and span limits adapter functions.

This module provides conversion functions that transform Pydantic woodworking-related
configuration models into domain-level WoodworkingConfig objects and span limits.
"""

from typing import TYPE_CHECKING

from cabinets.application.config.schemas import (
    BinPackingConfigSchema,
    CabinetConfiguration,
    JoineryConfigSchema,
    JoineryTypeConfig,
)

if TYPE_CHECKING:
    from cabinets.domain.services.woodworking import WoodworkingConfig
    from cabinets.infrastructure.bin_packing import BinPackingConfig


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
        default_shelf_joint=joint_type_map.get(
            joinery.default_shelf_joint, JointType.DADO
        ),
        default_back_joint=joint_type_map.get(
            joinery.default_back_joint, JointType.RABBET
        ),
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


__all__ = [
    "config_to_bin_packing",
    "config_to_hardware_settings",
    "config_to_span_limits",
    "config_to_woodworking",
]
