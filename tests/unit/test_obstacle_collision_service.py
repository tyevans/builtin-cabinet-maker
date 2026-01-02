"""Unit tests for ObstacleCollisionService.

These tests verify:
- Zone retrieval for specific walls
- Collision detection between sections and zones
- Batch collision checking
- Valid region finding with various obstacle configurations
- Edge cases and boundary conditions
"""

from cabinets.domain.entities import Obstacle
from cabinets.domain.services import ObstacleCollisionService
from cabinets.domain.value_objects import (
    Clearance,
    DEFAULT_CLEARANCES,
    ObstacleType,
    ObstacleZone,
    SectionBounds,
)


class TestObstacleCollisionServiceInit:
    """Tests for ObstacleCollisionService initialization."""

    def test_init_with_default_clearances(self) -> None:
        """Service should use DEFAULT_CLEARANCES when none provided."""
        service = ObstacleCollisionService()
        assert service.default_clearances == DEFAULT_CLEARANCES

    def test_init_with_custom_clearances(self) -> None:
        """Service should use provided custom clearances."""
        custom = {
            ObstacleType.WINDOW: Clearance(top=5.0, bottom=5.0, left=5.0, right=5.0)
        }
        service = ObstacleCollisionService(default_clearances=custom)
        assert service.default_clearances == custom


class TestGetObstacleZones:
    """Tests for get_obstacle_zones method."""

    def test_get_zones_for_wall_with_obstacles(self) -> None:
        """Should return zones for obstacles on specified wall."""
        service = ObstacleCollisionService()
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.DOOR,
                wall_index=0,
                horizontal_offset=100.0,
                bottom=0.0,
                width=36.0,
                height=80.0,
            ),
        ]
        zones = service.get_obstacle_zones(obstacles, wall_index=0)

        assert len(zones) == 2
        # Window zone (with 2" clearance): 22-74 horizontal, 34-74 vertical
        assert zones[0].left == 22.0
        assert zones[0].right == 74.0
        assert zones[0].bottom == 34.0
        assert zones[0].top == 74.0
        # Door zone (with 2" side clearance): 98-138 horizontal, 0-80 vertical
        assert zones[1].left == 98.0
        assert zones[1].right == 138.0
        assert zones[1].bottom == 0.0
        assert zones[1].top == 80.0

    def test_get_zones_empty_obstacles(self) -> None:
        """Should return empty list when no obstacles provided."""
        service = ObstacleCollisionService()
        zones = service.get_obstacle_zones([], wall_index=0)
        assert zones == []

    def test_get_zones_filters_by_wall_index(self) -> None:
        """Should only return zones for specified wall index."""
        service = ObstacleCollisionService()
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=1,
                horizontal_offset=12.0,
                bottom=36.0,
                width=36.0,
                height=36.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.DOOR,
                wall_index=2,
                horizontal_offset=0.0,
                bottom=0.0,
                width=36.0,
                height=80.0,
            ),
        ]

        zones_wall_0 = service.get_obstacle_zones(obstacles, wall_index=0)
        zones_wall_1 = service.get_obstacle_zones(obstacles, wall_index=1)
        zones_wall_2 = service.get_obstacle_zones(obstacles, wall_index=2)
        zones_wall_3 = service.get_obstacle_zones(obstacles, wall_index=3)

        assert len(zones_wall_0) == 1
        assert len(zones_wall_1) == 1
        assert len(zones_wall_2) == 1
        assert len(zones_wall_3) == 0

    def test_get_zones_multiple_obstacles_same_wall(self) -> None:
        """Should return zones for all obstacles on same wall."""
        service = ObstacleCollisionService()
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.OUTLET,
                wall_index=0,
                horizontal_offset=12.0,
                bottom=12.0,
                width=4.0,
                height=4.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.SWITCH,
                wall_index=0,
                horizontal_offset=36.0,
                bottom=48.0,
                width=4.0,
                height=4.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.VENT,
                wall_index=0,
                horizontal_offset=60.0,
                bottom=84.0,
                width=12.0,
                height=6.0,
            ),
        ]
        zones = service.get_obstacle_zones(obstacles, wall_index=0)
        assert len(zones) == 3

    def test_get_zones_uses_custom_clearances(self) -> None:
        """Should use custom clearances from service initialization."""
        custom = {
            ObstacleType.WINDOW: Clearance(top=10.0, bottom=10.0, left=10.0, right=10.0)
        }
        service = ObstacleCollisionService(default_clearances=custom)
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            ),
        ]
        zones = service.get_obstacle_zones(obstacles, wall_index=0)

        # With 10" clearance: 14-82 horizontal, 26-82 vertical
        assert zones[0].left == 14.0
        assert zones[0].right == 82.0
        assert zones[0].bottom == 26.0
        assert zones[0].top == 82.0


