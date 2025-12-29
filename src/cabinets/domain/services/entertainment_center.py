"""Entertainment center layout service for generating media cabinet configurations.

This module provides the EntertainmentCenterLayoutService for generating
entertainment center layouts with proper TV integration, cable management,
and media equipment accommodation.

FRD-19: Entertainment Centers and Media Fixtures - Phase 6: Layout Types
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from ..value_objects import Dimensions, Position

if TYPE_CHECKING:
    from ..entities import Cabinet, Section


@dataclass(frozen=True)
class TVIntegration:
    """TV placement specifications.

    Represents the configuration for TV integration in an entertainment center,
    including screen size, mounting method, and calculated viewing dimensions.

    Attributes:
        screen_size: Diagonal screen size in inches.
        mounting: Method of TV mounting ("wall" or "stand").
        center_height: Height from floor to TV center in inches.
        viewing_width: Calculated viewing width based on screen size in inches.
    """

    screen_size: int
    mounting: Literal["wall", "stand"]
    center_height: float
    viewing_width: float

    def __post_init__(self) -> None:
        if self.screen_size < 32:
            raise ValueError("Screen size must be at least 32 inches")
        if self.screen_size > 100:
            raise ValueError("Screen size must be at most 100 inches")
        if self.center_height <= 0:
            raise ValueError("Center height must be positive")
        if self.viewing_width <= 0:
            raise ValueError("Viewing width must be positive")

    @classmethod
    def from_screen_size(
        cls,
        size: int,
        mounting: Literal["wall", "stand"] = "wall",
        center_height: float = 42.0,
    ) -> "TVIntegration":
        """Create TVIntegration from screen size with calculated dimensions.

        Calculates the approximate viewing width based on the diagonal screen
        size assuming a 16:9 aspect ratio.

        Args:
            size: Diagonal screen size in inches.
            mounting: Method of TV mounting ("wall" or "stand").
            center_height: Height from floor to TV center in inches.
                          Default of 42" is optimal for seated viewing.

        Returns:
            TVIntegration instance with calculated viewing width.
        """
        # Standard TV widths for 16:9 aspect ratio (width = diagonal * 0.87 approximately)
        width_map = {
            32: 28.0,
            40: 35.0,
            43: 37.5,
            50: 44.0,
            55: 48.0,
            65: 57.0,
            75: 65.0,
            85: 74.0,
        }
        viewing_width = width_map.get(size, size * 0.87)
        return cls(
            screen_size=size,
            mounting=mounting,
            center_height=center_height,
            viewing_width=viewing_width,
        )


@dataclass(frozen=True)
class TVZone:
    """Calculated TV zone placement within a cabinet.

    Contains the calculated positions and dimensions for the TV zone
    and flanking storage areas.

    Attributes:
        tv_zone_start: Distance from cabinet left edge to TV zone start in inches.
        tv_zone_width: Width of the TV zone in inches.
        tv_zone_end: Distance from cabinet left edge to TV zone end in inches.
        flanking_left_width: Width of left flanking storage area in inches.
        flanking_right_width: Width of right flanking storage area in inches.
        tv_center_height: Height from floor to TV center in inches.
    """

    tv_zone_start: float
    tv_zone_width: float
    tv_zone_end: float
    flanking_left_width: float
    flanking_right_width: float
    tv_center_height: float

    def __post_init__(self) -> None:
        if self.tv_zone_width <= 0:
            raise ValueError("TV zone width must be positive")
        if self.flanking_left_width < 0:
            raise ValueError("Flanking left width must be non-negative")
        if self.flanking_right_width < 0:
            raise ValueError("Flanking right width must be non-negative")


@dataclass(frozen=True)
class CableChasePosition:
    """Position specification for a cable chase.

    Represents the location of a cable chase for wire routing
    within the entertainment center.

    Attributes:
        x: Horizontal position from cabinet left edge in inches.
        y: Vertical position from cabinet bottom in inches.
        width: Width of the cable chase in inches.
        purpose: Description of the cable chase purpose.
    """

    x: float
    y: float
    width: float = 3.0
    purpose: str = ""

    def __post_init__(self) -> None:
        if self.x < 0:
            raise ValueError("X position must be non-negative")
        if self.y < 0:
            raise ValueError("Y position must be non-negative")
        if self.width <= 0:
            raise ValueError("Width must be positive")

    def to_position(self) -> Position:
        """Convert to a Position value object.

        Returns:
            Position instance with x and y coordinates.
        """
        return Position(x=self.x, y=self.y)


class EntertainmentCenterLayoutService:
    """Service for generating entertainment center layouts.

    Provides methods for creating and validating entertainment center
    configurations including TV integration, equipment placement, and
    cable management.

    Entertainment center layout types supported:
    - CONSOLE: Low profile (16-30" height) for wall-mounted TV above
    - WALL_UNIT: Full height (72-96") with central TV zone
    - FLOATING: Wall-mounted with cleat system (12-24" height)
    - TOWER: Vertical equipment stack (24-36" width, 18"+ depth)

    Example:
        >>> service = EntertainmentCenterLayoutService()
        >>> tv = TVIntegration.from_screen_size(65)
        >>> errors, warnings = service.validate_layout(
        ...     "console",
        ...     Dimensions(width=72.0, height=24.0, depth=18.0)
        ... )
        >>> tv_zone = service.calculate_tv_zone(tv, cabinet_width=72.0)
    """

    # Layout constraints for each entertainment center type
    LAYOUT_CONSTRAINTS: dict[str, dict[str, float]] = {
        "console": {
            "min_height": 16.0,
            "max_height": 30.0,
            "default_height": 24.0,
            "min_depth": 14.0,
        },
        "wall_unit": {
            "min_height": 72.0,
            "max_height": 96.0,
            "default_height": 84.0,
            "min_depth": 12.0,
        },
        "floating": {
            "min_height": 12.0,
            "max_height": 24.0,
            "default_height": 18.0,
            "max_weight_lbs": 150.0,
            "min_depth": 12.0,
        },
        "tower": {
            "min_width": 24.0,
            "max_width": 36.0,
            "min_depth": 18.0,
            "default_depth": 20.0,
        },
    }

    # Standard cable chase width in inches
    DEFAULT_CABLE_CHASE_WIDTH: float = 3.0

    # TV clearance requirements (inches on each side)
    TV_SIDE_CLEARANCE: float = 2.0

    def __init__(self) -> None:
        """Initialize the entertainment center layout service."""
        self.layout_constraints = self.LAYOUT_CONSTRAINTS.copy()

    def validate_layout(
        self, layout_type: str, dimensions: Dimensions
    ) -> tuple[list[str], list[str]]:
        """Validate layout dimensions against constraints.

        Checks if the provided dimensions meet the requirements for the
        specified entertainment center layout type.

        Args:
            layout_type: Type of entertainment center layout.
                        One of "console", "wall_unit", "floating", "tower".
            dimensions: Cabinet dimensions to validate.

        Returns:
            Tuple of (errors, warnings) where errors are critical issues
            that prevent valid layout generation and warnings are advisory
            messages about potential concerns.

        Raises:
            ValueError: If layout_type is not recognized.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if layout_type not in self.layout_constraints:
            raise ValueError(
                f"Unknown layout type '{layout_type}'. "
                f"Valid types: {list(self.layout_constraints.keys())}"
            )

        constraints = self.layout_constraints[layout_type]

        if layout_type == "console":
            # Console height validation
            if dimensions.height < constraints["min_height"]:
                errors.append(
                    f"Console height {dimensions.height}\" below minimum "
                    f"{constraints['min_height']}\""
                )
            elif dimensions.height > constraints["max_height"]:
                warnings.append(
                    f"Console height {dimensions.height}\" exceeds typical "
                    f"maximum {constraints['max_height']}\""
                )
            # Console depth validation
            if dimensions.depth < constraints["min_depth"]:
                warnings.append(
                    f"Console depth {dimensions.depth}\" may be insufficient "
                    f"for equipment (recommend {constraints['min_depth']}\"+)"
                )

        elif layout_type == "wall_unit":
            # Wall unit height validation
            if dimensions.height < constraints["min_height"]:
                errors.append(
                    f"Wall unit height {dimensions.height}\" below minimum "
                    f"{constraints['min_height']}\""
                )
            elif dimensions.height > constraints["max_height"]:
                warnings.append(
                    f"Wall unit height {dimensions.height}\" exceeds typical "
                    f"maximum {constraints['max_height']}\""
                )
            # Wall unit depth validation
            if dimensions.depth < constraints["min_depth"]:
                warnings.append(
                    f"Wall unit depth {dimensions.depth}\" may be insufficient "
                    f"for equipment"
                )

        elif layout_type == "floating":
            # Floating height validation
            if dimensions.height < constraints["min_height"]:
                errors.append(
                    f"Floating unit height {dimensions.height}\" below minimum "
                    f"{constraints['min_height']}\""
                )
            elif dimensions.height > constraints["max_height"]:
                warnings.append(
                    f"Floating unit height {dimensions.height}\" exceeds typical "
                    f"maximum {constraints['max_height']}\""
                )
            # Floating depth validation
            if dimensions.depth < constraints["min_depth"]:
                warnings.append(
                    f"Floating unit depth {dimensions.depth}\" may be insufficient"
                )

        elif layout_type == "tower":
            # Tower width validation
            if dimensions.width < constraints["min_width"]:
                errors.append(
                    f"Tower width {dimensions.width}\" too narrow, minimum "
                    f"{constraints['min_width']}\""
                )
            elif dimensions.width > constraints["max_width"]:
                warnings.append(
                    f"Tower width {dimensions.width}\" exceeds typical maximum "
                    f"{constraints['max_width']}\""
                )
            # Tower depth validation (critical for equipment)
            if dimensions.depth < constraints["min_depth"]:
                errors.append(
                    f"Tower depth {dimensions.depth}\" insufficient for equipment, "
                    f"minimum {constraints['min_depth']}\""
                )

        return errors, warnings

    def calculate_tv_zone(self, tv: TVIntegration, cabinet_width: float) -> TVZone:
        """Calculate TV zone placement within cabinet.

        Determines the positions for the TV zone and flanking storage areas
        based on the TV specifications and cabinet width.

        Args:
            tv: TV integration specifications.
            cabinet_width: Total cabinet width in inches.

        Returns:
            TVZone with calculated positions and dimensions.

        Raises:
            ValueError: If cabinet width is insufficient for TV zone.
        """
        # TV zone width includes clearance on each side
        tv_zone_width = tv.viewing_width + (self.TV_SIDE_CLEARANCE * 2)

        # Check if cabinet is wide enough
        if tv_zone_width > cabinet_width:
            raise ValueError(
                f"Cabinet width {cabinet_width}\" insufficient for TV zone "
                f"({tv_zone_width}\" required including clearance)"
            )

        # Calculate flanking widths (centered TV)
        total_flanking = cabinet_width - tv_zone_width
        flanking_left_width = total_flanking / 2
        flanking_right_width = total_flanking / 2

        tv_zone_start = flanking_left_width
        tv_zone_end = flanking_left_width + tv_zone_width

        return TVZone(
            tv_zone_start=tv_zone_start,
            tv_zone_width=tv_zone_width,
            tv_zone_end=tv_zone_end,
            flanking_left_width=flanking_left_width,
            flanking_right_width=flanking_right_width,
            tv_center_height=tv.center_height,
        )

    def generate_cable_chase_positions(
        self, layout_type: str, cabinet_width: float, cabinet_height: float = 0.0
    ) -> list[CableChasePosition]:
        """Calculate cable chase positions for layout.

        Generates appropriate cable chase positions based on the layout type
        to facilitate cable routing within the entertainment center.

        Args:
            layout_type: Type of entertainment center layout.
            cabinet_width: Cabinet width in inches.
            cabinet_height: Cabinet height in inches (used for some layouts).

        Returns:
            List of CableChasePosition objects for cable routing.
        """
        positions: list[CableChasePosition] = []
        chase_width = self.DEFAULT_CABLE_CHASE_WIDTH

        if layout_type == "wall_unit":
            # Central cable chase behind TV zone
            positions.append(
                CableChasePosition(
                    x=cabinet_width / 2 - chase_width / 2,
                    y=0.0,
                    width=chase_width,
                    purpose="Central TV cable routing",
                )
            )

        elif layout_type == "tower":
            # Rear cable chase on right side for equipment stack
            positions.append(
                CableChasePosition(
                    x=cabinet_width - 4.0,
                    y=0.0,
                    width=chase_width,
                    purpose="Equipment stack cable routing",
                )
            )

        elif layout_type == "console":
            # Central cable chase for soundbar and equipment
            positions.append(
                CableChasePosition(
                    x=cabinet_width / 2 - chase_width / 2,
                    y=0.0,
                    width=chase_width,
                    purpose="Console equipment cable routing",
                )
            )

        elif layout_type == "floating":
            # Central cable chase with wall routing
            positions.append(
                CableChasePosition(
                    x=cabinet_width / 2 - chase_width / 2,
                    y=0.0,
                    width=chase_width,
                    purpose="Wall-mount cable routing to wall",
                )
            )

        return positions

    def get_default_dimensions(self, layout_type: str) -> Dimensions:
        """Get default dimensions for a layout type.

        Returns the recommended default dimensions for the specified
        entertainment center layout type.

        Args:
            layout_type: Type of entertainment center layout.

        Returns:
            Dimensions with default values for the layout type.

        Raises:
            ValueError: If layout_type is not recognized.
        """
        if layout_type not in self.layout_constraints:
            raise ValueError(
                f"Unknown layout type '{layout_type}'. "
                f"Valid types: {list(self.layout_constraints.keys())}"
            )

        constraints = self.layout_constraints[layout_type]

        if layout_type == "console":
            return Dimensions(
                width=72.0,
                height=constraints["default_height"],
                depth=18.0,
            )
        elif layout_type == "wall_unit":
            return Dimensions(
                width=96.0,
                height=constraints["default_height"],
                depth=16.0,
            )
        elif layout_type == "floating":
            return Dimensions(
                width=60.0,
                height=constraints["default_height"],
                depth=14.0,
            )
        elif layout_type == "tower":
            return Dimensions(
                width=30.0,
                height=72.0,
                depth=constraints["default_depth"],
            )
        else:
            # This should not be reached due to the check above
            raise ValueError(f"Unknown layout type '{layout_type}'")

    def calculate_floating_weight_capacity(
        self, width: float, depth: float, cleat_count: int = 2
    ) -> float:
        """Calculate safe weight capacity for floating mount.

        Estimates the safe weight capacity for a wall-mounted floating
        entertainment center based on dimensions and cleat configuration.

        Args:
            width: Cabinet width in inches.
            depth: Cabinet depth in inches.
            cleat_count: Number of French cleats used (default 2).

        Returns:
            Estimated safe weight capacity in pounds.

        Note:
            This is an advisory estimate only. Actual capacity depends
            on wall construction, stud alignment, and installation quality.
        """
        # Base capacity per cleat when mounted into studs (conservative estimate)
        capacity_per_cleat = 75.0  # lbs per cleat

        # Calculate total capacity
        total_capacity = capacity_per_cleat * cleat_count

        # Apply safety factor for wider/deeper units
        # Wider units have more leverage, reducing effective capacity
        width_factor = min(1.0, 48.0 / width) if width > 48.0 else 1.0
        depth_factor = min(1.0, 16.0 / depth) if depth > 16.0 else 1.0

        return total_capacity * width_factor * depth_factor

    def validate_floating_weight(
        self, dimensions: Dimensions, estimated_weight: float
    ) -> tuple[bool, str]:
        """Validate if floating mount can support estimated weight.

        Checks if a floating entertainment center configuration is safe
        for the estimated weight including cabinet and contents.

        Args:
            dimensions: Cabinet dimensions.
            estimated_weight: Estimated total weight in pounds.

        Returns:
            Tuple of (is_safe, message) where is_safe is True if the
            configuration is within safe limits.
        """
        constraints = self.layout_constraints.get("floating", {})
        max_weight = constraints.get("max_weight_lbs", 150.0)

        capacity = self.calculate_floating_weight_capacity(
            dimensions.width, dimensions.depth
        )

        if estimated_weight > max_weight:
            return (
                False,
                f"Estimated weight {estimated_weight:.0f} lbs exceeds maximum "
                f"safe floating mount capacity of {max_weight:.0f} lbs",
            )

        if estimated_weight > capacity:
            return (
                False,
                f"Estimated weight {estimated_weight:.0f} lbs exceeds calculated "
                f"safe capacity of {capacity:.0f} lbs for this configuration",
            )

        return (
            True,
            f"Weight {estimated_weight:.0f} lbs is within safe capacity "
            f"({capacity:.0f} lbs maximum)",
        )
