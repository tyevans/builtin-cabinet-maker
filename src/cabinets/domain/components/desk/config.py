"""Configuration value objects for desk components (FRD-18)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal


class CornerConnectionType(str, Enum):
    """Types of corner connections for L-shaped desks.

    Defines how two perpendicular desk surfaces connect at the corner.

    Attributes:
        BUTT: 90-degree butt joint connection (surfaces meet at right angle).
        DIAGONAL: 45-degree mitered connection with diagonal face panel.
    """

    BUTT = "butt"
    DIAGONAL = "diagonal"


@dataclass(frozen=True)
class GrommetSpec:
    """Specification for cable grommet cutout.

    Represents the position and size of a cable grommet cutout
    on a desktop surface.

    Attributes:
        x_position: Distance from left edge of desktop in inches.
        y_position: Distance from front edge of desktop in inches.
        diameter: Grommet diameter in inches.
    """

    x_position: float  # From left edge of desktop
    y_position: float  # From front edge of desktop
    diameter: float  # Grommet diameter in inches

    def __post_init__(self) -> None:
        """Validate grommet specification values."""
        if self.x_position < 0:
            raise ValueError("x_position must be non-negative")
        if self.y_position < 0:
            raise ValueError("y_position must be non-negative")
        if self.diameter <= 0:
            raise ValueError("diameter must be positive")


@dataclass(frozen=True)
class LShapedDeskConfiguration:
    """Configuration for L-shaped desk layout.

    An L-shaped desk consists of two desk surfaces that meet at a corner:
    the main surface (primary work area) and the return surface (secondary
    work area on the perpendicular wall).

    Attributes:
        main_surface_width: Width of main desk surface in inches.
        return_surface_width: Width of return surface in inches.
        main_surface_depth: Depth of main surface (default: 24").
        return_surface_depth: Depth of return surface (can differ from main).
        desk_height: Height of both surfaces in inches (must match).
        corner_type: Connection type - "butt" or "diagonal".
        corner_post: Include vertical support post at corner.
        main_left_pedestal: Pedestal config for main surface left side.
        return_right_pedestal: Pedestal config for return surface right side.
    """

    main_surface_width: float
    return_surface_width: float
    main_surface_depth: float = 24.0
    return_surface_depth: float = 24.0
    desk_height: float = 30.0
    corner_type: Literal["butt", "diagonal"] = "butt"
    corner_post: bool = True
    main_left_pedestal: dict[str, Any] | None = None
    return_right_pedestal: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate L-shaped desk configuration."""
        if self.main_surface_width <= 0:
            raise ValueError("main_surface_width must be positive")
        if self.return_surface_width <= 0:
            raise ValueError("return_surface_width must be positive")
        if self.main_surface_depth <= 0:
            raise ValueError("main_surface_depth must be positive")
        if self.return_surface_depth <= 0:
            raise ValueError("return_surface_depth must be positive")
        if self.desk_height <= 0:
            raise ValueError("desk_height must be positive")
        if self.corner_type not in ("butt", "diagonal"):
            raise ValueError("corner_type must be 'butt' or 'diagonal'")
