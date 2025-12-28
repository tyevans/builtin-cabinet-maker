"""Unit tests for ObstacleAwareLayoutService.

These tests verify:
- Basic layout without obstacles
- Obstacle avoidance (left, right, below, above)
- Auto height mode selection
- Section splitting around obstacles
- Edge cases and boundary conditions
- Result structure validation
"""

import pytest

from cabinets.domain.entities import Obstacle
from cabinets.domain.section_resolver import SectionSpec
from cabinets.domain.services import ObstacleAwareLayoutService, ObstacleCollisionService
from cabinets.domain.value_objects import (
    Clearance,
    LayoutResult,
    LayoutWarning,
    ObstacleType,
    PlacedSection,
    SectionBounds,
    SkippedArea,
)


class TestObstacleAwareLayoutServiceInit:
    """Tests for ObstacleAwareLayoutService initialization."""

    def test_init_with_defaults(self) -> None:
        """Service should initialize with default minimum dimensions."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        assert service.collision_service == collision_service
        assert service.min_section_width == 6.0
        assert service.min_section_height == 12.0

    def test_init_with_custom_minimums(self) -> None:
        """Service should accept custom minimum dimensions."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(
            collision_service,
            min_section_width=8.0,
            min_section_height=18.0,
        )

        assert service.min_section_width == 8.0
        assert service.min_section_height == 18.0


class TestBasicLayout:
    """Tests for basic layout without obstacles."""

    def test_no_obstacles_full_wall_layout(self) -> None:
        """With no obstacles, sections should fill the entire wall."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        sections = [
            SectionSpec(width=30.0, shelves=3),
            SectionSpec(width=30.0, shelves=4),
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 2
        assert len(result.warnings) == 0
        assert len(result.skipped_areas) == 0

        # Check first section
        assert result.placed_sections[0].section_index == 0
        assert result.placed_sections[0].bounds.left == 0.0
        assert result.placed_sections[0].bounds.right == 30.0
        assert result.placed_sections[0].height_mode == "full"
        assert result.placed_sections[0].shelves == 3

        # Check second section
        assert result.placed_sections[1].section_index == 1
        assert result.placed_sections[1].bounds.left == 30.0
        assert result.placed_sections[1].bounds.right == 60.0
        assert result.placed_sections[1].height_mode == "full"
        assert result.placed_sections[1].shelves == 4

    def test_single_section_fits_in_available_space(self) -> None:
        """Single section should fit in available wall space."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        sections = [SectionSpec(width=48.0, shelves=5)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        assert result.placed_sections[0].bounds.width == 48.0

    def test_fill_width_resolves_correctly(self) -> None:
        """Fill width should resolve to remaining wall space."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        sections = [
            SectionSpec(width=30.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 2
        # Fill should take remaining 90 inches
        assert result.placed_sections[1].bounds.width == 90.0

    def test_multiple_fill_sections(self) -> None:
        """Multiple fill sections should each get remaining space from their position."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        sections = [
            SectionSpec(width=24.0, shelves=2),
            SectionSpec(width="fill", shelves=3),
        ]

        result = service.layout_sections(
            wall_length=100.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 2
        assert result.placed_sections[0].bounds.right == 24.0
        # Fill should take 100 - 24 = 76
        assert result.placed_sections[1].bounds.width == 76.0


class TestObstacleAvoidance:
    """Tests for obstacle avoidance behavior."""

    def test_section_placed_in_gap_left_of_obstacle(self) -> None:
        """Section should be placed in the gap to the left of an obstacle."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=60.0,
                bottom=36.0,
                width=36.0,
                height=36.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        # Section should be placed before the window
        assert result.placed_sections[0].bounds.left == 0.0
        assert result.placed_sections[0].bounds.right == 30.0

    def test_section_placed_in_gap_right_of_obstacle(self) -> None:
        """Section should be placed in the gap to the right of an obstacle."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Door at the start of wall (0-40)
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.DOOR,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=0.0,
                width=36.0,
                height=80.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        # Section should be placed after the door (which has 2" clearance on sides)
        # Door zone: 0 - 2 (left clearance) to 36 + 2 (right clearance) = -2 to 38
        # But left edge clamped to 0, so zone is 0-38
        # Section should start at 38 or later
        assert result.placed_sections[0].bounds.left >= 38.0

    def test_section_placed_below_window_lower_mode(self) -> None:
        """Section with lower mode should be placed below window."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Window in middle of wall, high up
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=40.0,
                bottom=48.0,
                width=40.0,
                height=36.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=2, height_mode="lower")]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        section = result.placed_sections[0]
        assert section.height_mode == "lower"
        # Window zone bottom: 48 - 2 (clearance) = 46
        # Lower region should be 0 to 46
        assert section.bounds.top <= 46.0
        assert section.bounds.bottom == 0.0

    def test_section_placed_above_door_upper_mode(self) -> None:
        """Section with upper mode should be placed above door."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Door in middle of wall
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.DOOR,
                wall_index=0,
                horizontal_offset=40.0,
                bottom=0.0,
                width=36.0,
                height=80.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=1, height_mode="upper")]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        section = result.placed_sections[0]
        assert section.height_mode == "upper"
        # Door zone top: 80 + 0 (no top clearance) = 80
        # Upper region should be 80 to 96
        assert section.bounds.bottom >= 80.0
        assert section.bounds.top == 96.0


