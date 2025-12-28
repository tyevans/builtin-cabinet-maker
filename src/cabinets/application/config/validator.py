"""Validation structures and woodworking advisory checks.

This module provides validation result structures and domain-specific
validation logic for cabinet configurations, including woodworking
best practice advisories and obstacle validation.
"""

from dataclasses import dataclass, field
from typing import Any

from cabinets.application.config.schema import (
    CabinetConfiguration,
    ObstacleConfig,
    WallSegmentConfig,
)


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
MAX_SHELF_SPAN_3_4_PLYWOOD = 36.0  # inches
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

        # Check shelf span for 3/4" material
        if section_width is not None and section.shelves > 0:
            if (
                material_thickness <= 0.75
                and section_width > MAX_SHELF_SPAN_3_4_PLYWOOD
            ):
                result.add_warning(
                    path=section_path,
                    message=(
                        f"Shelf span of {section_width:.0f}\" exceeds recommended "
                        f"{MAX_SHELF_SPAN_3_4_PLYWOOD:.0f}\" for {material_thickness}\" material"
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


def validate_config(config: CabinetConfiguration) -> ValidationResult:
    """Perform full validation of a cabinet configuration.

    This function performs both structural validation (which should already
    be handled by Pydantic) and advisory checks for woodworking best practices
    and obstacle validation.

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

    return result
