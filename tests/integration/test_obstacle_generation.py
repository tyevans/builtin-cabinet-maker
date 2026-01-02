"""Integration tests for obstacle-aware cabinet generation."""

from pathlib import Path

from cabinets.application.config import (
    load_config,
    validate_config,
    config_to_obstacles,
    config_to_clearance_defaults,
    config_to_section_specs,
)
from cabinets.domain.services import (
    ObstacleCollisionService,
    ObstacleAwareLayoutService,
)
from cabinets.domain.section_resolver import SectionSpec
from cabinets.domain.value_objects import ObstacleType


FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "configs"


class TestObstacleConfigLoading:
    """Test loading configs with obstacles."""

    def test_load_config_with_window(self):
        """Config with window obstacle loads successfully."""
        config = load_config(FIXTURES_PATH / "valid_with_window.json")
        assert config.room is not None
        assert len(config.room.obstacles) == 1
        assert config.room.obstacles[0].type.value == "window"

    def test_load_config_with_multiple_obstacles(self):
        """Config with multiple obstacles loads successfully."""
        config = load_config(FIXTURES_PATH / "valid_with_multiple_obstacles.json")
        assert len(config.room.obstacles) == 3

    def test_load_config_with_custom_clearances(self):
        """Config with custom clearances loads successfully."""
        config = load_config(FIXTURES_PATH / "valid_with_custom_clearances.json")
        assert config.obstacle_defaults is not None
        assert config.obstacle_defaults.window is not None
        assert config.obstacle_defaults.window.top == 3


class TestObstacleValidation:
    """Test validation of configs with obstacles."""

    def test_valid_config_with_obstacles_passes(self):
        """Valid config with obstacles passes validation."""
        config = load_config(FIXTURES_PATH / "valid_with_window.json")
        result = validate_config(config)
        assert result.is_valid

    def test_invalid_obstacle_beyond_wall_fails(self):
        """Obstacle extending beyond wall fails validation."""
        config = load_config(
            FIXTURES_PATH / "invalid_obstacle_extends_beyond_wall.json"
        )
        result = validate_config(config)
        assert not result.is_valid
        assert any("extends beyond" in e.message for e in result.errors)


class TestObstacleConversion:
    """Test converting config obstacles to domain objects."""

    def test_config_to_obstacles(self):
        """Config obstacles convert to domain Obstacle entities."""
        config = load_config(FIXTURES_PATH / "valid_with_window.json")
        obstacles = config_to_obstacles(config)
        assert len(obstacles) == 1
        assert obstacles[0].wall_index == 0
        assert obstacles[0].width == 48
        assert obstacles[0].height == 48

    def test_config_to_clearance_defaults(self):
        """Custom clearance defaults merge with system defaults."""
        config = load_config(FIXTURES_PATH / "valid_with_custom_clearances.json")
        defaults = config_to_clearance_defaults(config)

        # Custom window clearance
        assert defaults[ObstacleType.WINDOW].top == 3
        # Default door clearance (not overridden)
        assert defaults[ObstacleType.DOOR].left == 2


