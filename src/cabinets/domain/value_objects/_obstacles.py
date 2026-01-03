"""Obstacle detection and avoidance value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities import Obstacle


class ObstacleType(str, Enum):
    """Types of obstacles that cabinets must avoid.

    Defines physical obstructions and infrastructure elements that
    require clearance or special handling during cabinet placement.

    Attributes:
        WINDOW: Window opening in wall.
        DOOR: Door or door frame.
        OUTLET: Electrical outlet/receptacle.
        SWITCH: Light switch or other wall switch.
        VENT: HVAC vent or register.
        SKYLIGHT: Skylight projection into cabinet space.
        CUSTOM: User-defined obstacle type.
        ELECTRICAL_PANEL: Electrical service panel (requires 36" clearance).
        COOKTOP: Cooking surface (requires 30" vertical clearance).
        HEAT_SOURCE: Heat-generating appliance or element.
        CLOSET_LIGHT: Closet lighting fixture (NEC clearance required).
    """

    # Existing values
    WINDOW = "window"
    DOOR = "door"
    OUTLET = "outlet"
    SWITCH = "switch"
    VENT = "vent"
    SKYLIGHT = "skylight"
    CUSTOM = "custom"

    # New safety-related obstacles (FRD-21)
    ELECTRICAL_PANEL = "electrical_panel"
    COOKTOP = "cooktop"
    HEAT_SOURCE = "heat_source"
    CLOSET_LIGHT = "closet_light"


@dataclass(frozen=True)
class Clearance:
    """Clearance distances around an obstacle.

    Specifies the minimum space that must be kept clear around an obstacle
    in each direction. All values are in inches.

    Attributes:
        top: Clearance above the obstacle.
        bottom: Clearance below the obstacle.
        left: Clearance to the left of the obstacle.
        right: Clearance to the right of the obstacle.
    """

    top: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    right: float = 0.0

    def __post_init__(self) -> None:
        if self.top < 0 or self.bottom < 0 or self.left < 0 or self.right < 0:
            raise ValueError("Clearance values must be non-negative")


@dataclass(frozen=True)
class SectionBounds:
    """2D bounds of a cabinet section on a wall.

    Represents the rectangular area occupied by a cabinet section
    in wall-relative coordinates.

    Attributes:
        left: Horizontal offset from wall start (left edge of section).
        right: Horizontal offset from wall start (right edge of section).
        bottom: Vertical offset from floor (bottom edge of section).
        top: Vertical offset from floor (top edge of section).
    """

    left: float
    right: float
    bottom: float
    top: float

    def __post_init__(self) -> None:
        if self.right <= self.left:
            raise ValueError("right must be greater than left")
        if self.top <= self.bottom:
            raise ValueError("top must be greater than bottom")

    @property
    def width(self) -> float:
        """Width of the section bounds."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Height of the section bounds."""
        return self.top - self.bottom


@dataclass(frozen=True)
class ObstacleZone:
    """Bounding box of obstacle including clearances.

    Represents the total exclusion zone for an obstacle, which includes
    both the obstacle itself and any required clearance around it.

    Attributes:
        left: Left edge of the exclusion zone.
        right: Right edge of the exclusion zone.
        bottom: Bottom edge of the exclusion zone.
        top: Top edge of the exclusion zone.
        obstacle: Reference to the obstacle this zone represents.
    """

    left: float
    right: float
    bottom: float
    top: float
    obstacle: "Obstacle"

    @property
    def width(self) -> float:
        """Width of the obstacle zone."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Height of the obstacle zone."""
        return self.top - self.bottom

    def overlaps(self, other: SectionBounds) -> bool:
        """Check if this zone overlaps with a section.

        Two rectangles overlap if neither is completely to the left,
        right, above, or below the other.

        Args:
            other: The section bounds to check for overlap.

        Returns:
            True if there is any overlap, False otherwise.
        """
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.top <= other.bottom
            or self.bottom >= other.top
        )


@dataclass(frozen=True)
class CollisionResult:
    """Result of collision detection between section and obstacle zone.

    Represents a detected collision between a cabinet section and an
    obstacle zone, including the area of overlap.

    Attributes:
        zone: The obstacle zone that was collided with.
        overlap_area: Square inches of overlap between section and zone.
    """

    zone: ObstacleZone
    overlap_area: float

    def __post_init__(self) -> None:
        if self.overlap_area < 0:
            raise ValueError("overlap_area must be non-negative")


# Default clearances for each obstacle type
DEFAULT_CLEARANCES: dict[ObstacleType, Clearance] = {
    # Existing obstacle clearances
    ObstacleType.WINDOW: Clearance(top=2.0, bottom=2.0, left=2.0, right=2.0),
    ObstacleType.DOOR: Clearance(top=0.0, bottom=0.0, left=2.0, right=2.0),
    ObstacleType.OUTLET: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.SWITCH: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.VENT: Clearance(top=4.0, bottom=4.0, left=4.0, right=4.0),
    ObstacleType.SKYLIGHT: Clearance(top=2.0, bottom=2.0, left=2.0, right=2.0),
    ObstacleType.CUSTOM: Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0),
    # New safety-related clearances (FRD-21)
    # Note: Electrical panel 36" frontal clearance is checked separately by SafetyService
    ObstacleType.ELECTRICAL_PANEL: Clearance(
        top=0.0, bottom=0.0, left=15.0, right=15.0
    ),
    # Cooktop 30" top clearance per range hood/microwave clearance requirements
    ObstacleType.COOKTOP: Clearance(top=30.0, bottom=0.0, left=0.0, right=0.0),
    ObstacleType.HEAT_SOURCE: Clearance(top=30.0, bottom=0.0, left=15.0, right=15.0),
    # Closet light 12" bottom clearance per NEC 410.16 for incandescent fixtures
    ObstacleType.CLOSET_LIGHT: Clearance(top=0.0, bottom=12.0, left=6.0, right=6.0),
}
