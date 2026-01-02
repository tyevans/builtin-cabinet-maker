"""Woodworking configuration.

This module provides WoodworkingConfig for customizing woodworking
intelligence service behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from cabinets.domain.value_objects import JointType


@dataclass(frozen=True)
class WoodworkingConfig:
    """Configuration for woodworking intelligence service.

    Allows customization of default joint types and dimension ratios
    for joinery calculations.

    Attributes:
        default_shelf_joint: Default joint type for shelf-to-side connections.
        default_back_joint: Default joint type for back panel-to-case connections.
        dado_depth_ratio: Ratio of material thickness for dado depth (default 1/3).
        rabbet_depth_ratio: Ratio of case material thickness for rabbet depth (default 1/2).
        dowel_edge_offset: Distance from panel edges for first/last dowels in inches.
        dowel_spacing: Spacing between dowels in inches.
        pocket_hole_edge_offset: Distance from panel edges for first/last pocket holes.
        pocket_hole_spacing: Spacing between pocket holes in inches.
    """

    default_shelf_joint: JointType = JointType.DADO
    default_back_joint: JointType = JointType.RABBET
    dado_depth_ratio: float = 1 / 3  # Standard: 1/3 of thickness
    rabbet_depth_ratio: float = 0.5  # Standard: 1/2 of case thickness
    dowel_edge_offset: float = 2.0  # 2" from edges (FR-01.5)
    dowel_spacing: float = 6.0  # 6" spacing (FR-01.5)
    pocket_hole_edge_offset: float = 4.0  # 4" from edges (FR-01.6)
    pocket_hole_spacing: float = 8.0  # 8" spacing (FR-01.6)

    def __post_init__(self) -> None:
        if self.dado_depth_ratio <= 0 or self.dado_depth_ratio > 1:
            raise ValueError("dado_depth_ratio must be between 0 and 1")
        if self.rabbet_depth_ratio <= 0 or self.rabbet_depth_ratio > 1:
            raise ValueError("rabbet_depth_ratio must be between 0 and 1")
        if self.dowel_edge_offset <= 0:
            raise ValueError("dowel_edge_offset must be positive")
        if self.dowel_spacing <= 0:
            raise ValueError("dowel_spacing must be positive")
        if self.pocket_hole_edge_offset <= 0:
            raise ValueError("pocket_hole_edge_offset must be positive")
        if self.pocket_hole_spacing <= 0:
            raise ValueError("pocket_hole_spacing must be positive")