class TestCheckCollision:
    """Tests for check_collision method."""

    def _create_zone(
        self,
        left: float = 20.0,
        right: float = 70.0,
        bottom: float = 34.0,
        top: float = 74.0,
    ) -> ObstacleZone:
        """Helper to create an ObstacleZone with a dummy obstacle."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=22.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        return ObstacleZone(
            left=left, right=right, bottom=bottom, top=top, obstacle=obstacle
        )

    def test_no_collision_section_left_of_zone(self) -> None:
        """No collision when section is entirely to the left of zone."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=0.0, right=20.0, bottom=0.0, top=96.0)
        zones = [self._create_zone(left=20.0, right=70.0)]

        results = service.check_collision(section, zones)
        assert results == []

    def test_no_collision_section_right_of_zone(self) -> None:
        """No collision when section is entirely to the right of zone."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=70.0, right=120.0, bottom=0.0, top=96.0)
        zones = [self._create_zone(left=20.0, right=70.0)]

        results = service.check_collision(section, zones)
        assert results == []

    def test_no_collision_section_above_zone(self) -> None:
        """No collision when section is entirely above zone."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=30.0, right=60.0, bottom=74.0, top=96.0)
        zones = [self._create_zone(bottom=34.0, top=74.0)]

        results = service.check_collision(section, zones)
        assert results == []

    def test_no_collision_section_below_zone(self) -> None:
        """No collision when section is entirely below zone."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=30.0, right=60.0, bottom=0.0, top=34.0)
        zones = [self._create_zone(bottom=34.0, top=74.0)]

        results = service.check_collision(section, zones)
        assert results == []

    def test_collision_section_overlaps_zone(self) -> None:
        """Collision detected when section overlaps zone."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=30.0, right=60.0, bottom=40.0, top=80.0)
        zones = [self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)]

        results = service.check_collision(section, zones)
        assert len(results) == 1
        assert results[0].zone == zones[0]
        # Overlap: x from 30-60 (30), y from 40-74 (34) = 30 * 34 = 1020
        assert results[0].overlap_area == 1020.0

    def test_collision_section_inside_zone(self) -> None:
        """Collision detected when section is entirely inside zone."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=30.0, right=50.0, bottom=40.0, top=60.0)
        zones = [self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)]

        results = service.check_collision(section, zones)
        assert len(results) == 1
        # Full section area: 20 * 20 = 400
        assert results[0].overlap_area == 400.0

    def test_collision_zone_inside_section(self) -> None:
        """Collision detected when zone is entirely inside section."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=10.0, right=80.0, bottom=30.0, top=80.0)
        zone = self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)
        zones = [zone]

        results = service.check_collision(section, zones)
        assert len(results) == 1
        # Full zone area: 50 * 40 = 2000
        assert results[0].overlap_area == 2000.0

    def test_no_collision_touching_edges_horizontal(self) -> None:
        """No collision when section just touches zone at horizontal edge."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=70.0, right=100.0, bottom=40.0, top=60.0)
        zones = [self._create_zone(left=20.0, right=70.0)]

        results = service.check_collision(section, zones)
        assert results == []

    def test_no_collision_touching_edges_vertical(self) -> None:
        """No collision when section just touches zone at vertical edge."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=30.0, right=60.0, bottom=74.0, top=96.0)
        zones = [self._create_zone(top=74.0)]

        results = service.check_collision(section, zones)
        assert results == []

    def test_multiple_collisions(self) -> None:
        """Detect collisions with multiple zones."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=0.0, right=120.0, bottom=0.0, top=96.0)
        zones = [
            self._create_zone(left=20.0, right=40.0, bottom=30.0, top=60.0),
            self._create_zone(left=60.0, right=80.0, bottom=30.0, top=60.0),
        ]

        results = service.check_collision(section, zones)
        assert len(results) == 2

    def test_collision_empty_zones_list(self) -> None:
        """No collision when zones list is empty."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=0.0, right=120.0, bottom=0.0, top=96.0)

        results = service.check_collision(section, [])
        assert results == []

    def test_overlap_area_calculation_partial_overlap(self) -> None:
        """Overlap area should be calculated correctly for partial overlap."""
        service = ObstacleCollisionService()
        # Zone: left=40, right=80, bottom=40, top=80
        # Section: left=60, right=100, bottom=60, top=100
        # Overlap: x from 60-80 (20), y from 60-80 (20) = 400
        section = SectionBounds(left=60.0, right=100.0, bottom=60.0, top=100.0)
        zones = [self._create_zone(left=40.0, right=80.0, bottom=40.0, top=80.0)]

        results = service.check_collision(section, zones)
        assert len(results) == 1
        assert results[0].overlap_area == 400.0


