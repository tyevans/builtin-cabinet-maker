"""Validation structures and woodworking advisory checks.

This module provides validation result structures and domain-specific
validation logic for cabinet configurations, including woodworking
best practice advisories, obstacle validation, and infrastructure validation.
"""

from dataclasses import dataclass, field
from typing import Any

from cabinets.application.config.schema import (
    CabinetConfiguration,
    GrommetConfigSchema,
    InfrastructureConfigSchema,
    LightingConfigSchema,
    ObstacleConfig,
    OutletConfigSchema,
    VentilationConfigSchema,
    WallSegmentConfig,
)
from cabinets.domain.services.woodworking import get_max_span


# Standard grommet sizes in inches
STANDARD_GROMMET_SIZES: frozenset[float] = frozenset({2.0, 2.5, 3.0})

# Minimum edge distance for cutouts in inches
MIN_CUTOUT_EDGE_DISTANCE: float = 1.0


@dataclass
class ValidationError:
    """Represents a blocking validation error.

    Validation errors indicate configuration issues that must be fixed
    before the cabinet can be generated.

    Attributes:
        path: JSON path to the invalid field (e.g., "cabinet.sections[0].width")
        message: Human-readable description of the error
        value: The invalid value that caused the error
    """

    path: str
    message: str
    value: Any = None


