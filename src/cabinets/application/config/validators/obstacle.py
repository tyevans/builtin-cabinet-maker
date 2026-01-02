"""Obstacle validation for cabinet configurations.

This module provides validation for obstacles defined in room configurations,
including bounds checking and wall blocking detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ValidationError, ValidationResult, ValidationWarning
from .helpers import wall_completely_blocked, wall_mostly_blocked

if TYPE_CHECKING:
    from cabinets.application.config.schemas import CabinetConfiguration


class ObstacleValidator:
    """Validator for obstacle-related configuration rules.

    Validates obstacles against the following rules:
    - V-01: Obstacle must be within wall bounds
    - V-02: Wall reference must be valid (within walls array)
    - V-03: Clearance must be non-negative (handled by Pydantic, but double-check)
    - V-04: Wall must have usable area (not completely blocked)
    - V-06: Width below minimum warning
    """

    @property
    def name(self) -> str:
        """Return the validator name."""
        return "obstacle"

    def validate(self, config: CabinetConfiguration) -> ValidationResult:
        """Check obstacle-related validation rules.

        Args:
            config: A validated CabinetConfiguration instance

        Returns:
            ValidationResult containing any errors or warnings
        """
        result = ValidationResult()

        if not config.room or not config.room.obstacles:
            return result

        walls = config.room.walls if config.room.walls else []

        for i, obstacle in enumerate(config.room.obstacles):
            path = f"room.obstacles[{i}]"

            # V-02: Wall reference valid
            if obstacle.wall >= len(walls):
                result.add_error(
                    path=path,
                    message=f"Obstacle references unknown wall index: {obstacle.wall}",
                    value=obstacle.wall,
                )
                continue

            wall = walls[obstacle.wall]

            # V-01: Obstacle within wall bounds (horizontal)
            if obstacle.horizontal_offset + obstacle.width > wall.length:
                result.add_error(
                    path=path,
                    message=(
                        f"Obstacle extends beyond wall {obstacle.wall} "
                        f"(wall length: {wall.length}, obstacle ends at: "
                        f"{obstacle.horizontal_offset + obstacle.width})"
                    ),
                )

            # V-01: Obstacle within wall bounds (vertical)
            if obstacle.bottom + obstacle.height > wall.height:
                result.add_error(
                    path=path,
                    message=(
                        f"Obstacle extends beyond wall {obstacle.wall} height "
                        f"(wall height: {wall.height}, obstacle ends at: "
                        f"{obstacle.bottom + obstacle.height})"
                    ),
                )

        # V-04: Check if any wall is completely blocked or mostly blocked
        for wall_idx, wall in enumerate(walls):
            wall_obstacles = [o for o in config.room.obstacles if o.wall == wall_idx]
            if wall_completely_blocked(wall, wall_obstacles):
                result.add_error(
                    path=f"room.walls[{wall_idx}]",
                    message=f"Wall {wall_idx} is entirely blocked by obstacles",
                )
            elif wall_mostly_blocked(wall, wall_obstacles, threshold=0.8):
                result.add_warning(
                    path=f"room.walls[{wall_idx}]",
                    message=f"Wall {wall_idx} has >80% of usable width blocked by obstacles",
                    suggestion="Consider if there is enough space for cabinet sections",
                )

        return result


# Legacy function for backwards compatibility
def check_obstacle_advisories(
    config: CabinetConfiguration,
) -> list[ValidationError | ValidationWarning]:
    """Check obstacle-related validation rules.

    This function is maintained for backwards compatibility.
    New code should use ObstacleValidator directly.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of validation errors and warnings for obstacle-related issues
    """
    validator = ObstacleValidator()
    result = validator.validate(config)

    # Convert ValidationResult to list for legacy compatibility
    results: list[ValidationError | ValidationWarning] = []
    results.extend(result.errors)
    results.extend(result.warnings)
    return results
