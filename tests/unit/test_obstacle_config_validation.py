"""Unit tests for obstacle configuration validation.

These tests verify the obstacle-related validation rules:
- V-01: Obstacle within wall bounds
- V-02: Invalid wall reference
- V-03: Clearance non-negative (handled by Pydantic)
- V-04: Wall completely blocked
- V-06: Width below minimum warning (mostly blocked)
"""

import pytest

from cabinets.application.config import (
    CabinetConfig,
    CabinetConfiguration,
    ObstacleConfig,
    ObstacleTypeConfig,
    RoomConfig,
    WallSegmentConfig,
    check_obstacle_advisories,
    validate_config,
)
from cabinets.application.config.validator import ValidationError, ValidationWarning


class TestObstacleWithinWallBounds:
    """Tests for V-01: Obstacle must be within wall bounds."""

    def test_obstacle_within_bounds(self) -> None:
        """Obstacle fully within wall should pass validation."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        # No errors about obstacle bounds
        obstacle_errors = [e for e in result.errors if "Obstacle extends" in e.message]
        assert len(obstacle_errors) == 0

    def test_obstacle_extends_beyond_wall_width(self) -> None:
        """Obstacle extending beyond wall width should produce error."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=60.0,  # 60 + 48 = 108 > 100
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        assert not result.is_valid
        assert any(
            "extends beyond wall" in e.message and "wall length" in e.message
            for e in result.errors
        )

    def test_obstacle_extends_beyond_wall_height(self) -> None:
        """Obstacle extending beyond wall height should produce error."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=24.0,
            bottom=70.0,  # 70 + 36 = 106 > 96
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        assert not result.is_valid
        assert any(
            "extends beyond wall" in e.message and "wall height" in e.message
            for e in result.errors
        )

    def test_obstacle_at_wall_edge_is_valid(self) -> None:
        """Obstacle exactly at wall edge should pass validation."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=72.0,  # 72 + 48 = 120 exactly
            bottom=60.0,  # 60 + 36 = 96 exactly
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        obstacle_errors = [e for e in result.errors if "Obstacle extends" in e.message]
        assert len(obstacle_errors) == 0


class TestInvalidWallReference:
    """Tests for V-02: Invalid wall reference."""

    def test_valid_wall_reference(self) -> None:
        """Obstacle referencing valid wall index should pass validation."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        wall_ref_errors = [e for e in result.errors if "unknown wall index" in e.message]
        assert len(wall_ref_errors) == 0

    def test_invalid_wall_reference(self) -> None:
        """Obstacle referencing non-existent wall should produce error."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=5,  # Only wall 0 exists
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        assert not result.is_valid
        assert any("unknown wall index" in e.message for e in result.errors)

    def test_multiple_walls_valid_reference(self) -> None:
        """Obstacle on second wall of multi-wall room should be valid."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=80.0, height=96.0, angle=90)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.OUTLET,
            wall=1,  # Second wall exists
            horizontal_offset=10.0,
            bottom=12.0,
            width=4.0,
            height=4.0,
        )
        room = RoomConfig(name="test", walls=[wall1, wall2], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        wall_ref_errors = [e for e in result.errors if "unknown wall index" in e.message]
        assert len(wall_ref_errors) == 0


class TestWallCompletelyBlocked:
    """Tests for V-04: Wall completely blocked by obstacles."""

    def test_wall_not_blocked(self) -> None:
        """Wall with partial coverage should pass validation."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=36.0,  # Leaves 36" on left
            bottom=36.0,
            width=48.0,  # 36 + 48 = 84, leaves 36" on right
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        blocked_errors = [e for e in result.errors if "entirely blocked" in e.message]
        assert len(blocked_errors) == 0

    def test_wall_completely_blocked(self) -> None:
        """Wall with full coverage should produce error."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        # Two obstacles that together cover the entire wall width
        obs1 = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=0.0,
            bottom=36.0,
            width=50.0,
            height=36.0,
        )
        obs2 = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=50.0,
            bottom=36.0,
            width=50.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obs1, obs2])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        blocked_errors = [e for e in result.errors if "entirely blocked" in e.message]
        assert len(blocked_errors) == 1

    def test_wall_single_obstacle_blocks_entirely(self) -> None:
        """Single obstacle covering entire wall should produce error."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.DOOR,
            wall=0,
            horizontal_offset=0.0,
            bottom=0.0,
            width=100.0,  # Covers entire wall
            height=80.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        blocked_errors = [e for e in result.errors if "entirely blocked" in e.message]
        assert len(blocked_errors) == 1