class TestCheckCollisionsBatch:
    """Tests for check_collisions_batch method."""

    def _create_zone(
        self,
        left: float,
        right: float,
        bottom: float,
        top: float,
    ) -> ObstacleZone:
        """Helper to create an ObstacleZone with a dummy obstacle."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=left + 2.0,
            bottom=bottom + 2.0,
            width=right - left - 4.0,
            height=top - bottom - 4.0,
        )
        return ObstacleZone(
            left=left, right=right, bottom=bottom, top=top, obstacle=obstacle
        )

    def test_batch_check_multiple_sections_multiple_zones(self) -> None:
        """Should check all sections against all zones."""
        service = ObstacleCollisionService()
        sections = [
            SectionBounds(left=0.0, right=30.0, bottom=0.0, top=96.0),
            SectionBounds(left=30.0, right=60.0, bottom=0.0, top=96.0),
            SectionBounds(left=60.0, right=90.0, bottom=0.0, top=96.0),
        ]
        zones = [
            self._create_zone(left=20.0, right=40.0, bottom=30.0, top=60.0),
        ]

        results = service.check_collisions_batch(sections, zones)

        assert len(results) == 3
        assert 0 in results
        assert 1 in results
        assert 2 in results

    def test_batch_check_mixed_results(self) -> None:
        """Some sections collide, some don't."""
        service = ObstacleCollisionService()
        sections = [
            SectionBounds(left=0.0, right=20.0, bottom=0.0, top=96.0),  # No collision
            SectionBounds(left=25.0, right=55.0, bottom=0.0, top=96.0),  # Collision
            SectionBounds(left=60.0, right=90.0, bottom=0.0, top=96.0),  # No collision
        ]
        zones = [
            self._create_zone(left=20.0, right=60.0, bottom=30.0, top=60.0),
        ]

        results = service.check_collisions_batch(sections, zones)

        assert len(results[0]) == 0  # No collision
        assert len(results[1]) == 1  # Collision with zone
        assert len(results[2]) == 0  # No collision

    def test_batch_check_empty_sections(self) -> None:
        """Should return empty dict when no sections provided."""
        service = ObstacleCollisionService()
        zones = [
            self._create_zone(left=20.0, right=40.0, bottom=30.0, top=60.0),
        ]

        results = service.check_collisions_batch([], zones)
        assert results == {}

    def test_batch_check_empty_zones(self) -> None:
        """All sections should have no collisions when zones empty."""
        service = ObstacleCollisionService()
        sections = [
            SectionBounds(left=0.0, right=30.0, bottom=0.0, top=96.0),
            SectionBounds(left=30.0, right=60.0, bottom=0.0, top=96.0),
        ]

        results = service.check_collisions_batch(sections, [])

        assert len(results[0]) == 0
        assert len(results[1]) == 0

    def test_batch_check_section_collides_with_multiple_zones(self) -> None:
        """Section can collide with multiple zones."""
        service = ObstacleCollisionService()
        sections = [
            SectionBounds(left=0.0, right=100.0, bottom=0.0, top=96.0),
        ]
        zones = [
            self._create_zone(left=10.0, right=30.0, bottom=30.0, top=60.0),
            self._create_zone(left=50.0, right=70.0, bottom=30.0, top=60.0),
        ]

        results = service.check_collisions_batch(sections, zones)

        assert len(results[0]) == 2