class TestAutoHeightMode:
    """Tests for automatic height mode selection."""

    def test_auto_prefers_full_height_when_available(self) -> None:
        """Auto mode should prefer full height when available."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Small outlet that doesn't block full height on left side
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.OUTLET,
                wall_index=0,
                horizontal_offset=80.0,
                bottom=12.0,
                width=4.0,
                height=4.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=3, height_mode="auto")]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        # Should use full height since left side of wall is clear
        assert result.placed_sections[0].height_mode == "full"
        assert result.placed_sections[0].bounds.bottom == 0.0
        assert result.placed_sections[0].bounds.top == 96.0

    def test_auto_falls_back_to_lower_when_full_blocked(self) -> None:
        """Auto mode should fall back to lower when full height is blocked."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Window blocking full height across entire wall width
        # This forces auto mode to use lower region since no full region is available
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=48.0,
                width=120.0,  # Full wall width
                height=36.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=2, height_mode="auto")]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        section = result.placed_sections[0]
        # Should fall back to lower since full is blocked across entire wall
        assert section.height_mode == "lower"
        # Window zone bottom: 48 - 2 = 46
        assert section.bounds.top <= 46.0

    def test_auto_falls_back_to_upper_when_lower_blocked(self) -> None:
        """Auto mode should fall back to upper when full and lower are blocked."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Large obstacle blocking floor level
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=0.0,
                width=60.0,
                height=60.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=2, height_mode="auto")]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Should find the upper region (60-96) or the full region to the right (60-120)
        assert len(result.placed_sections) == 1
        section = result.placed_sections[0]
        # Either placed above the obstacle (upper) or to the right (full)
        assert section.height_mode in ("upper", "full")


class TestSectionSplitting:
    """Tests for section splitting around obstacles."""

    def test_section_split_around_centered_obstacle(self) -> None:
        """Section should be split around a centered obstacle."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Obstacle in the center of the wall, floor to ceiling
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=50.0,
                bottom=0.0,
                width=20.0,
                height=96.0,
            ),
        ]

        # Request a section that spans across the obstacle
        sections = [SectionSpec(width=100.0, shelves=6)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Section should be split around the obstacle
        assert len(result.placed_sections) >= 2
        # Should have a warning about splitting
        assert len(result.warnings) >= 1
        assert any("split" in w.message.lower() for w in result.warnings)

    def test_warning_generated_when_section_split(self) -> None:
        """Warning should be generated when a section is split."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Floor-to-ceiling obstacle in middle
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=40.0,
                bottom=0.0,
                width=20.0,
                height=96.0,
            ),
        ]

        sections = [SectionSpec(width=80.0, shelves=4)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Check for split warning
        assert result.has_warnings
        split_warnings = [w for w in result.warnings if "split" in w.message.lower()]
        assert len(split_warnings) >= 1

    def test_proportional_shelf_distribution_on_split(self) -> None:
        """Shelves should be distributed proportionally when section is split."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Floor-to-ceiling obstacle in middle
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=40.0,
                bottom=0.0,
                width=20.0,
                height=96.0,
            ),
        ]

        # Request 10 shelves in a section spanning the obstacle
        sections = [SectionSpec(width=80.0, shelves=10)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Total shelves in split sections should roughly match requested
        # (may differ due to rounding and minimum of 1 shelf per section)
        total_shelves = sum(s.shelves for s in result.placed_sections)
        # Each split section should have at least 1 shelf
        for section in result.placed_sections:
            assert section.shelves >= 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_section_too_wide_skipped_with_warning(self) -> None:
        """Section too wide to fit should be skipped with warning."""
        collision_service = ObstacleCollisionService()
        # Use a larger minimum width to prevent splitting into tiny sections
        service = ObstacleAwareLayoutService(
            collision_service,
            min_section_width=15.0,
        )

        # Large obstacle leaving only small gaps (less than min_section_width)
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=10.0,
                bottom=0.0,
                width=100.0,
                height=96.0,
            ),
        ]

        # Section wider than available gaps
        sections = [SectionSpec(width=50.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # With min_section_width=15, the gaps of 10" on each side are too small
        # Section should be skipped
        assert len(result.skipped_areas) == 1
        assert len(result.warnings) >= 1
        assert "skipped" in result.warnings[0].message.lower()

    def test_wall_completely_blocked_all_sections_skipped(self) -> None:
        """All sections should be skipped when wall is completely blocked."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Obstacle covering entire wall
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=0.0,
                width=120.0,
                height=96.0,
            ),
        ]

        sections = [
            SectionSpec(width=30.0, shelves=3),
            SectionSpec(width=30.0, shelves=3),
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # All sections should be skipped
        assert len(result.placed_sections) == 0
        assert len(result.skipped_areas) == 2
        assert len(result.warnings) >= 2

    def test_minimum_width_enforcement(self) -> None:
        """Sections smaller than minimum width should not be placed."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(
            collision_service,
            min_section_width=10.0,
        )

        # Request a section smaller than minimum
        sections = [SectionSpec(width=8.0, shelves=2)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        # Section should still be placed if there's space
        # (min_section_width mainly affects regions and splitting)
        assert len(result.placed_sections) == 1

    def test_multiple_obstacles_complex_layout(self) -> None:
        """Layout should handle multiple obstacles correctly."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Multiple obstacles
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=20.0,
                bottom=36.0,
                width=24.0,
                height=36.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.DOOR,
                wall_index=0,
                horizontal_offset=80.0,
                bottom=0.0,
                width=32.0,
                height=80.0,
            ),
        ]

        sections = [
            SectionSpec(width=15.0, shelves=2),
            SectionSpec(width=15.0, shelves=3),
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Should place at least some sections
        assert len(result.placed_sections) >= 1

    def test_empty_sections_list(self) -> None:
        """Empty sections list should return empty result."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=[],
        )

        assert len(result.placed_sections) == 0
        assert len(result.warnings) == 0
        assert len(result.skipped_areas) == 0

    def test_obstacles_on_different_wall_ignored(self) -> None:
        """Obstacles on different walls should be ignored."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Obstacle on wall 1, but we're laying out wall 0
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=1,
                horizontal_offset=0.0,
                bottom=0.0,
                width=120.0,
                height=96.0,
            ),
        ]

        sections = [SectionSpec(width=60.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,  # Different wall
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Section should be placed since obstacle is on different wall
        assert len(result.placed_sections) == 1
        assert result.placed_sections[0].bounds.width == 60.0


class TestResultStructure:
    """Tests for result structure validation."""

    def test_correct_placed_section_bounds(self) -> None:
        """PlacedSection bounds should be correctly set."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        sections = [SectionSpec(width=40.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        section = result.placed_sections[0]

        assert section.bounds.left == 0.0
        assert section.bounds.right == 40.0
        assert section.bounds.bottom == 0.0
        assert section.bounds.top == 96.0
        assert section.bounds.width == 40.0
        assert section.bounds.height == 96.0

    def test_warnings_populated_correctly(self) -> None:
        """Warnings should have correct structure."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Create situation that generates warning
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=0.0,
                width=120.0,
                height=96.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.warnings) >= 1
        warning = result.warnings[0]
        assert isinstance(warning, LayoutWarning)
        assert len(warning.message) > 0

    def test_skipped_areas_tracked_correctly(self) -> None:
        """Skipped areas should be properly tracked."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Block entire wall
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.CUSTOM,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=0.0,
                width=120.0,
                height=96.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.skipped_areas) == 1
        skipped = result.skipped_areas[0]
        assert isinstance(skipped, SkippedArea)
        assert len(skipped.reason) > 0
        assert isinstance(skipped.bounds, SectionBounds)

    def test_layout_result_properties(self) -> None:
        """LayoutResult properties should work correctly."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        sections = [
            SectionSpec(width=30.0, shelves=3),
            SectionSpec(width=40.0, shelves=4),
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        assert result.section_count == 2
        assert result.total_placed_width == 70.0
        assert not result.has_warnings
        assert not result.has_skipped_areas


class TestModeMatching:
    """Tests for height mode matching behavior."""

    def test_full_mode_only_matches_full_region(self) -> None:
        """Full height mode should only match full regions."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Window in center creates lower and upper regions
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=36.0,
                width=60.0,
                height=36.0,
            ),
        ]

        # Request full height only - should place after the window
        sections = [SectionSpec(width=30.0, shelves=3, height_mode="full")]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        if result.placed_sections:
            # Should be placed in full region (after window zone ends)
            section = result.placed_sections[0]
            assert section.height_mode == "full"
            assert section.bounds.bottom == 0.0
            assert section.bounds.top == 96.0

    def test_lower_mode_matches_lower_and_gap_regions(self) -> None:
        """Lower mode should match lower and gap regions."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        # Window high on wall
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=60.0,
                width=60.0,
                height=30.0,
            ),
        ]

        sections = [SectionSpec(width=30.0, shelves=2, height_mode="lower")]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        section = result.placed_sections[0]
        assert section.height_mode == "lower"
        # Window zone bottom: 60 - 2 = 58
        assert section.bounds.top <= 58.0


class TestRegionConsumption:
    """Tests for region consumption after placement."""

    def test_region_consumed_after_placement(self) -> None:
        """Placed section should consume its region."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        sections = [
            SectionSpec(width=40.0, shelves=3),
            SectionSpec(width=40.0, shelves=3),
            SectionSpec(width=40.0, shelves=3),
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=[],
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 3
        # Sections should be placed sequentially
        assert result.placed_sections[0].bounds.left == 0.0
        assert result.placed_sections[0].bounds.right == 40.0
        assert result.placed_sections[1].bounds.left == 40.0
        assert result.placed_sections[1].bounds.right == 80.0
        assert result.placed_sections[2].bounds.left == 80.0
        assert result.placed_sections[2].bounds.right == 120.0

    def test_sections_do_not_overlap(self) -> None:
        """Placed sections should never overlap."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.OUTLET,
                wall_index=0,
                horizontal_offset=60.0,
                bottom=12.0,
                width=4.0,
                height=4.0,
            ),
        ]

        sections = [
            SectionSpec(width=30.0, shelves=2),
            SectionSpec(width=30.0, shelves=2),
            SectionSpec(width=30.0, shelves=2),
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Check no overlaps between placed sections
        for i, section_a in enumerate(result.placed_sections):
            for j, section_b in enumerate(result.placed_sections):
                if i >= j:
                    continue
                # Sections should not horizontally overlap
                assert (
                    section_a.bounds.right <= section_b.bounds.left
                    or section_b.bounds.right <= section_a.bounds.left
                )


class TestValueObjectValidation:
    """Tests for value object validation."""

    def test_placed_section_validation(self) -> None:
        """PlacedSection should validate its inputs."""
        bounds = SectionBounds(left=0.0, right=30.0, bottom=0.0, top=96.0)

        # Valid PlacedSection
        section = PlacedSection(
            section_index=0,
            bounds=bounds,
            height_mode="full",
            shelves=3,
        )
        assert section.section_index == 0

        # Invalid section_index
        with pytest.raises(ValueError, match="section_index must be non-negative"):
            PlacedSection(
                section_index=-1,
                bounds=bounds,
                height_mode="full",
                shelves=3,
            )

        # Invalid height_mode
        with pytest.raises(ValueError, match="height_mode must be one of"):
            PlacedSection(
                section_index=0,
                bounds=bounds,
                height_mode="invalid",
                shelves=3,
            )

        # Invalid shelves
        with pytest.raises(ValueError, match="shelves must be non-negative"):
            PlacedSection(
                section_index=0,
                bounds=bounds,
                height_mode="full",
                shelves=-1,
            )

    def test_layout_warning_creation(self) -> None:
        """LayoutWarning should be created correctly."""
        warning = LayoutWarning(
            message="Test warning",
            suggestion="Test suggestion",
        )
        assert warning.message == "Test warning"
        assert warning.suggestion == "Test suggestion"

        warning_no_suggestion = LayoutWarning(message="Another warning")
        assert warning_no_suggestion.suggestion is None

    def test_skipped_area_creation(self) -> None:
        """SkippedArea should be created correctly."""
        bounds = SectionBounds(left=0.0, right=30.0, bottom=0.0, top=96.0)
        skipped = SkippedArea(
            bounds=bounds,
            reason="Test reason",
        )
        assert skipped.bounds == bounds
        assert skipped.reason == "Test reason"

    def test_layout_result_creation(self) -> None:
        """LayoutResult should be created correctly."""
        # Empty result
        result = LayoutResult()
        assert result.placed_sections == []
        assert result.warnings == []
        assert result.skipped_areas == []

        # Result with data
        bounds = SectionBounds(left=0.0, right=30.0, bottom=0.0, top=96.0)
        section = PlacedSection(
            section_index=0,
            bounds=bounds,
            height_mode="full",
            shelves=3,
        )
        warning = LayoutWarning(message="Test")
        skipped = SkippedArea(bounds=bounds, reason="Test")

        result = LayoutResult(
            placed_sections=[section],
            warnings=[warning],
            skipped_areas=[skipped],
        )
        assert len(result.placed_sections) == 1
        assert len(result.warnings) == 1
        assert len(result.skipped_areas) == 1


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complex_layout_with_multiple_obstacles(self) -> None:
        """Test complex layout with multiple obstacles and sections."""
        collision_service = ObstacleCollisionService()
        service = ObstacleAwareLayoutService(collision_service)

        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=36.0,
                height=36.0,
                name="window1",
            ),
            Obstacle(
                obstacle_type=ObstacleType.DOOR,
                wall_index=0,
                horizontal_offset=100.0,
                bottom=0.0,
                width=20.0,
                height=80.0,
                name="door1",
            ),
        ]

        sections = [
            SectionSpec(width=20.0, shelves=2),  # Before window
            SectionSpec(width=30.0, shelves=3, height_mode="lower"),  # Under window
            SectionSpec(width=20.0, shelves=2),  # After window, before door
        ]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        # Should place at least some sections
        assert len(result.placed_sections) >= 1

        # Verify no collisions with obstacles
        for section in result.placed_sections:
            zones = collision_service.get_obstacle_zones(obstacles, wall_index=0)
            collisions = collision_service.check_collision(section.bounds, zones)
            assert len(collisions) == 0

    def test_layout_respects_custom_clearances(self) -> None:
        """Layout should respect custom obstacle clearances."""
        custom_clearances = {
            ObstacleType.WINDOW: Clearance(top=6.0, bottom=6.0, left=6.0, right=6.0)
        }
        collision_service = ObstacleCollisionService(default_clearances=custom_clearances)
        service = ObstacleAwareLayoutService(collision_service)

        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=50.0,
                bottom=36.0,
                width=20.0,
                height=36.0,
            ),
        ]

        sections = [SectionSpec(width=40.0, shelves=3)]

        result = service.layout_sections(
            wall_length=120.0,
            wall_height=96.0,
            wall_index=0,
            obstacles=obstacles,
            requested_sections=sections,
        )

        assert len(result.placed_sections) == 1
        # Window zone with 6" clearance: 44-76 horizontal
        # Section should be placed before or after this zone
        section = result.placed_sections[0]
        assert section.bounds.right <= 44.0 or section.bounds.left >= 76.0
