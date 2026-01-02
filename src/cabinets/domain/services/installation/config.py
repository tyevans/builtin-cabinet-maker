"""Installation configuration dataclass.

This module provides the InstallationConfig dataclass for configuring
cabinet installation parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...value_objects import (
    LoadCategory,
    MountingSystem,
    WallType,
)


@dataclass(frozen=True)
class InstallationConfig:
    """Configuration for cabinet installation.

    Contains all parameters needed to plan cabinet installation,
    including wall construction details, mounting method, and
    expected load category.

    Attributes:
        wall_type: Type of wall construction (drywall, plaster, concrete, etc.).
        wall_thickness: Thickness of wall covering in inches (default 0.5 for drywall).
        stud_spacing: Distance between wall studs in inches (default 16.0 OC).
        stud_offset: Distance from wall start to first stud in inches.
        mounting_system: Method used to mount cabinet to wall.
        expected_load: Expected load category for capacity planning.
        cleat_position_from_top: Distance from cabinet top to cleat center in inches.
        cleat_width_percentage: Cleat width as percentage of cabinet width (0-100).
        cleat_bevel_angle: Bevel angle for French cleat in degrees.
    """

    wall_type: WallType = WallType.DRYWALL
    wall_thickness: float = 0.5  # inches (1/2" drywall standard)
    stud_spacing: float = 16.0  # inches on center
    stud_offset: float = 0.0  # first stud from wall start
    mounting_system: MountingSystem = MountingSystem.DIRECT_TO_STUD
    expected_load: LoadCategory = LoadCategory.MEDIUM
    cleat_position_from_top: float = 4.0  # inches
    cleat_width_percentage: float = 90.0  # percent of cabinet width
    cleat_bevel_angle: float = 45.0  # degrees

    def __post_init__(self) -> None:
        if self.wall_thickness <= 0:
            raise ValueError("Wall thickness must be positive")
        if self.stud_spacing <= 0:
            raise ValueError("Stud spacing must be positive")
        if self.stud_offset < 0:
            raise ValueError("Stud offset must be non-negative")
        if self.cleat_position_from_top < 0:
            raise ValueError("Cleat position from top must be non-negative")
        if not 0 < self.cleat_width_percentage <= 100:
            raise ValueError("Cleat width percentage must be between 0 and 100")
        if not 0 < self.cleat_bevel_angle < 90:
            raise ValueError("Cleat bevel angle must be between 0 and 90 degrees")