class TestObstacleAwareLayout:
    """Test obstacle-aware layout generation."""

    def test_layout_avoids_window(self):
        """Layout correctly avoids window obstacle."""
        config = load_config(FIXTURES_PATH / "valid_with_window.json")
        obstacles = config_to_obstacles(config)
        defaults = config_to_clearance_defaults(config)

        collision_service = ObstacleCollisionService(defaults)
        layout_service = ObstacleAwareLayoutService(collision_service)

        wall = config.room.walls[0]
        sections = [
            SectionSpec(width=36, shelves=4),
            SectionSpec(width=48, shelves=2, height_mode="lower"),
            SectionSpec(width=36, shelves=4),
        ]

        result = layout_service.layout_sections(
            wall_length=wall.length,
            wall_height=wall.height,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Should have placed sections
        assert result.section_count > 0

        # Lower section should be below window
        lower_sections = [s for s in result.placed_sections if s.height_mode == "lower"]
        if lower_sections:
            window = obstacles[0]
            for section in lower_sections:
                assert section.bounds.top <= window.bottom

    def test_layout_with_door_at_start(self):
        """Layout handles area occupied by door."""
        config = load_config(FIXTURES_PATH / "valid_with_multiple_obstacles.json")
        obstacles = config_to_obstacles(config)
        defaults = config_to_clearance_defaults(config)

        collision_service = ObstacleCollisionService(defaults)
        layout_service = ObstacleAwareLayoutService(collision_service)

        wall = config.room.walls[0]
        sections = [SectionSpec(width="fill", shelves=4)]

        result = layout_service.layout_sections(
            wall_length=wall.length,
            wall_height=wall.height,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Should have placed sections (may be split or partial height)
        assert result.section_count > 0

        # Verify no section collides with obstacle zones
        zones = collision_service.get_obstacle_zones(obstacles, 0)
        for placed in result.placed_sections:
            collisions = collision_service.check_collision(placed.bounds, zones)
            assert len(collisions) == 0, (
                f"Section {placed.section_index} collides with obstacles"
            )


class TestEndToEndObstacleGeneration:
    """End-to-end tests for obstacle-aware cabinet generation."""

    def test_full_pipeline_with_obstacles(self):
        """Full pipeline works with obstacle configs."""
        config = load_config(FIXTURES_PATH / "valid_with_window.json")

        # Validate
        result = validate_config(config)
        assert result.is_valid

        # Convert to domain objects
        obstacles = config_to_obstacles(config)
        defaults = config_to_clearance_defaults(config)

        # Create services
        collision_service = ObstacleCollisionService(defaults)
        layout_service = ObstacleAwareLayoutService(collision_service)

        # Generate layout
        wall = config.room.walls[0]
        sections = config_to_section_specs(config)

        layout_result = layout_service.layout_sections(
            wall_length=wall.length,
            wall_height=wall.height,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Should have successful layout
        assert layout_result.section_count > 0

        # All placed sections should not collide with obstacles
        zones = collision_service.get_obstacle_zones(obstacles, 0)
        for placed in layout_result.placed_sections:
            collisions = collision_service.check_collision(placed.bounds, zones)
            assert len(collisions) == 0, (
                f"Section {placed.section_index} collides with obstacles"
            )

    def test_pipeline_with_custom_clearances(self):
        """Pipeline respects custom clearances."""
        config = load_config(FIXTURES_PATH / "valid_with_custom_clearances.json")

        # Validate
        result = validate_config(config)
        assert result.is_valid

        # Convert to domain objects
        obstacles = config_to_obstacles(config)
        defaults = config_to_clearance_defaults(config)

        # Verify custom clearance is applied
        assert defaults[ObstacleType.WINDOW].top == 3

        # The obstacle has its own clearance override
        obstacle = obstacles[0]
        assert obstacle.clearance_override is not None
        assert obstacle.clearance_override.bottom == 6

        # Create services
        collision_service = ObstacleCollisionService(defaults)
        layout_service = ObstacleAwareLayoutService(collision_service)

        # Generate layout
        wall = config.room.walls[0]
        sections = config_to_section_specs(config)

        layout_result = layout_service.layout_sections(
            wall_length=wall.length,
            wall_height=wall.height,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Should have successful layout
        assert layout_result.section_count > 0

    def test_pipeline_with_multiple_obstacles(self):
        """Pipeline handles multiple obstacles correctly."""
        config = load_config(FIXTURES_PATH / "valid_with_multiple_obstacles.json")

        # Validate
        result = validate_config(config)
        assert result.is_valid

        # Convert to domain objects
        obstacles = config_to_obstacles(config)
        assert len(obstacles) == 3

        defaults = config_to_clearance_defaults(config)

        # Create services
        collision_service = ObstacleCollisionService(defaults)
        layout_service = ObstacleAwareLayoutService(collision_service)

        # Generate layout
        wall = config.room.walls[0]
        sections = config_to_section_specs(config)

        layout_result = layout_service.layout_sections(
            wall_length=wall.length,
            wall_height=wall.height,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # All placed sections should not collide with obstacles
        zones = collision_service.get_obstacle_zones(obstacles, 0)
        for placed in layout_result.placed_sections:
            collisions = collision_service.check_collision(placed.bounds, zones)
            assert len(collisions) == 0, (
                f"Section {placed.section_index} collides with obstacles"
            )