class TestFindValidRegions:
    """Tests for find_valid_regions method."""

    def _create_zone(
        self,
        left: float,
        right: float,
        bottom: float,
        top: float,
    ) -> ObstacleZone:
        """Helper to create an ObstacleZone with a dummy obstacle."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=max(0, left + 2.0),
            bottom=max(0, bottom + 2.0),
            width=max(1.0, right - left - 4.0),
            height=max(1.0, top - bottom - 4.0),
        )
        return ObstacleZone(
            left=left, right=right, bottom=bottom, top=top, obstacle=obstacle
        )

    def test_no_obstacles_returns_full_wall(self) -> None:
        """With no obstacles, entire wall is available."""
        service = ObstacleCollisionService()
        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=[],
        )

        assert len(regions) == 1
        assert regions[0].left == 0.0
        assert regions[0].right == 120.0
        assert regions[0].bottom == 0.0
        assert regions[0].top == 96.0
        assert regions[0].region_type == "full"

    def test_centered_window_creates_left_and_right_regions(self) -> None:
        """Window in center should create regions on left and right."""
        service = ObstacleCollisionService()
        # Window zone in center: 40-80 horizontal, 30-70 vertical
        zones = [self._create_zone(left=40.0, right=80.0, bottom=30.0, top=70.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have: full region left (0-40), lower region (40-80, 0-30),
        # upper region (40-80, 70-96), full region right (80-120)
        region_types = {
            (r.region_type, r.left, r.right, r.bottom, r.top) for r in regions
        }

        # Check full region on left
        assert ("full", 0.0, 40.0, 0.0, 96.0) in region_types
        # Check full region on right
        assert ("full", 80.0, 120.0, 0.0, 96.0) in region_types
        # Check lower region below window
        assert ("lower", 40.0, 80.0, 0.0, 30.0) in region_types
        # Check upper region above window
        assert ("upper", 40.0, 80.0, 70.0, 96.0) in region_types

    def test_door_at_wall_start_creates_gap_after(self) -> None:
        """Door at start of wall should create gap after it."""
        service = ObstacleCollisionService()
        # Door at start: 0-40 horizontal, 0-80 vertical
        zones = [self._create_zone(left=0.0, right=40.0, bottom=0.0, top=80.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have: upper region over door (0-40, 80-96), full region after (40-120)
        region_types = {
            (r.region_type, r.left, r.right, r.bottom, r.top) for r in regions
        }

        assert ("upper", 0.0, 40.0, 80.0, 96.0) in region_types
        assert ("full", 40.0, 120.0, 0.0, 96.0) in region_types

    def test_door_at_wall_end_creates_gap_before(self) -> None:
        """Door at end of wall should create gap before it."""
        service = ObstacleCollisionService()
        # Door at end: 80-120 horizontal, 0-80 vertical
        zones = [self._create_zone(left=80.0, right=120.0, bottom=0.0, top=80.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        region_types = {
            (r.region_type, r.left, r.right, r.bottom, r.top) for r in regions
        }

        assert ("full", 0.0, 80.0, 0.0, 96.0) in region_types
        assert ("upper", 80.0, 120.0, 80.0, 96.0) in region_types

    def test_multiple_obstacles_complex_regions(self) -> None:
        """Multiple obstacles should create complex valid regions."""
        service = ObstacleCollisionService()
        # Two windows with gap between
        zones = [
            self._create_zone(left=20.0, right=50.0, bottom=36.0, top=72.0),
            self._create_zone(left=70.0, right=100.0, bottom=36.0, top=72.0),
        ]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have regions: left of first window, between windows, right of second,
        # plus upper/lower for each window
        assert len(regions) >= 5

    def test_minimum_width_filtering(self) -> None:
        """Regions smaller than min_width should be excluded."""
        service = ObstacleCollisionService()
        # Zone that leaves only 5" gap on right (less than 6" min)
        zones = [self._create_zone(left=0.0, right=115.0, bottom=36.0, top=72.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Gap on right (115-120) should be excluded due to min_width
        region_lefts = {r.left for r in regions}
        assert 115.0 not in region_lefts

    def test_minimum_height_filtering(self) -> None:
        """Regions smaller than min_height should be excluded."""
        service = ObstacleCollisionService()
        # Zone that leaves only 8" below (less than 12" min)
        zones = [self._create_zone(left=40.0, right=80.0, bottom=8.0, top=90.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Lower region (0-8 height) should be excluded
        lower_regions = [
            r for r in regions if r.region_type == "lower" and r.left == 40.0
        ]
        assert len(lower_regions) == 0

    def test_upper_and_lower_region_detection(self) -> None:
        """Should detect both upper and lower regions for centered obstacle."""
        service = ObstacleCollisionService()
        # Window in center of wall
        zones = [self._create_zone(left=40.0, right=80.0, bottom=36.0, top=72.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        lower_regions = [r for r in regions if r.region_type == "lower"]
        upper_regions = [r for r in regions if r.region_type == "upper"]

        assert len(lower_regions) >= 1
        assert len(upper_regions) >= 1

    def test_obstacle_extending_beyond_wall_left(self) -> None:
        """Obstacle with negative left should be clamped to wall edge."""
        service = ObstacleCollisionService()
        # Zone extending past left edge
        zones = [self._create_zone(left=-10.0, right=40.0, bottom=36.0, top=72.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have upper/lower regions starting from 0, and full region after 40
        full_regions = [r for r in regions if r.region_type == "full"]
        assert any(r.left == 40.0 and r.right == 120.0 for r in full_regions)

    def test_obstacle_extending_beyond_wall_right(self) -> None:
        """Obstacle extending past right edge should be clamped."""
        service = ObstacleCollisionService()
        # Zone extending past right edge
        zones = [self._create_zone(left=80.0, right=130.0, bottom=36.0, top=72.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have full region on left (0-80)
        full_regions = [r for r in regions if r.region_type == "full"]
        assert any(r.left == 0.0 and r.right == 80.0 for r in full_regions)

    def test_overlapping_obstacles(self) -> None:
        """Overlapping obstacles should be handled correctly."""
        service = ObstacleCollisionService()
        # Two overlapping windows
        zones = [
            self._create_zone(left=30.0, right=60.0, bottom=36.0, top=72.0),
            self._create_zone(left=50.0, right=80.0, bottom=36.0, top=72.0),
        ]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should still find valid regions
        assert len(regions) >= 1

    def test_wall_completely_blocked_horizontally(self) -> None:
        """Wall completely blocked horizontally should only have upper/lower regions."""
        service = ObstacleCollisionService()
        # Zone covering full wall width
        zones = [self._create_zone(left=0.0, right=120.0, bottom=36.0, top=72.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should only have lower and upper regions, no full regions
        full_regions = [r for r in regions if r.region_type == "full"]
        assert len(full_regions) == 0

        # Should have lower (0-36) and upper (72-96) regions
        lower_regions = [r for r in regions if r.region_type == "lower"]
        upper_regions = [r for r in regions if r.region_type == "upper"]
        assert len(lower_regions) >= 1
        assert len(upper_regions) >= 1

    def test_wall_completely_blocked_floor_to_ceiling(self) -> None:
        """Zone covering floor to ceiling should create gaps on sides only."""
        service = ObstacleCollisionService()
        # Zone covering full height in middle
        zones = [self._create_zone(left=40.0, right=80.0, bottom=0.0, top=96.0)]

        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have full regions on left (0-40) and right (80-120)
        full_regions = [r for r in regions if r.region_type == "full"]
        assert len(full_regions) == 2

        # No lower or upper regions for this zone (floor to ceiling)
        lower_upper_regions = [
            r for r in regions if r.region_type in ("lower", "upper")
        ]
        assert len(lower_upper_regions) == 0

    def test_custom_minimum_dimensions(self) -> None:
        """Should respect custom minimum width and height."""
        service = ObstacleCollisionService()
        zones = [self._create_zone(left=40.0, right=80.0, bottom=36.0, top=72.0)]

        # With very large minimums, fewer regions should be returned
        regions_large_min = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=50.0,
            min_height=50.0,
        )

        # With small minimums, more regions should be returned
        regions_small_min = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=1.0,
            min_height=1.0,
        )

        assert len(regions_large_min) <= len(regions_small_min)


class TestAnalyzeVerticalRegion:
    """Tests for _analyze_vertical_region private method."""

    def _create_zone(
        self,
        left: float,
        right: float,
        bottom: float,
        top: float,
    ) -> ObstacleZone:
        """Helper to create an ObstacleZone with a dummy obstacle."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=max(0, left + 2.0),
            bottom=max(0, bottom + 2.0),
            width=max(1.0, right - left - 4.0),
            height=max(1.0, top - bottom - 4.0),
        )
        return ObstacleZone(
            left=left, right=right, bottom=bottom, top=top, obstacle=obstacle
        )

    def test_region_too_narrow(self) -> None:
        """Region narrower than min_width should return empty list."""
        service = ObstacleCollisionService()
        regions = service._analyze_vertical_region(
            left=0.0,
            right=5.0,  # Only 5" wide
            wall_height=96.0,
            zones=[],
            min_width=6.0,
            min_height=12.0,
        )
        assert regions == []

    def test_no_blocking_zones_returns_full_region(self) -> None:
        """No blocking zones should return single full-height region."""
        service = ObstacleCollisionService()
        regions = service._analyze_vertical_region(
            left=0.0,
            right=40.0,
            wall_height=96.0,
            zones=[],
            min_width=6.0,
            min_height=12.0,
        )

        assert len(regions) == 1
        assert regions[0].region_type == "full"
        assert regions[0].left == 0.0
        assert regions[0].right == 40.0
        assert regions[0].bottom == 0.0
        assert regions[0].top == 96.0

    def test_blocking_zone_creates_upper_and_lower_regions(self) -> None:
        """Blocking zone should create regions above and below."""
        service = ObstacleCollisionService()
        zones = [self._create_zone(left=0.0, right=50.0, bottom=36.0, top=72.0)]

        regions = service._analyze_vertical_region(
            left=10.0,
            right=40.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have lower (0-36) and upper (72-96) regions
        assert len(regions) == 2
        lower = [r for r in regions if r.bottom == 0.0][0]
        upper = [r for r in regions if r.bottom == 72.0][0]

        assert lower.region_type == "lower"
        assert lower.top == 36.0
        assert upper.region_type == "upper"
        assert upper.top == 96.0

    def test_zone_not_in_horizontal_range_ignored(self) -> None:
        """Zones outside the horizontal range should not block."""
        service = ObstacleCollisionService()
        zones = [self._create_zone(left=60.0, right=90.0, bottom=36.0, top=72.0)]

        regions = service._analyze_vertical_region(
            left=0.0,
            right=40.0,  # Zone is to the right of this range
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        assert len(regions) == 1
        assert regions[0].region_type == "full"

    def test_multiple_vertically_stacked_blockers(self) -> None:
        """Multiple stacked blockers should create gap regions between them."""
        service = ObstacleCollisionService()
        zones = [
            self._create_zone(left=0.0, right=50.0, bottom=20.0, top=40.0),
            self._create_zone(left=0.0, right=50.0, bottom=60.0, top=80.0),
        ]

        regions = service._analyze_vertical_region(
            left=10.0,
            right=40.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )

        # Should have: lower (0-20), gap (40-60), upper (80-96)
        region_bottoms = {r.bottom for r in regions}
        assert 0.0 in region_bottoms  # Lower region
        assert 40.0 in region_bottoms  # Gap between blockers
        assert 80.0 in region_bottoms  # Upper region


class TestCalculateOverlapArea:
    """Tests for _calculate_overlap_area private method."""

    def _create_zone(
        self,
        left: float,
        right: float,
        bottom: float,
        top: float,
    ) -> ObstacleZone:
        """Helper to create an ObstacleZone with a dummy obstacle."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=max(0, left),
            bottom=max(0, bottom),
            width=max(1.0, right - left),
            height=max(1.0, top - bottom),
        )
        return ObstacleZone(
            left=left, right=right, bottom=bottom, top=top, obstacle=obstacle
        )

    def test_no_overlap_returns_zero(self) -> None:
        """Non-overlapping section and zone should return 0."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=0.0, right=20.0, bottom=0.0, top=96.0)
        zone = self._create_zone(left=30.0, right=60.0, bottom=30.0, top=60.0)

        overlap = service._calculate_overlap_area(section, zone)
        assert overlap == 0.0

    def test_full_overlap_section_inside_zone(self) -> None:
        """Section inside zone should return section area."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=40.0, right=50.0, bottom=40.0, top=50.0)
        zone = self._create_zone(left=30.0, right=60.0, bottom=30.0, top=60.0)

        overlap = service._calculate_overlap_area(section, zone)
        assert overlap == 100.0  # 10 * 10

    def test_full_overlap_zone_inside_section(self) -> None:
        """Zone inside section should return zone area."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=20.0, right=80.0, bottom=20.0, top=80.0)
        zone = self._create_zone(left=30.0, right=60.0, bottom=30.0, top=60.0)

        overlap = service._calculate_overlap_area(section, zone)
        assert overlap == 900.0  # 30 * 30

    def test_partial_overlap(self) -> None:
        """Partial overlap should return intersection area."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=0.0, right=50.0, bottom=0.0, top=50.0)
        zone = self._create_zone(left=40.0, right=100.0, bottom=40.0, top=100.0)

        overlap = service._calculate_overlap_area(section, zone)
        # Overlap: x from 40-50 (10), y from 40-50 (10) = 100
        assert overlap == 100.0

    def test_edge_touching_no_overlap(self) -> None:
        """Touching edges should return 0 overlap."""
        service = ObstacleCollisionService()
        section = SectionBounds(left=0.0, right=30.0, bottom=0.0, top=50.0)
        zone = self._create_zone(left=30.0, right=60.0, bottom=0.0, top=50.0)

        overlap = service._calculate_overlap_area(section, zone)
        assert overlap == 0.0


class TestIntegration:
    """Integration tests for ObstacleCollisionService."""

    def test_full_workflow_window_on_wall(self) -> None:
        """Test complete workflow: get zones, check collisions, find valid regions."""
        service = ObstacleCollisionService()

        # Create obstacles
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=48.0,
                bottom=36.0,
                width=36.0,
                height=36.0,
                name="living_room_window",
            ),
        ]

        # Get zones for wall 0
        zones = service.get_obstacle_zones(obstacles, wall_index=0)
        assert len(zones) == 1

        # Check collision with section that overlaps window
        overlapping_section = SectionBounds(left=40.0, right=80.0, bottom=0.0, top=96.0)
        collisions = service.check_collision(overlapping_section, zones)
        assert len(collisions) == 1

        # Check collision with section that doesn't overlap
        clear_section = SectionBounds(left=0.0, right=40.0, bottom=0.0, top=96.0)
        no_collisions = service.check_collision(clear_section, zones)
        assert len(no_collisions) == 0

        # Find valid regions
        regions = service.find_valid_regions(
            wall_length=120.0,
            wall_height=96.0,
            zones=zones,
            min_width=6.0,
            min_height=12.0,
        )
        assert len(regions) >= 3  # At least left, right, and upper/lower regions

    def test_multiple_walls_different_obstacles(self) -> None:
        """Test handling obstacles on different walls."""
        service = ObstacleCollisionService()

        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.DOOR,
                wall_index=1,
                horizontal_offset=0.0,
                bottom=0.0,
                width=36.0,
                height=80.0,
            ),
            Obstacle(
                obstacle_type=ObstacleType.OUTLET,
                wall_index=2,
                horizontal_offset=12.0,
                bottom=12.0,
                width=4.0,
                height=4.0,
            ),
        ]

        # Each wall should have its own zones
        zones_0 = service.get_obstacle_zones(obstacles, wall_index=0)
        zones_1 = service.get_obstacle_zones(obstacles, wall_index=1)
        zones_2 = service.get_obstacle_zones(obstacles, wall_index=2)

        assert len(zones_0) == 1
        assert len(zones_1) == 1
        assert len(zones_2) == 1

        # Zones should reference correct obstacles
        assert zones_0[0].obstacle.obstacle_type == ObstacleType.WINDOW
        assert zones_1[0].obstacle.obstacle_type == ObstacleType.DOOR
        assert zones_2[0].obstacle.obstacle_type == ObstacleType.OUTLET

    def test_batch_collision_detection_workflow(self) -> None:
        """Test batch collision detection for layout optimization."""
        service = ObstacleCollisionService()

        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=48.0,
                bottom=36.0,
                width=36.0,
                height=36.0,
            ),
        ]
        zones = service.get_obstacle_zones(obstacles, wall_index=0)

        # Check multiple potential section placements
        candidate_sections = [
            SectionBounds(left=0.0, right=30.0, bottom=0.0, top=96.0),
            SectionBounds(left=30.0, right=60.0, bottom=0.0, top=96.0),
            SectionBounds(left=60.0, right=90.0, bottom=0.0, top=96.0),
            SectionBounds(left=90.0, right=120.0, bottom=0.0, top=96.0),
        ]

        results = service.check_collisions_batch(candidate_sections, zones)

        # Sections 0 and 3 should be clear
        # Sections 1 and 2 should have collisions
        assert len(results[0]) == 0  # Clear
        assert len(results[1]) == 1  # Collision
        assert len(results[2]) == 1  # Collision
        assert len(results[3]) == 0  # Clear
