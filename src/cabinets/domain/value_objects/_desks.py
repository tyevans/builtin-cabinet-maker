"""Desk configuration value objects (FRD-18)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeskType(str, Enum):
    """Types of desk configurations.

    Defines the different desk layout options that can be generated.

    Attributes:
        SINGLE: Standard single-surface desk.
        L_SHAPED: Two perpendicular desk surfaces forming an L.
        CORNER: Corner desk with diagonal or 90-degree connection.
        STANDING: Standing-height desk (38-48").
    """

    SINGLE = "single"
    L_SHAPED = "l_shaped"
    CORNER = "corner"
    STANDING = "standing"


class EdgeTreatment(str, Enum):
    """Desktop edge treatment types.

    Defines the different edge finishing options for desktop surfaces.

    Attributes:
        SQUARE: Standard square edge (default).
        BULLNOSE: Rounded/bullnose edge profile.
        WATERFALL: Edge continues down as vertical front panel.
        EASED: Slightly rounded/softened edge.
    """

    SQUARE = "square"
    BULLNOSE = "bullnose"
    WATERFALL = "waterfall"
    EASED = "eased"


class PedestalType(str, Enum):
    """Types of desk pedestals.

    Defines the different pedestal configurations that support desk surfaces.

    Attributes:
        FILE: File drawer pedestal with pencil drawer above file drawer.
        STORAGE: Multiple storage drawers pedestal.
        OPEN: Open shelving pedestal without drawers.
    """

    FILE = "file"
    STORAGE = "storage"
    OPEN = "open"


@dataclass(frozen=True)
class DeskDimensions:
    """Ergonomic desk dimension constants.

    Provides standard ergonomic measurements for desk components.
    All values are in inches.

    Attributes:
        standard_desk_height: Standard seated desk height (29-30").
        standing_desk_min_height: Minimum standing desk height (38").
        standing_desk_max_height: Maximum standing desk height (48").
        min_knee_clearance_height: Minimum knee clearance height (24").
        min_knee_clearance_width: Minimum knee clearance width (20").
        min_knee_clearance_depth: Minimum knee clearance depth (15").
        keyboard_tray_height: Height for keyboard tray below desktop (3").
        keyboard_tray_depth: Standard keyboard tray depth (10").
    """

    standard_desk_height: float = 29.5
    standing_desk_min_height: float = 38.0
    standing_desk_max_height: float = 48.0
    min_knee_clearance_height: float = 24.0
    min_knee_clearance_width: float = 20.0
    min_knee_clearance_depth: float = 15.0
    keyboard_tray_height: float = 3.0
    keyboard_tray_depth: float = 10.0

    def __post_init__(self) -> None:
        if self.standard_desk_height <= 0:
            raise ValueError("Standard desk height must be positive")
        if self.standing_desk_min_height <= 0:
            raise ValueError("Standing desk min height must be positive")
        if self.standing_desk_max_height <= self.standing_desk_min_height:
            raise ValueError("Standing desk max height must be greater than min height")
        if self.min_knee_clearance_height <= 0:
            raise ValueError("Minimum knee clearance height must be positive")
        if self.min_knee_clearance_width <= 0:
            raise ValueError("Minimum knee clearance width must be positive")
        if self.min_knee_clearance_depth <= 0:
            raise ValueError("Minimum knee clearance depth must be positive")
        if self.keyboard_tray_height <= 0:
            raise ValueError("Keyboard tray height must be positive")
        if self.keyboard_tray_depth <= 0:
            raise ValueError("Keyboard tray depth must be positive")
