"""Unit tests for ObstacleValidator."""

from __future__ import annotations

import pytest

from cabinets.application.config.schemas import (
    CabinetConfig,
    CabinetConfiguration,
    MaterialConfig,
    ObstacleConfig,
    ObstacleTypeConfig,
    RoomConfig,
    SectionConfig,
    WallSegmentConfig,
)
from cabinets.domain.value_objects import MaterialType
from cabinets.application.config.validators.obstacle import (
    ObstacleValidator,
    check_obstacle_advisories,
)


@pytest.fixture
def validator() -> ObstacleValidator:
    """Create an ObstacleValidator instance."""
    return ObstacleValidator()


@pytest.fixture
def config_with_room() -> CabinetConfiguration:
    """Create a cabinet configuration with room and walls."""
    return CabinetConfiguration(
        schema_version="1.6",
        cabinet=CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialConfig(
                type=MaterialType.PLYWOOD,
                thickness=0.75,
            ),
            sections=[
                SectionConfig(width=24.0, shelves=3),
            ],
        ),
        room=RoomConfig(
            name="test_room",
            walls=[
                WallSegmentConfig(length=120.0, height=96.0),
                WallSegmentConfig(length=96.0, height=96.0),
            ],
            obstacles=[],
        ),
    )


class TestObstacleValidatorName:
    """Tests for validator name property."""

    def test_name_is_obstacle(self, validator: ObstacleValidator) -> None:
        """Validator name should be 'obstacle'."""
        assert validator.name == "obstacle"


class TestNoObstacles:
    """Tests for configurations without obstacles."""

    def test_no_errors_without_obstacles(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """No errors when there are no obstacles."""
        result = validator.validate(config_with_room)

        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_no_errors_without_room(self, validator: ObstacleValidator) -> None:
        """No errors when there is no room config."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.75,
                ),
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                ],
            ),
        )

        result = validator.validate(config)

        assert result.is_valid
        assert len(result.errors) == 0


class TestWallReferenceValidation:
    """Tests for wall reference validation (V-02)."""

    def test_error_for_invalid_wall_index(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """Error when obstacle references invalid wall index."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=5,  # Only 2 walls (0, 1), so 5 is invalid
                horizontal_offset=10.0,
                bottom=0.0,
                width=30.0,
                height=48.0,
            ),
        ]

        result = validator.validate(config_with_room)

        assert not result.is_valid
        assert len(result.errors) == 1
        assert "unknown wall index" in result.errors[0].message.lower()
        assert result.errors[0].value == 5


class TestObstacleBoundsValidation:
    """Tests for obstacle bounds validation (V-01)."""

    def test_error_for_obstacle_exceeding_wall_width(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """Error when obstacle extends beyond wall width."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,  # Wall 0 is 120" long
                horizontal_offset=100.0,  # Starts at 100"
                bottom=0.0,
                width=30.0,  # Ends at 130", beyond 120"
                height=48.0,
            ),
        ]

        result = validator.validate(config_with_room)

        assert not result.is_valid
        horizontal_errors = [
            e
            for e in result.errors
            if "length" in e.message.lower() or "ends at" in e.message.lower()
        ]
        assert len(horizontal_errors) >= 1

    def test_error_for_obstacle_exceeding_wall_height(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """Error when obstacle extends beyond wall height."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,  # Wall 0 is 96" high
                horizontal_offset=10.0,
                bottom=60.0,  # Starts at 60"
                width=30.0,
                height=48.0,  # Ends at 108", beyond 96"
            ),
        ]

        result = validator.validate(config_with_room)

        assert not result.is_valid
        height_errors = [e for e in result.errors if "height" in e.message.lower()]
        assert len(height_errors) >= 1

    def test_valid_obstacle_within_bounds(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """No error for obstacle within wall bounds."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,  # Wall 0 is 120" x 96"
                horizontal_offset=10.0,
                bottom=24.0,
                width=30.0,  # Ends at 40", within 120"
                height=48.0,  # Ends at 72", within 96"
            ),
        ]

        result = validator.validate(config_with_room)

        assert result.is_valid


class TestWallBlockingValidation:
    """Tests for wall blocking validation (V-04)."""

    def test_error_for_completely_blocked_wall(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """Error when wall is completely blocked by obstacles."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,  # Wall 0 is 120" long
                horizontal_offset=0.0,
                bottom=0.0,
                width=60.0,
                height=48.0,
            ),
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=60.0,
                bottom=0.0,
                width=60.0,  # Together, these cover 0-120"
                height=48.0,
            ),
        ]

        result = validator.validate(config_with_room)

        blocking_errors = [
            e for e in result.errors if "entirely blocked" in e.message.lower()
        ]
        assert len(blocking_errors) >= 1

    def test_warning_for_mostly_blocked_wall(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """Warning when wall is >80% blocked."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,  # Wall 0 is 120" long
                horizontal_offset=0.0,
                bottom=0.0,
                width=100.0,  # 100/120 = 83% blocked
                height=48.0,
            ),
        ]

        result = validator.validate(config_with_room)

        blocking_warnings = [w for w in result.warnings if ">80%" in w.message]
        assert len(blocking_warnings) >= 1

    def test_no_warning_for_partially_blocked_wall(
        self, validator: ObstacleValidator, config_with_room: CabinetConfiguration
    ) -> None:
        """No warning when wall is <80% blocked."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,  # Wall 0 is 120" long
                horizontal_offset=0.0,
                bottom=0.0,
                width=50.0,  # 50/120 = 42% blocked
                height=48.0,
            ),
        ]

        result = validator.validate(config_with_room)

        blocking_warnings = [
            w for w in result.warnings if "blocked" in w.message.lower()
        ]
        assert len(blocking_warnings) == 0


class TestLegacyFunction:
    """Tests for backwards-compatible check_obstacle_advisories function."""

    def test_legacy_function_returns_list(
        self, config_with_room: CabinetConfiguration
    ) -> None:
        """Legacy function returns list of errors and warnings."""
        result = check_obstacle_advisories(config_with_room)

        assert isinstance(result, list)

    def test_legacy_function_includes_errors(
        self, config_with_room: CabinetConfiguration
    ) -> None:
        """Legacy function includes errors for invalid config."""
        config_with_room.room.obstacles = [
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=10,  # Invalid wall index
                horizontal_offset=10.0,
                bottom=0.0,
                width=30.0,
                height=48.0,
            ),
        ]

        result = check_obstacle_advisories(config_with_room)

        from cabinets.application.config.validators.base import ValidationError

        errors = [r for r in result if isinstance(r, ValidationError)]
        assert len(errors) >= 1