class TestWallMostlyBlocked:
    """Tests for warning when wall is mostly blocked."""

    def test_wall_mostly_blocked_warning(self) -> None:
        """Wall with >80% coverage should produce warning."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        # Obstacles covering 85% of wall width
        obs1 = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=0.0,
            bottom=36.0,
            width=45.0,
            height=36.0,
        )
        obs2 = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=55.0,  # Gap of 10"
            bottom=36.0,
            width=40.0,  # Total: 45 + 40 = 85%
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obs1, obs2])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        mostly_blocked_warnings = [
            w for w in result.warnings if ">80%" in w.message
        ]
        assert len(mostly_blocked_warnings) == 1

    def test_wall_under_threshold_no_warning(self) -> None:
        """Wall with <80% coverage should not produce warning."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        # Obstacles covering 70% of wall width
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=15.0,
            bottom=36.0,
            width=70.0,  # 70%
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        mostly_blocked_warnings = [
            w for w in result.warnings if ">80%" in w.message
        ]
        assert len(mostly_blocked_warnings) == 0


class TestNoRoomOrObstacles:
    """Tests for configs without room or obstacles."""

    def test_no_room_config(self) -> None:
        """Config without room should not produce obstacle errors."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )

        result = validate_config(config)
        obstacle_errors = [e for e in result.errors if "obstacle" in e.path.lower()]
        assert len(obstacle_errors) == 0

    def test_room_without_obstacles(self) -> None:
        """Room config without obstacles should not produce obstacle errors."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room = RoomConfig(name="test", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        obstacle_errors = [e for e in result.errors if "obstacle" in e.path.lower()]
        assert len(obstacle_errors) == 0


class TestCheckObstacleAdvisoriesDirectly:
    """Tests for check_obstacle_advisories function."""

    def test_returns_empty_list_for_no_room(self) -> None:
        """check_obstacle_advisories should return empty list when no room."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )

        results = check_obstacle_advisories(config)
        assert results == []

    def test_returns_empty_list_for_no_obstacles(self) -> None:
        """check_obstacle_advisories should return empty list when no obstacles."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room = RoomConfig(name="test", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        results = check_obstacle_advisories(config)
        assert results == []

    def test_returns_validation_error_type(self) -> None:
        """check_obstacle_advisories should return proper ValidationError type."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=5,  # Invalid wall reference
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        results = check_obstacle_advisories(config)
        assert len(results) >= 1
        assert isinstance(results[0], ValidationError)

    def test_returns_validation_warning_type(self) -> None:
        """check_obstacle_advisories should return proper ValidationWarning type."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        # 85% coverage - should produce warning but not error
        obs1 = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=0.0,
            bottom=36.0,
            width=45.0,
            height=36.0,
        )
        obs2 = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=55.0,
            bottom=36.0,
            width=40.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obs1, obs2])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        results = check_obstacle_advisories(config)
        warnings = [r for r in results if isinstance(r, ValidationWarning)]
        assert len(warnings) >= 1


class TestMultipleObstaclesMultipleWalls:
    """Tests for complex scenarios with multiple obstacles and walls."""

    def test_obstacles_on_different_walls(self) -> None:
        """Obstacles on different walls should be validated against their walls."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=80.0, height=96.0, angle=90)

        # Valid obstacle on wall 0
        obs1 = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=36.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )

        # Invalid obstacle on wall 1 (extends beyond length 80)
        obs2 = ObstacleConfig(
            type=ObstacleTypeConfig.DOOR,
            wall=1,
            horizontal_offset=50.0,  # 50 + 36 = 86 > 80
            bottom=0.0,
            width=36.0,
            height=80.0,
        )

        room = RoomConfig(name="test", walls=[wall1, wall2], obstacles=[obs1, obs2])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        # Should have exactly one error for obs2
        extends_errors = [e for e in result.errors if "extends beyond wall" in e.message]
        assert len(extends_errors) == 1
        assert "room.obstacles[1]" in extends_errors[0].path

    def test_multiple_errors_on_same_obstacle(self) -> None:
        """Obstacle with multiple issues should produce multiple errors."""
        wall = WallSegmentConfig(length=100.0, height=96.0)
        # Obstacle that extends beyond both width AND height
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=70.0,  # 70 + 48 = 118 > 100
            bottom=70.0,  # 70 + 36 = 106 > 96
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = validate_config(config)
        extends_errors = [e for e in result.errors if "extends beyond wall" in e.message]
        # Should have two errors - one for width, one for height
        assert len(extends_errors) == 2