@dataclass
class ValidationWarning:
    """Represents a non-blocking validation warning.

    Validation warnings indicate potential issues or deviations from
    woodworking best practices. The configuration can still be used,
    but the user should be aware of these concerns.

    Attributes:
        path: JSON path to the concerning field
        message: Human-readable description of the concern
        suggestion: Optional suggested remediation
    """

    path: str
    message: str
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Container for validation errors and warnings.

    This class collects all validation issues found during configuration
    validation and provides methods to check the overall validation status.

    Attributes:
        errors: List of blocking validation errors
        warnings: List of non-blocking validation warnings
    """

    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the configuration has no blocking errors."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """Check if the configuration has any warnings."""
        return len(self.warnings) > 0

    @property
    def exit_code(self) -> int:
        """Get the CLI exit code based on validation status.

        Returns:
            0 if valid with no warnings
            1 if there are errors
            2 if valid but has warnings
        """
        if self.errors:
            return 1
        if self.warnings:
            return 2
        return 0

    def add_error(
        self, path: str, message: str, value: Any = None
    ) -> "ValidationResult":
        """Add a validation error and return self for chaining."""
        self.errors.append(ValidationError(path=path, message=message, value=value))
        return self

    def add_warning(
        self, path: str, message: str, suggestion: str | None = None
    ) -> "ValidationResult":
        """Add a validation warning and return self for chaining."""
        self.warnings.append(
            ValidationWarning(path=path, message=message, suggestion=suggestion)
        )
        return self

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another ValidationResult into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self


# Woodworking Advisory Constants
# Note: SPAN_LIMITS and get_max_span are imported from woodworking.py for material-specific limits
MIN_RECOMMENDED_THICKNESS = 0.5  # inches
MAX_ASPECT_RATIO = 4.0  # height:depth ratio for stability


def check_woodworking_advisories(config: CabinetConfiguration) -> ValidationResult:
    """Check configuration against woodworking best practices.

    This function validates the configuration against common woodworking
    guidelines and returns warnings for potential issues. These are advisory
    only and do not prevent cabinet generation.

    Advisories checked:
    - Shelf span exceeds recommended maximum for material thickness
    - Material thickness is very thin (< 0.5")
    - Extreme cabinet aspect ratios (stability concerns)

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        ValidationResult containing any warnings found
    """
    result = ValidationResult()

    material_thickness = config.cabinet.material.thickness
    material_type = config.cabinet.material.type

    # Check each section for shelf span concerns
    for i, section in enumerate(config.cabinet.sections):
        section_path = f"cabinet.sections[{i}]"

        # Determine effective section width
        section_width: float | None = None
        if isinstance(section.width, (int, float)):
            section_width = float(section.width)
        elif section.width == "fill":
            # For "fill" sections, we need to estimate the width
            # This is approximate - actual calculation happens in domain layer
            section_width = _estimate_fill_section_width(config, i)

        # Check shelf span using material-specific limits from SPAN_LIMITS
        if section_width is not None and section.shelves > 0:
            max_span = get_max_span(material_type, material_thickness)
            if section_width > max_span:
                result.add_warning(
                    path=section_path,
                    message=(
                        f"Shelf span of {section_width:.0f}\" exceeds recommended "
                        f"{max_span:.0f}\" for {material_type.value} at {material_thickness}\" thickness"
                    ),
                    suggestion=(
                        "Consider adding a center support divider or using "
                        "thicker material (1\" or greater)"
                    ),
                )

    # Check for very thin material
    if material_thickness < MIN_RECOMMENDED_THICKNESS:
        result.add_warning(
            path="cabinet.material.thickness",
            message=(
                f"Material thickness of {material_thickness}\" is below "
                f"recommended minimum of {MIN_RECOMMENDED_THICKNESS}\""
            ),
            suggestion="Consider using at least 1/2\" (0.5\") material for structural integrity",
        )

    # Check back material thickness if specified
    if config.cabinet.back_material:
        back_thickness = config.cabinet.back_material.thickness
        if back_thickness < 0.25:
            result.add_warning(
                path="cabinet.back_material.thickness",
                message=f"Back panel thickness of {back_thickness}\" is very thin",
                suggestion="Consider using at least 1/4\" (0.25\") material for the back panel",
            )

    # Check aspect ratio for stability
    aspect_ratio = config.cabinet.height / config.cabinet.depth
    if aspect_ratio > MAX_ASPECT_RATIO:
        result.add_warning(
            path="cabinet",
            message=(
                f"Height-to-depth ratio of {aspect_ratio:.1f}:1 may cause stability issues"
            ),
            suggestion=(
                f"Consider increasing depth or securing cabinet to wall. "
                f"Recommended ratio is {MAX_ASPECT_RATIO:.0f}:1 or less"
            ),
        )

    return result


def _estimate_fill_section_width(config: CabinetConfiguration, section_index: int) -> float | None:
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


def check_obstacle_advisories(
    config: CabinetConfiguration,
) -> list[ValidationError | ValidationWarning]:
    """Check obstacle-related validation rules.

    Validates obstacles against the following rules:
    - V-01: Obstacle must be within wall bounds
    - V-02: Wall reference must be valid (within walls array)
    - V-03: Clearance must be non-negative (handled by Pydantic, but double-check)
    - V-04: Wall must have usable area (not completely blocked)
    - V-06: Width below minimum warning

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of validation errors and warnings for obstacle-related issues
    """
    results: list[ValidationError | ValidationWarning] = []

    if not config.room or not config.room.obstacles:
        return results

    walls = config.room.walls if config.room.walls else []

    for i, obstacle in enumerate(config.room.obstacles):
        path = f"room.obstacles[{i}]"

        # V-02: Wall reference valid
        if obstacle.wall >= len(walls):
            results.append(
                ValidationError(
                    path=path,
                    message=f"Obstacle references unknown wall index: {obstacle.wall}",
                    value=obstacle.wall,
                )
            )
            continue

        wall = walls[obstacle.wall]

        # V-01: Obstacle within wall bounds (horizontal)
        if obstacle.horizontal_offset + obstacle.width > wall.length:
            results.append(
                ValidationError(
                    path=path,
                    message=(
                        f"Obstacle extends beyond wall {obstacle.wall} "
                        f"(wall length: {wall.length}, obstacle ends at: "
                        f"{obstacle.horizontal_offset + obstacle.width})"
                    ),
                )
            )

        # V-01: Obstacle within wall bounds (vertical)
        if obstacle.bottom + obstacle.height > wall.height:
            results.append(
                ValidationError(
                    path=path,
                    message=(
                        f"Obstacle extends beyond wall {obstacle.wall} height "
                        f"(wall height: {wall.height}, obstacle ends at: "
                        f"{obstacle.bottom + obstacle.height})"
                    ),
                )
            )

    # V-04: Check if any wall is completely blocked or mostly blocked
    for wall_idx, wall in enumerate(walls):
        wall_obstacles = [o for o in config.room.obstacles if o.wall == wall_idx]
        if _wall_completely_blocked(wall, wall_obstacles):
            results.append(
                ValidationError(
                    path=f"room.walls[{wall_idx}]",
                    message=f"Wall {wall_idx} is entirely blocked by obstacles",
                )
            )
        elif _wall_mostly_blocked(wall, wall_obstacles, threshold=0.8):
            results.append(
                ValidationWarning(
                    path=f"room.walls[{wall_idx}]",
                    message=f"Wall {wall_idx} has >80% of usable width blocked by obstacles",
                    suggestion="Consider if there is enough space for cabinet sections",
                )
            )

    return results


def _wall_completely_blocked(
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


def _wall_mostly_blocked(
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


# =============================================================================
# Infrastructure Validation Functions (FRD-15)
# =============================================================================


def _get_panel_dimensions(
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


def _cutouts_overlap(
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


def _get_cutout_info(
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


def _get_section_count(config: CabinetConfiguration) -> int:
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


def check_infrastructure_advisories(
    config: CabinetConfiguration,
) -> list[ValidationError | ValidationWarning]:
    """Check infrastructure configuration for potential issues.

    Validates infrastructure elements against the following rules:
    - V-01: Cutout within panel bounds
    - V-02: Cutout edge distance (min 1")
    - V-03: Cutout overlap detection
    - V-04: Outlet accessibility (behind fixed shelf warning)
    - V-05: Grommet size validation (standard sizes: 2, 2.5, or 3)
    - V-06: Section index validation
    - V-07: Ventilation adequacy warning

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of validation errors and warnings for infrastructure-related issues
    """
    results: list[ValidationError | ValidationWarning] = []

    if not config.infrastructure:
        return results

    infra = config.infrastructure
    section_count = _get_section_count(config)

    # Collect all cutouts for overlap detection, organized by panel
    panel_cutouts: dict[str, list[tuple[str, tuple[float, float], tuple[float, float]]]] = {}

    # V-06: Section index validation for lighting
    for i, lighting in enumerate(infra.lighting):
        path = f"infrastructure.lighting[{i}]"
        for section_idx in lighting.section_indices:
            if section_idx >= section_count:
                results.append(
                    ValidationError(
                        path=f"{path}.section_indices",
                        message=f"Section index {section_idx} out of range (cabinet has {section_count} sections)",
                        value=section_idx,
                    )
                )

    # Process outlets
    for i, outlet in enumerate(infra.outlets):
        path = f"infrastructure.outlets[{i}]"

        # V-06: Section index validation
        if outlet.section_index >= section_count:
            results.append(
                ValidationError(
                    path=f"{path}.section_index",
                    message=f"Section index {outlet.section_index} out of range (cabinet has {section_count} sections)",
                    value=outlet.section_index,
                )
            )

        # Get panel dimensions and cutout info
        panel_dims = _get_panel_dimensions(config, outlet.panel)
        cutout_path, cutout_pos, cutout_dims, panel = _get_cutout_info(outlet, "outlet", i)

        # V-01: Cutout within panel bounds
        if cutout_pos[0] + cutout_dims[0] > panel_dims[0]:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel width: {panel_dims[0]})",
                )
            )
        if cutout_pos[1] + cutout_dims[1] > panel_dims[1]:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel height: {panel_dims[1]})",
                )
            )
        if cutout_pos[0] < 0 or cutout_pos[1] < 0:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) has negative position",
                )
            )

        # V-02: Cutout edge distance
        if cutout_pos[0] < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if cutout_pos[1] < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if panel_dims[0] - (cutout_pos[0] + cutout_dims[0]) < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if panel_dims[1] - (cutout_pos[1] + cutout_dims[1]) < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )

        # V-04: Outlet accessibility - check if outlet is behind a shelf position
        # This is a simplified check; in reality, it would need to compare against
        # actual shelf heights within the specified section
        if outlet.panel == "back" and config.cabinet.sections:
            if outlet.section_index < len(config.cabinet.sections):
                section = config.cabinet.sections[outlet.section_index]
                if section.shelves > 0:
                    results.append(
                        ValidationWarning(
                            path=path,
                            message=f"Outlet behind fixed shelf at section {outlet.section_index}",
                            suggestion="Consider adjusting shelf positions or outlet location for accessibility",
                        )
                    )

        # Collect for overlap detection
        if panel not in panel_cutouts:
            panel_cutouts[panel] = []
        panel_cutouts[panel].append((cutout_path, cutout_pos, cutout_dims))

    # Process grommets
    for i, grommet in enumerate(infra.grommets):
        path = f"infrastructure.grommets[{i}]"

        # V-05: Grommet size validation
        if grommet.size not in STANDARD_GROMMET_SIZES:
            results.append(
                ValidationError(
                    path=f"{path}.size",
                    message=f"Invalid grommet size: {grommet.size} (use 2, 2.5, or 3)",
                    value=grommet.size,
                )
            )

        # V-06: Section index validation (if specified)
        if grommet.section_index is not None and grommet.section_index >= section_count:
            results.append(
                ValidationError(
                    path=f"{path}.section_index",
                    message=f"Section index {grommet.section_index} out of range (cabinet has {section_count} sections)",
                    value=grommet.section_index,
                )
            )

        # Get panel dimensions and cutout info
        panel_dims = _get_panel_dimensions(config, grommet.panel)
        cutout_path, cutout_pos, cutout_dims, panel = _get_cutout_info(grommet, "grommet", i)

        # V-01: Cutout within panel bounds
        if cutout_pos[0] + cutout_dims[0] > panel_dims[0]:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel width: {panel_dims[0]})",
                )
            )
        if cutout_pos[1] + cutout_dims[1] > panel_dims[1]:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel height: {panel_dims[1]})",
                )
            )
        if cutout_pos[0] < 0 or cutout_pos[1] < 0:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) has negative position",
                )
            )

        # V-02: Cutout edge distance
        if cutout_pos[0] < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if cutout_pos[1] < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if panel_dims[0] - (cutout_pos[0] + cutout_dims[0]) < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if panel_dims[1] - (cutout_pos[1] + cutout_dims[1]) < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )

        # Collect for overlap detection
        if panel not in panel_cutouts:
            panel_cutouts[panel] = []
        panel_cutouts[panel].append((cutout_path, cutout_pos, cutout_dims))

    # Process ventilation areas
    for i, vent in enumerate(infra.ventilation):
        path = f"infrastructure.ventilation[{i}]"

        # Get panel dimensions and cutout info
        panel_dims = _get_panel_dimensions(config, vent.panel)
        cutout_path, cutout_pos, cutout_dims, panel = _get_cutout_info(vent, "ventilation", i)

        # V-01: Cutout within panel bounds
        if cutout_pos[0] + cutout_dims[0] > panel_dims[0]:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel width: {panel_dims[0]})",
                )
            )
        if cutout_pos[1] + cutout_dims[1] > panel_dims[1]:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel height: {panel_dims[1]})",
                )
            )
        if cutout_pos[0] < 0 or cutout_pos[1] < 0:
            results.append(
                ValidationError(
                    path=path,
                    message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) has negative position",
                )
            )

        # V-02: Cutout edge distance
        if cutout_pos[0] < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if cutout_pos[1] < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if panel_dims[0] - (cutout_pos[0] + cutout_dims[0]) < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )
        if panel_dims[1] - (cutout_pos[1] + cutout_dims[1]) < MIN_CUTOUT_EDGE_DISTANCE:
            results.append(
                ValidationError(
                    path=path,
                    message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
                )
            )

        # Collect for overlap detection
        if panel not in panel_cutouts:
            panel_cutouts[panel] = []
        panel_cutouts[panel].append((cutout_path, cutout_pos, cutout_dims))

    # V-03: Cutout overlap detection
    for panel, cutouts in panel_cutouts.items():
        for i, (path1, pos1, dims1) in enumerate(cutouts):
            for j, (path2, pos2, dims2) in enumerate(cutouts[i + 1 :], start=i + 1):
                if _cutouts_overlap(pos1, dims1, pos2, dims2):
                    results.append(
                        ValidationError(
                            path=path1,
                            message=f"Cutouts overlap at ({pos1[0]}, {pos1[1]})",
                        )
                    )

    # V-07: Ventilation adequacy warning
    # Check if there are electronics-related keywords in notes or configuration
    # but no ventilation is configured
    has_ventilation = len(infra.ventilation) > 0
    has_outlets = len(infra.outlets) > 0

    # If we have outlets but no ventilation, suggest ventilation for electronics
    if has_outlets and not has_ventilation:
        results.append(
            ValidationWarning(
                path="infrastructure",
                message="Electronics enclosure may need additional ventilation",
                suggestion="Consider adding ventilation cutouts for heat dissipation",
            )
        )

    return results


def validate_config(config: CabinetConfiguration) -> ValidationResult:
    """Perform full validation of a cabinet configuration.

    This function performs both structural validation (which should already
    be handled by Pydantic) and advisory checks for woodworking best practices,
    obstacle validation, and infrastructure validation.

    Args:
        config: A CabinetConfiguration instance (already validated by Pydantic)

    Returns:
        ValidationResult containing any errors or warnings
    """
    result = ValidationResult()

    # Add woodworking advisory checks
    result.merge(check_woodworking_advisories(config))

    # Add obstacle validation
    obstacle_results = check_obstacle_advisories(config)
    for r in obstacle_results:
        if isinstance(r, ValidationError):
            result.add_error(r.path, r.message, r.value)
        else:
            result.add_warning(r.path, r.message, r.suggestion)

    # Add infrastructure validation (FRD-15)
    if config.infrastructure is not None:
        infra_results = check_infrastructure_advisories(config)
        for r in infra_results:
            if isinstance(r, ValidationError):
                result.add_error(r.path, r.message, r.value)
            else:
                result.add_warning(r.path, r.message, r.suggestion)

    # Validate total fixed section width doesn't exceed cabinet width
    total_fixed_width = 0.0
    for section in config.cabinet.sections:
        if isinstance(section.width, (int, float)):
            total_fixed_width += section.width

    material_thickness = config.cabinet.material.thickness
    num_dividers = len(config.cabinet.sections) - 1 if config.cabinet.sections else 0
    available_width = (
        config.cabinet.width
        - (material_thickness * 2)
        - (material_thickness * num_dividers)
    )

    if total_fixed_width > available_width:
        result.add_error(
            path="cabinet.sections",
            message=(
                f"Total fixed section width ({total_fixed_width:.1f}\") exceeds "
                f"available cabinet interior width ({available_width:.1f}\")"
            ),
            value=total_fixed_width,
        )

    # FR-06.3: Validate section depth overrides don't exceed cabinet depth
    cabinet_depth = config.cabinet.depth
    for i, section in enumerate(config.cabinet.sections):
        if section.depth is not None and section.depth > cabinet_depth:
            result.add_error(
                path=f"cabinet.sections[{i}].depth",
                message=(
                    f"Section depth ({section.depth}\") exceeds "
                    f"cabinet depth ({cabinet_depth}\")"
                ),
                value=section.depth,
            )

    # Also validate section depths in multi-row layouts
    if config.cabinet.rows:
        for row_idx, row in enumerate(config.cabinet.rows):
            for section_idx, section in enumerate(row.sections):
                if section.depth is not None and section.depth > cabinet_depth:
                    result.add_error(
                        path=f"cabinet.rows[{row_idx}].sections[{section_idx}].depth",
                        message=(
                            f"Section depth ({section.depth}\") exceeds "
                            f"cabinet depth ({cabinet_depth}\")"
                        ),
                        value=section.depth,
                    )

    return result
