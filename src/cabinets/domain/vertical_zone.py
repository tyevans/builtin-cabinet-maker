"""Vertical zone data model for FRD-22 Countertops and Vertical Zones.

This module defines the data structures for vertical zone configurations,
including zone stacks, individual zones, and preset configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .value_objects import GapPurpose, ZoneMounting, ZoneType


@dataclass(frozen=True)
class VerticalZone:
    """Definition of a single vertical zone.

    Attributes:
        zone_type: Type of zone (base, upper, gap, bench, open)
        height: Height of the zone in inches
        depth: Depth of the zone in inches (0 for gap zones)
        mounting: How the zone is mounted (floor, wall, suspended, on_base)
        sections: Section configurations within the zone
        gap_purpose: Purpose of gap zone (backsplash, mirror, hooks, workspace, display)
        mounting_height: Distance from floor to bottom of zone (for wall-mounted)
    """

    zone_type: ZoneType
    height: float
    depth: float
    mounting: ZoneMounting
    sections: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    gap_purpose: GapPurpose | None = None
    mounting_height: float | None = None

    def __post_init__(self) -> None:
        if self.height <= 0:
            raise ValueError("Zone height must be positive")
        if self.depth < 0:
            raise ValueError("Zone depth cannot be negative")
        if self.depth == 0 and self.zone_type != ZoneType.GAP:
            raise ValueError("Zone depth must be positive for non-gap zones")


@dataclass(frozen=True)
class VerticalZoneStack:
    """Stack of vertical zones from floor to ceiling.

    Attributes:
        zones: Ordered list of zones from bottom to top
        total_width: Total width of the zone stack in inches
        full_height_sides: Whether side panels span all zones
    """

    zones: tuple[VerticalZone, ...]
    total_width: float
    full_height_sides: bool = False

    def __post_init__(self) -> None:
        if not self.zones:
            raise ValueError("Zone stack must have at least one zone")
        if self.total_width <= 0:
            raise ValueError("Total width must be positive")

    @property
    def total_height(self) -> float:
        """Calculate total height of zone stack."""
        return sum(z.height for z in self.zones)

    @property
    def base_zones(self) -> tuple[VerticalZone, ...]:
        """Get floor-mounted zones."""
        return tuple(z for z in self.zones if z.mounting == ZoneMounting.FLOOR)

    @property
    def upper_zones(self) -> tuple[VerticalZone, ...]:
        """Get wall-mounted zones."""
        return tuple(z for z in self.zones if z.mounting == ZoneMounting.WALL)

    @property
    def gap_zones(self) -> tuple[VerticalZone, ...]:
        """Get gap zones."""
        return tuple(z for z in self.zones if z.zone_type == ZoneType.GAP)

    def zone_bottom_height(self, zone_index: int) -> float:
        """Calculate height from floor to bottom of specified zone."""
        if zone_index < 0 or zone_index >= len(self.zones):
            raise IndexError(f"Zone index {zone_index} out of range")
        return sum(self.zones[i].height for i in range(zone_index))


# Zone presets - frozen configurations for common use cases

KITCHEN_PRESET = VerticalZoneStack(
    zones=(
        VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        ),
        # Note: Countertop (1.5") is handled separately by CountertopSurfaceComponent
        VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
            gap_purpose=GapPurpose.BACKSPLASH,
        ),
        VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
            mounting_height=54.0,
        ),
    ),
    total_width=48.0,  # Default, will be overridden by config
)

MUDROOM_PRESET = VerticalZoneStack(
    zones=(
        VerticalZone(
            zone_type=ZoneType.BENCH,
            height=18.0,
            depth=16.0,
            mounting=ZoneMounting.FLOOR,
        ),
        VerticalZone(
            zone_type=ZoneType.GAP,
            height=48.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
            gap_purpose=GapPurpose.HOOKS,
        ),
        VerticalZone(
            zone_type=ZoneType.OPEN,
            height=18.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
            mounting_height=66.0,
        ),
    ),
    total_width=48.0,
    full_height_sides=True,
)

VANITY_PRESET = VerticalZoneStack(
    zones=(
        VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.0,
            depth=21.0,
            mounting=ZoneMounting.FLOOR,
        ),
        # Note: Countertop (1.25") is handled separately
        VerticalZone(
            zone_type=ZoneType.GAP,
            height=24.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
            gap_purpose=GapPurpose.MIRROR,
        ),
        VerticalZone(
            zone_type=ZoneType.UPPER,
            height=12.0,
            depth=6.0,
            mounting=ZoneMounting.WALL,
            mounting_height=60.0,
        ),
    ),
    total_width=36.0,
)

HUTCH_PRESET = VerticalZoneStack(
    zones=(
        VerticalZone(
            zone_type=ZoneType.BASE,
            height=30.0,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        ),
        # Note: Work surface (1") is handled separately
        VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.ON_BASE,
            gap_purpose=GapPurpose.WORKSPACE,
        ),
        VerticalZone(
            zone_type=ZoneType.UPPER,
            height=24.0,
            depth=12.0,
            mounting=ZoneMounting.ON_BASE,
        ),
    ),
    total_width=48.0,
)


def get_preset(preset_name: str, width: float | None = None) -> VerticalZoneStack:
    """Get a zone stack preset by name, optionally with custom width.

    Args:
        preset_name: Name of the preset (kitchen, mudroom, vanity, hutch)
        width: Optional custom width to override the preset default

    Returns:
        VerticalZoneStack configured for the preset

    Raises:
        ValueError: If preset_name is not recognized
    """
    presets = {
        "kitchen": KITCHEN_PRESET,
        "mudroom": MUDROOM_PRESET,
        "vanity": VANITY_PRESET,
        "hutch": HUTCH_PRESET,
    }

    preset = presets.get(preset_name.lower())
    if preset is None:
        raise ValueError(
            f"Unknown preset: {preset_name}. Valid presets: {list(presets.keys())}"
        )

    if width is not None and width != preset.total_width:
        # Create new stack with custom width
        return VerticalZoneStack(
            zones=preset.zones,
            total_width=width,
            full_height_sides=preset.full_height_sides,
        )

    return preset
