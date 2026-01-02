"""Helper functions for cabinet configuration validation.

This module provides shared geometry and calculation helpers used by
multiple validators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cabinets.application.config.schemas import (
        CabinetConfiguration,
        GrommetConfigSchema,
        ObstacleConfig,
        OutletConfigSchema,
        VentilationConfigSchema,
        WallSegmentConfig,
    )


def estimate_fill_section_width(
    config: CabinetConfiguration, section_index: int
) -> float | None:
    """Estimate the width of a 'fill' section.

    This is an approximation for advisory purposes. The actual width
    calculation is performed in the domain layer.

    Args:
        config: The cabinet configuration
        section_index: Index of the section to estimate

    Returns:
        Estimated width in inches, or None if cannot be determined
    """
    sections = config.cabinet.sections
    if not sections:
        return config.cabinet.width - (config.cabinet.material.thickness * 2)

    # Count fixed and fill sections
    fixed_total = 0.0
    fill_count = 0

    for section in sections:
        if isinstance(section.width, (int, float)):
            fixed_total += section.width
        else:
            fill_count += 1

    if fill_count == 0:
        return None

    # Calculate available space for fill sections
    # Subtract material thickness for sides and dividers
    material_thickness = config.cabinet.material.thickness
    num_dividers = len(sections) - 1
    side_material = material_thickness * 2  # Left and right sides
    divider_material = material_thickness * num_dividers

    available = config.cabinet.width - side_material - divider_material - fixed_total

    if available <= 0:
        return None

    # Divide equally among fill sections
    return available / fill_count


def get_panel_dimensions(
    config: CabinetConfiguration, panel: str
) -> tuple[float, float]:
    """Get width and height of a panel based on cabinet dimensions.

    Returns the panel dimensions based on cabinet geometry:
    - back panel: width x height
    - left_side/right_side: depth x height
    - top/bottom: width x depth

    Args:
        config: The cabinet configuration
        panel: Panel name (back, left_side, right_side, top, bottom)

    Returns:
        Tuple of (width, height) in inches
    """
    cab = config.cabinet
    if panel == "back":
        return (cab.width, cab.height)
    elif panel in ("left_side", "right_side"):
        return (cab.depth, cab.height)
    elif panel == "top":
        return (cab.width, cab.depth)
    elif panel == "bottom":
        return (cab.width, cab.depth)
    else:
        # For unknown panels, return cabinet width x height as default
        return (cab.width, cab.height)


def cutouts_overlap(
    c1_pos: tuple[float, float],
    c1_dims: tuple[float, float],
    c2_pos: tuple[float, float],
    c2_dims: tuple[float, float],
) -> bool:
    """Check if two rectangular cutouts overlap.

    Uses axis-aligned bounding box collision detection.

    Args:
        c1_pos: (x, y) position of first cutout
        c1_dims: (width, height) of first cutout
        c2_pos: (x, y) position of second cutout
        c2_dims: (width, height) of second cutout

    Returns:
        True if the cutouts overlap, False otherwise
    """
    # Calculate bounding box corners
    c1_left = c1_pos[0]
    c1_right = c1_pos[0] + c1_dims[0]
    c1_bottom = c1_pos[1]
    c1_top = c1_pos[1] + c1_dims[1]

    c2_left = c2_pos[0]
    c2_right = c2_pos[0] + c2_dims[0]
    c2_bottom = c2_pos[1]
    c2_top = c2_pos[1] + c2_dims[1]

    # Check for non-overlapping conditions
    if c1_right <= c2_left or c2_right <= c1_left:
        return False
    if c1_top <= c2_bottom or c2_top <= c1_bottom:
        return False

    return True


def get_cutout_info(
    element: OutletConfigSchema | GrommetConfigSchema | VentilationConfigSchema,
    element_type: str,
    index: int,
) -> tuple[str, tuple[float, float], tuple[float, float], str]:
    """Extract cutout information from an infrastructure element.

    Args:
        element: The infrastructure element configuration
        element_type: Type of element (outlet, grommet, ventilation)
        index: Index of the element in its list

    Returns:
        Tuple of (path, position, dimensions, panel)
    """
    # Import here to avoid circular imports
    from cabinets.application.config.schemas import (
        GrommetConfigSchema,
        OutletConfigSchema,
        VentilationConfigSchema,
    )

    path = f"infrastructure.{element_type}s[{index}]"

    if isinstance(element, OutletConfigSchema):
        # Standard outlet cutout dimensions
        if element.type.value == "single":
            dims = (2.75, 4.5)  # Standard single outlet box
        elif element.type.value == "gfi":
            dims = (2.75, 5.5)  # GFI outlets are taller
        else:  # double
            dims = (4.5, 4.5)  # Double outlet box
        return (path, (element.position.x, element.position.y), dims, element.panel)
    elif isinstance(element, GrommetConfigSchema):
        # Grommets are circular, use diameter for both dimensions
        dims = (element.size, element.size)
        return (path, (element.position.x, element.position.y), dims, element.panel)
    elif isinstance(element, VentilationConfigSchema):
        dims = (element.width, element.height)
        return (path, (element.position.x, element.position.y), dims, element.panel)

    # Default fallback
    return (path, (0, 0), (0, 0), "")


def get_section_count(config: CabinetConfiguration) -> int:
    """Get the total number of sections in the cabinet.

    Handles both single-row (sections) and multi-row (rows) layouts.

    Args:
        config: The cabinet configuration

    Returns:
        Total number of sections
    """
    if config.cabinet.rows:
        # Multi-row layout: count sections in all rows
        return sum(len(row.sections) for row in config.cabinet.rows)
    else:
        # Single-row layout
        return len(config.cabinet.sections) if config.cabinet.sections else 1


def wall_completely_blocked(
    wall: WallSegmentConfig, obstacles: list[ObstacleConfig]
) -> bool:
    """Check if wall is completely blocked by obstacles.

    A wall is considered completely blocked if obstacles cover the entire
    width of the wall (ignoring height considerations for simplicity).

    Args:
        wall: The wall configuration to check
        obstacles: List of obstacles on this wall

    Returns:
        True if the wall is completely blocked, False otherwise
    """
    if not obstacles:
        return False

    # Sort obstacles by horizontal position
    sorted_obs = sorted(obstacles, key=lambda o: o.horizontal_offset)

    # Check for gaps - if any gap exists, wall is not completely blocked
    current_x = 0.0
    for obs in sorted_obs:
        if obs.horizontal_offset > current_x:
            return False  # Gap found
        current_x = max(current_x, obs.horizontal_offset + obs.width)

    return current_x >= wall.length


def wall_mostly_blocked(
    wall: WallSegmentConfig, obstacles: list[ObstacleConfig], threshold: float
) -> bool:
    """Check if wall width is mostly blocked.

    A wall is considered mostly blocked if the total obstacle width
    exceeds the threshold percentage of the wall length.

    Note: This is a simplified check that does not account for obstacle
    overlaps. For more accurate blocking calculation, use the domain
    layer obstacle collision service.

    Args:
        wall: The wall configuration to check
        obstacles: List of obstacles on this wall
        threshold: Fraction (0.0-1.0) of wall that must be blocked

    Returns:
        True if the wall is mostly blocked, False otherwise
    """
    if not obstacles:
        return False

    # Calculate total blocked width (simplified, ignoring overlaps)
    blocked_width = sum(o.width for o in obstacles)
    return blocked_width / wall.length > threshold
